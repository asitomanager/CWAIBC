""" Helper functions for the user service. """

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from commons import logger

load_dotenv(override=True)
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
# >>> import secrets
# >>> secrets.token_hex()
# SECRET_KEY = "c675e7ca94f91314b650ff37c9d9fd743ad2d256de69fe2a8a603ed3478e6d47"
# ALGORITHM = "HS256"


def generate_jwt_token(user_id: int, token_usage="access"):
    """Create an access or refresh token for the user."""
    logger.info("Generating %s token..", token_usage)
    if token_usage == "access":
        expires_delta = timedelta(minutes=60)
    elif token_usage == "refresh":
        expires_delta = timedelta(days=7)
    else:
        raise ValueError("Invalid token usage")
    to_encode = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + expires_delta,
        "token_usage": token_usage,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def add_token_to_revocation_list(token: str):
    """This function should add the token to some persistent store.
    Implement the logic according to our storage solution."""


def get_current_refresh_user(
    token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/login"))]
):
    """Get the current user from the refresh token."""
    try:
        logger.info("Decoding refresh token..")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise JWTError("User ID is None in payload")
        if payload.get("token_usage") != "refresh":
            raise JWTError("Invalid Token usage. Refresh token expected")
        return {"user_id": user_id}
    except JWTError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_current_user(
    token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/login"))]
):
    """Get the current user from the token."""
    try:
        logger.info("Decoding access token..")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise JWTError("User ID is None in payload")
        if payload.get("token_usage") != "access":
            raise JWTError("Invalid Token usage. access token expected")
        return user_id
    except JWTError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
