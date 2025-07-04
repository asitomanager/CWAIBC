"""Auth routes for the user service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from commons import AuthenticationException, AuthorizationException, logger
from user_management.routes.lib import (
    add_token_to_revocation_list,
    generate_jwt_token,
    get_current_refresh_user,
    get_current_user,
)
from user_management.src.candidate import Candidate
from user_management.src.schemas import ChangePasswordRequest
from user_management.src.user import User

router = APIRouter(tags=["auth"])


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    login_info: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    """Login a user and return an access token."""
    logger.info("User login request received")
    try:
        user_id, name, role = User().login(login_info.username, login_info.password)
        if role == "Candidate":
            if Candidate(user_id).credentials_expired():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credentials expired !",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        access_token = generate_jwt_token(user_id, "access")
        refresh_token = generate_jwt_token(user_id, "refresh")

        return {
            "user_id": user_id,
            "name": name,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": role,
            # "token_type": "Bearer",
        }
    except (AuthorizationException, AuthenticationException) as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.delete("/logout", status_code=status.HTTP_205_RESET_CONTENT)
def logout(
    access_token: str = Header(None),
    refresh_token: str = Header(None),
):
    """
    Invalidate a user's access and refresh tokens.

    This function receives an access token and a refresh token, presumably belonging to a user,
    and adds them to a revocation list to prevent further use.

    Args:
        access_token (str): The access token issued to the user.
        refresh_token (str): The refresh token issued to the user.

    Returns:
        dict: A dictionary with a message indicating successful logout.

    Raises:
        HTTPException: If either the access token or refresh token is not provided.
    """
    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token and refresh token are required.",
        )
    # Invalidate the access token
    add_token_to_revocation_list(access_token)

    # Invalidate the refresh token
    add_token_to_revocation_list(refresh_token)


@router.get("/refresh")
def refresh(user_id: Annotated[int, Depends(get_current_refresh_user)]):
    """Refresh access token."""
    try:
        new_access_token = generate_jwt_token(user_id)
        return {"access_token": new_access_token}
    except AuthorizationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) + " Please provide valid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Securely store your refresh tokens, as they have a longer life than access tokens.
    # Implement token revocation for refresh tokens to improve security.
    # Handle the edge cases in your token refresh logic, such as what happens
    # if a refresh token is expired or revoked.


@router.patch("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    user_id: Annotated[int, Depends(get_current_user)], request: ChangePasswordRequest
):
    """
    Change the password for the authenticated user.
    """
    try:
        user_obj = User(user_id=user_id)
        user_obj.set_password(request)
        return {"detail": "Password changed successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AuthenticationException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from exc
