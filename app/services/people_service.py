# -*- coding: utf-8 -*-
"""
People service for handling person data operations.

This service encapsulates business logic related to person data,
including validation, caching, and data retrieval from Cortex API.
"""
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger

from app.models import PersonData
from app.pydantic_models import CortexPersonOut
from app.services.cortex_service import CortexService
from app.utils import validate_cpf


class PeopleService:
    """Service for managing person data operations."""

    @staticmethod
    async def get_person_details(
        lookup_cpf: str, requester_cpf: str, raise_for_errors: bool = True
    ) -> Optional[CortexPersonOut]:
        """
        Get person details by CPF.
        
        Checks local database first, then fetches from Cortex API if needed.
        
        Args:
            lookup_cpf: CPF to look up
            requester_cpf: CPF of the user making the request
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            Person details or None if not found and raise_for_errors=False
            
        Raises:
            HTTPException: On validation errors or API failures
        """
        # Validate CPF format
        if not validate_cpf(lookup_cpf):
            if raise_for_errors:
                raise HTTPException(status_code=400, detail="Invalid CPF format")
            return None

        # Check local database first
        person_data = await PersonData.get_or_none(cpf=lookup_cpf)
        if person_data:
            logger.debug(f"Found person CPF {lookup_cpf} in local database")
            return CortexPersonOut(
                **person_data.data,
                created_at=person_data.created_at,
                updated_at=person_data.updated_at,
            )

        # Fetch from Cortex API
        logger.debug(f"Person CPF {lookup_cpf} not in database, fetching from Cortex API")
        success, data = await CortexService.get_person_data(lookup_cpf, requester_cpf)
        
        if not success:
            return await PeopleService._handle_cortex_error(data, raise_for_errors)

        # Save to database and return
        person_data = await PersonData.create(cpf=lookup_cpf, data=data)
        return CortexPersonOut(
            **data,
            created_at=person_data.created_at,
            updated_at=person_data.updated_at,
        )

    @staticmethod
    async def get_multiple_people_details(
        cpfs: List[str], requester_cpf: str, raise_for_errors: bool = True
    ) -> List[Optional[CortexPersonOut]]:
        """
        Get details for multiple people in batches.
        
        Args:
            cpfs: List of CPFs to look up
            requester_cpf: CPF of the user making the request
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            List of person details (may contain None for failed requests)
        """
        # Validate all CPFs first
        for cpf in cpfs:
            if not validate_cpf(cpf):
                if raise_for_errors:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid CPF format: {cpf}"
                    )

        # Process in batches of 10
        import asyncio
        results = []
        for i in range(0, len(cpfs), 10):
            batch = cpfs[i:i + 10]
            batch_results = await asyncio.gather(
                *[
                    PeopleService.get_person_details(
                        lookup_cpf=cpf, 
                        requester_cpf=requester_cpf, 
                        raise_for_errors=raise_for_errors
                    )
                    for cpf in batch
                ]
            )
            results.extend(batch_results)
        
        return results

    @staticmethod
    async def calculate_credits_needed(cpfs: List[str]) -> int:
        """
        Calculate how many credits are needed for the given CPFs.
        
        Credits are only needed for CPFs not in our database.
        
        Args:
            cpfs: List of CPFs
            
        Returns:
            Number of credits needed
        """
        cpfs_data = await PersonData.filter(cpf__in=cpfs).values_list(
            "cpf", flat=True
        )
        missing_cpfs = set(cpfs) - set(cpfs_data)
        return len(missing_cpfs)

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
