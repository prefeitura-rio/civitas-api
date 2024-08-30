# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status

from app import config
from app.models import User
from app.oidc import get_current_user
from app.pydantic_models import OIDCUser
from app.utils import validate_cpf


async def get_user(
    user_info: Annotated[OIDCUser, Security(get_current_user, scopes=["profile"])]
) -> User:
    if config.AUTH_PROVIDER_GROUP_USER not in user_info.groups and config.AUTH_PROVIDER_GROUP_AGENT not in user_info.groups:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this application.",
        )

    is_admin = config.AUTH_PROVIDER_GROUP_ADMIN in user_info.groups
    is_user = config.AUTH_PROVIDER_GROUP_USER in user_info.groups
    is_agent = config.AUTH_PROVIDER_GROUP_AGENT in user_info.groups or is_user or is_admin

    user = await User.get_or_none(username=user_info.nickname)
    if user is None:
        user = await User.create(
            username=user_info.nickname,
            full_name=user_info.name,
            cpf=user_info.cpf,
            registration=user_info.matricula,
            agency=user_info.orgao,
            sector=user_info.setor,
            email=user_info.email,
            is_admin=is_admin,
            is_user=is_user,
            is_agent=is_agent,
        )
    else:
        modified = False
        if user.is_admin != is_admin:
            user.is_admin = is_admin
            modified = True
        if user.is_user != is_user:
            user.is_user = is_user
            modified = True
        if user.is_agent != is_agent:
            user.is_agent = is_agent
            modified = True
        if user.full_name != user_info.name:
            user.full_name = user_info.name
            modified = True
        if user.cpf != user_info.cpf:
            user.cpf = user_info.cpf
            modified = True
        if user.registration != user_info.matricula:
            user.registration = user_info.matricula
            modified = True
        if user.agency != user_info.orgao:
            user.agency = user_info.orgao
            modified = True
        if user.sector != user_info.setor:
            user.sector = user_info.setor
            modified = True
        if user.email != user_info.email:
            user.email = user_info.email
            modified = True
        if modified:
            await user.save()

    return user


async def is_agent(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires agent privileges.",
        )

    return user


async def is_user(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires user privileges.",
        )

    return user


async def is_admin(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires admin privileges.",
        )

    return user


async def has_cpf(user: Annotated[User, Depends(get_user)]) -> User:
    if user.cpf is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires a valid CPF. Ask your administrator to update your profile.",
        )

    elif not validate_cpf(user.cpf):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires a valid CPF. Ask your administrator to update your profile.",
        )

    return user
