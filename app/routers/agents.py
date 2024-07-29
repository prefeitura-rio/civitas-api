# -*- coding: utf-8 -*-
import traceback
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app import config
from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.pydantic_models import AgentLocationIn, AgentLocationOut, DataRelayResponse
from app.redis_cache import cache

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET", router=router, path="/location", response_model=list[AgentLocationOut]
)
async def get_agents_location(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    try:
        token = await cache.get_data_relay_token()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.DATA_RELAY_BASE_URL}/data/agent-location",
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
    except Exception:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to fetch agents location")


@router_request(
    method="POST",
    router=router,
    path="/location",
    response_model=DataRelayResponse,
)
async def set_agent_location(
    location: AgentLocationIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.DATA_RELAY_BASE_URL}/data/agent-location",
                headers={"X-Api-Key": config.DATA_RELAY_PUBLISH_TOKEN},
                json=location.dict(),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
    except Exception:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to set agent location")
