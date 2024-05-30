# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status

from app import config
from app.models import User
from app.oidc import get_current_user
from app.pydantic_models import OIDCUser


async def get_user(
    user_info: Annotated[OIDCUser, Security(get_current_user, scopes=["profile"])]
) -> User:
    if config.AUTH_PROVIDER_GROUP_USER not in user_info.groups:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this application.",
        )

    is_admin = config.AUTH_PROVIDER_GROUP_ADMIN in user_info.groups

    user = await User.get_or_none(username=user_info.nickname)
    if user is None:
        user = await User.create(username=user_info.nickname, is_admin=is_admin)
    else:
        if user.is_admin != is_admin:
            user.is_admin = is_admin
            await user.save()

    return user


async def is_admin(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return user
