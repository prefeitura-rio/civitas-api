# -*- coding: utf-8 -*-
"""
Company service for handling company data operations.

This service encapsulates business logic related to company data,
including validation, caching, and data retrieval from Cortex API.
"""
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger

from app.models import CompanyData
from app.pydantic_models import CortexCompanyOut
from app.services.cortex_service import CortexService
from app.utils import validate_cnpj


class CompanyService:
    """Service for managing company data operations."""

    @staticmethod
    async def get_company_details(
        cnpj: str, requester_cpf: str, raise_for_errors: bool = True
    ) -> Optional[CortexCompanyOut]:
        """
        Get company details by CNPJ.
        
        Checks local database first, then fetches from Cortex API if needed.
        
        Args:
            cnpj: CNPJ to look up
            requester_cpf: CPF of the user making the request
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            Company details or None if not found and raise_for_errors=False
            
        Raises:
            HTTPException: On validation errors or API failures
        """
        # Validate CNPJ format
        if not validate_cnpj(cnpj):
            if raise_for_errors:
                raise HTTPException(status_code=400, detail="Invalid CNPJ format")
            return None

        # Check local database first
        company_data = await CompanyData.get_or_none(cnpj=cnpj)
        if company_data:
            logger.debug(f"Found company CNPJ {cnpj} in local database")
            return CortexCompanyOut(
                **company_data.data,
                created_at=company_data.created_at,
                updated_at=company_data.updated_at,
            )

        # Fetch from Cortex API
        logger.debug(f"Company CNPJ {cnpj} not in database, fetching from Cortex API")
        success, data = await CortexService.get_company_data(cnpj, requester_cpf)
        
        if not success:
            return await CompanyService._handle_cortex_error(data, raise_for_errors)

        # Save to database and return
        company_data = await CompanyData.create(cnpj=cnpj, data=data)
        return CortexCompanyOut(
            **data,
            created_at=company_data.created_at,
            updated_at=company_data.updated_at,
        )

    @staticmethod
    async def get_multiple_companies_details(
        cnpjs: List[str], requester_cpf: str, raise_for_errors: bool = True
    ) -> List[Optional[CortexCompanyOut]]:
        """
        Get details for multiple companies in batches.
        
        Args:
            cnpjs: List of CNPJs to look up
            requester_cpf: CPF of the user making the request
            raise_for_errors: Whether to raise exceptions on errors
            
        Returns:
            List of company details (may contain None for failed requests)
        """
        # Validate all CNPJs first
        for cnpj in cnpjs:
            if not validate_cnpj(cnpj):
                if raise_for_errors:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid CNPJ format: {cnpj}"
                    )

        # Process in batches of 10
        import asyncio
        results = []
        for i in range(0, len(cnpjs), 10):
            batch = cnpjs[i:i + 10]
            batch_results = await asyncio.gather(
                *[
                    CompanyService.get_company_details(
                        cnpj=cnpj, 
                        requester_cpf=requester_cpf, 
                        raise_for_errors=raise_for_errors
                    )
                    for cnpj in batch
                ]
            )
            results.extend(batch_results)
        
        return results

    @staticmethod
    async def calculate_credits_needed(cnpjs: List[str]) -> int:
        """
        Calculate how many credits are needed for the given CNPJs.
        
        Credits are only needed for CNPJs not in our database.
        
        Args:
            cnpjs: List of CNPJs
            
        Returns:
            Number of credits needed
        """
        cnpjs_data = await CompanyData.filter(cnpj__in=cnpjs).values_list(
            "cnpj", flat=True
        )
        missing_cnpjs = set(cnpjs) - set(cnpjs_data)
        return len(missing_cnpjs)

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
