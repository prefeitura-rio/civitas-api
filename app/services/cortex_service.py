# -*- coding: utf-8 -*-
"""
Cortex API service for handling external API calls.

This service encapsulates all interactions with the Cortex API,
providing a clean interface for the rest of the application.
"""
from typing import Any, Tuple

import aiohttp
from loguru import logger

from app import config
import app.utils as utils


class CortexService:
    """Service for interacting with Cortex APIs."""

    @staticmethod
    async def get_vehicle_data(plate: str, cpf: str) -> Tuple[bool, Any]:
        """
        Fetch vehicle data from Cortex API.
        
        Args:
            plate: Vehicle license plate
            cpf: User CPF for authentication
            
        Returns:
            Tuple of (success: bool, data: dict or response object)
        """
        logger.debug(f"Fetching vehicle data for plate {plate} from Cortex API")
        
        return await utils.cortex_request(
            method="GET",
            url=f"{config.CORTEX_VEICULOS_BASE_URL}/emplacamentos/placa/{plate}",
            cpf=cpf,
            raise_for_status=False,
        )
    
    @staticmethod
    async def get_person_data(lookup_cpf: str, requester_cpf: str) -> Tuple[bool, Any]:
        """
        Fetch person data from Cortex API.
        
        Args:
            lookup_cpf: CPF to look up
            requester_cpf: CPF of the user making the request
            
        Returns:
            Tuple of (success: bool, data: dict or response object)
        """
        logger.debug(f"Fetching person data for CPF {lookup_cpf} from Cortex API")
        
        return await utils.cortex_request(
            method="GET",
            url=f"{config.CORTEX_PESSOAS_BASE_URL}/pessoas/cpf/{lookup_cpf}",
            cpf=requester_cpf,
            raise_for_status=False,
        )
    
    @staticmethod
    async def get_company_data(cnpj: str, cpf: str) -> Tuple[bool, Any]:
        """
        Fetch company data from Cortex API.
        
        Args:
            cnpj: Company CNPJ to look up
            cpf: User CPF for authentication
            
        Returns:
            Tuple of (success: bool, data: dict or response object)
        """
        logger.debug(f"Fetching company data for CNPJ {cnpj} from Cortex API")
        
        return await utils.cortex_request(
            method="GET", 
            url=f"{config.CORTEX_PESSOAS_BASE_URL}/empresas/cnpj/{cnpj}",
            cpf=cpf,
            raise_for_status=False,
        )

    @staticmethod
    def is_legal_block_error(response: Any) -> bool:
        """
        Check if the response indicates a legal block (451 status).
        
        Args:
            response: Response object from Cortex API
            
        Returns:
            True if response indicates legal block
        """
        return (
            isinstance(response, aiohttp.ClientResponse) 
            and response.status == 451
        )
