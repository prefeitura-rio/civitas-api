# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_cache.decorator import cache
from httpx import AsyncClient
from jose import jwt

from app import config
from app.pydantic_models import OIDCUser, Token

oidc_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@cache(expire=config.OIDC_GET_USER_TOKEN_CACHE_TTL)
async def get_user_token(username: str, password: str) -> tuple[str, str, float]:
    async with AsyncClient() as client:
        response = await client.post(
            config.OIDC_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": config.OIDC_CLIENT_ID,
                "client_secret": config.OIDC_CLIENT_SECRET,
                "scope": "profile cpf civitas email",
            },
        )
        if response.status_code != 200:
            raise AuthError(response.json(), response.status_code)
        data = response.json()
        expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        return (data["access_token"], data["token_type"], expires_at.timestamp())


async def authenticate_user(form_data: OAuth2PasswordRequestForm) -> Token:
    # Mock authentication for test environment
    import os
    env = os.getenv("ENVIRONMENT", "dev")
    if env == "test":
        return await authenticate_user_test(form_data)
    
    token, token_type, expires_at = await get_user_token(
        username=form_data.username, password=form_data.password
    )
    expires_in = datetime.fromtimestamp(expires_at) - datetime.now()
    return Token(
        access_token=token, token_type=token_type, expires_in=expires_in.seconds
    )


async def authenticate_user_test(form_data: OAuth2PasswordRequestForm) -> Token:
    """Mock authentication for test environment."""
    from app.models import User
    
    # Check if user exists in database
    user = await User.filter(username=form_data.username).first()
    if not user:
        raise AuthError(
            {"code": "invalid_credentials", "description": "Invalid username or password"},
            401,
        )
    
    # In test mode, accept any password
    # Generate a mock JWT token
    mock_payload = {
        "sub": str(user.id),
        "preferred_username": user.username,
        "name": user.full_name,
        "email": user.email,
        "cpf": user.cpf,
        "groups": []
    }
    
    # Add groups based on user permissions
    if user.is_admin:
        mock_payload["groups"].append(config.AUTH_PROVIDER_GROUP_ADMIN)
    if user.is_user:
        mock_payload["groups"].append(config.AUTH_PROVIDER_GROUP_USER)
    if user.is_agent:
        mock_payload["groups"].append(config.AUTH_PROVIDER_GROUP_AGENT)
    
    # Create a simple mock token (not a real JWT, just for testing)
    mock_token = f"test_token_{user.username}_{user.id}"
    
    return Token(
        access_token=mock_token,
        token_type="Bearer",
        expires_in=3600  # 1 hour
    )


async def get_current_user(authorization_header: Annotated[str, Depends(oidc_scheme)]):
    # Mock user validation for test environment (only for manual testing, not integration tests)
    import os
    import sys
    env = os.getenv("ENVIRONMENT", "dev")
    
    # Check if we're running in pytest (integration tests use dependency overrides)
    is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
    
    # Only use manual test authentication if we're in test mode but NOT in pytest
    if env == "test" and not is_pytest:
        return await get_current_user_test(authorization_header)
    elif env == "test" and is_pytest:
        # In integration tests, let the dependency override handle this
        # This will fall through to the normal JWT validation which will be overridden
        pass
    
    try:
        unverified_header = jwt.get_unverified_header(authorization_header)
    except Exception:
        raise AuthError(
            {"code": "invalid_jwt_header", "description": "Unable to parse JWT header"},
            401,
        )

    # Check if 'kid' exists in the header
    if "kid" not in unverified_header:
        raise AuthError(
            {
                "code": "missing_kid",
                "description": "The JWT header is missing the 'kid' field.",
            },
            401,
        )

    rsa_key = {}
    algorithms = ""
    for key in config.JWS["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            algorithms = key["alg"]

    if not rsa_key:
        raise AuthError(
            {
                "code": "invalid_rsa",
                "description": "Unable to find a valid RSA key.",
            },
            401,
        )

    try:
        payload = jwt.decode(
            authorization_header,
            rsa_key,
            algorithms=algorithms,
            audience=config.OIDC_CLIENT_ID,
            issuer=config.OIDC_ISSUER_URL,
        )
    except jwt.ExpiredSignatureError:
        raise AuthError(
            {"code": "token_expired", "description": "token is expired"}, 401
        )
    except jwt.JWTClaimsError:
        raise AuthError(
            {
                "code": "invalid_claims",
                "description": "Incorrect claims, please check the audience and issuer",
            },
            401,
        )
    except Exception:
        raise AuthError(
            {
                "code": "invalid_jwt",
                "description": "Unable to parse JWT token.",
            },
            401,
        )

    return OIDCUser(**payload)


async def get_current_user_test(authorization_header: str):
    """Mock user validation for test environment."""
    from app.pydantic_models import OIDCUser
    from datetime import datetime
    
    print("DEBUG: get_current_user_test called")
    print(f"DEBUG: Authorization header = {authorization_header}")
    
    # Always return a mock user for test environment
    print("DEBUG: Creating mock user")
    
    mock_user = OIDCUser(
        iss="http://localhost:8080",
        sub="9140579b-e4e2-4c2f-a399-4b55ce03c175",
        aud="test-client",
        exp=int(datetime.now().timestamp()) + 3600,
        iat=int(datetime.now().timestamp()),
        auth_time=int(datetime.now().timestamp()),
        acr="1",
        azp="test-client",
        uid="9140579b-e4e2-4c2f-a399-4b55ce03c175",
        email="test.user@example.com",
        email_verified=True,
        name="Test User",
        given_name="Test",
        preferred_username="test.user",
        nickname="test.user",
        groups=["test-admin", "test-user"],
        matricula="12345",
        orgao="Test Agency",
        setor="Test Sector",
        cpf="12345678901"
    )
    
    print("DEBUG: Mock user created successfully")
    return mock_user
