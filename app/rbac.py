# -*- coding: utf-8 -*-
from typing import Awaitable, Callable

import orjson as json
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app import config
from app.dependencies import is_user
from app.models import User, UserHistory
from app.oidc import get_current_user
from app.pydantic_models import OIDCUser
from app.utils import translate_method_to_action, user_has_permission


class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        method: str = request.method.upper()
        action = translate_method_to_action(method)
        resource = request.url.path[1:]

        if resource in config.RBAC_EXCLUDED_PATHS:
            return await call_next(request)

        try:
            authorization: str = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

            token = authorization.split(" ")[1]
            oidc_user: OIDCUser = await get_current_user(token)
            user: User = await get_user(oidc_user)

            if not await user_has_permission(user=user, action=action, resource=resource):
                if method == "GET":
                    body = None
                else:
                    body_bytes = await request.body()
                    body_str = body_bytes.decode()
                    if body_str:
                        body = json.loads(body_str)
                    else:
                        body = None
                await UserHistory.create(
                    user=user,
                    method=method,
                    path=request.url.path,
                    query_params=dict(request.query_params),
                    body=body,
                    status_code=403,
                )
                return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        except Exception as e:
            logger.error(f"Error on RBAC: {e}")
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

        logger.debug(f"User {user.email} has permission to {action} on {resource}")
        response = await call_next(request)
        return response
