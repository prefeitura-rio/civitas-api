# -*- coding: utf-8 -*-
"""
Plate service for handling vehicle plate operations.

This service encapsulates business logic related to vehicle plates,
including validation, caching, and data retrieval.
"""
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger

from app.models import PlateData
from app.pydantic_models import CortexPlacaOut
from app.services.cortex_service import CortexService
from app.utils import validate_plate


class PlateService:
    """Service for managing vehicle plate operations."""

    @staticmethod
    async def get_plate_details(
        plate: str, cpf: str, raise_for_errors: bool = True
    ) -> Optional[CortexPlacaOut]:
        """
        Get vehicle details by plate number.
        
        Checks local database first, then fetches from Cortex API if needed.
        
        Args:
            plate: Vehicle license plate
            cpf: User CPF for authentication
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            Vehicle details or None if not found and raise_for_errors=False
            
        Raises:
            HTTPException: On validation errors or API failures
        """
        # Validate plate format
        plate = plate.upper()
        if not validate_plate(plate):
            if raise_for_errors:
                raise HTTPException(status_code=400, detail="Invalid plate format")
            return None

        # Check local database first
        plate_data = await PlateData.get_or_none(plate=plate)
        if plate_data:
            logger.debug(f"Found plate {plate} in local database")
            return CortexPlacaOut(
                **plate_data.data,
                created_at=plate_data.created_at,
                updated_at=plate_data.updated_at,
            )

        # Fetch from Cortex API
        logger.debug(f"Plate {plate} not in database, fetching from Cortex API")
        success, data = await CortexService.get_vehicle_data(plate, cpf)
        
        if not success:
            return await PlateService._handle_cortex_error(data, raise_for_errors)

        # Save to database and return
        plate_data = await PlateData.create(plate=plate, data=data)
        return CortexPlacaOut(
            **data,
            created_at=plate_data.created_at,
            updated_at=plate_data.updated_at,
        )

    @staticmethod
    async def get_multiple_plates_details(
        plates: List[str], cpf: str, raise_for_errors: bool = True
    ) -> List[Optional[CortexPlacaOut]]:
        """
        Get details for multiple plates in batches.
        
        Args:
            plates: List of license plates
            cpf: User CPF for authentication
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            List of vehicle details (may contain None for failed requests)
        """
        # Validate all plates first
        for plate in plates:
            if not validate_plate(plate.upper()):
                if raise_for_errors:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid plate format: {plate}"
                    )

        # Process in batches of 10
        import asyncio
        results = []
        for i in range(0, len(plates), 10):
            batch = plates[i:i + 10]
            batch_results = await asyncio.gather(
                *[
                    PlateService.get_plate_details(
                        plate=plate, cpf=cpf, raise_for_errors=raise_for_errors
                    )
                    for plate in batch
                ]
            )
            results.extend(batch_results)
        
        return results

    @staticmethod
    async def calculate_credits_needed(plates: List[str]) -> int:
        """
        Calculate how many credits are needed for the given plates.
        
        Credits are only needed for plates not in our database.
        
        Args:
            plates: List of license plates
            
        Returns:
            Number of credits needed
        """
        plates_data = await PlateData.filter(plate__in=plates).values_list(
            "plate", flat=True
        )
        missing_plates = set(plates) - set(plates_data)
        return len(missing_plates)

    @staticmethod
    async def _handle_cortex_error(response, raise_for_errors: bool):
        """Handle Cortex API error responses."""
        if CortexService.is_legal_block_error(response):
            if raise_for_errors:
                raise HTTPException(
                    status_code=451,
                    detail="Unavailable for legal reasons. CPF might be blocked.",
                )
            return None
        else:
            if raise_for_errors:
                raise HTTPException(
                    status_code=500,
                    detail="Something unexpected happened to Cortex API",
                )
            return None
