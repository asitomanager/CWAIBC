"""
Defines API routes for managing metadata, such as skills and designations.

This module provides endpoints to fetch and update lists of values (LOVs) like skills and roles.
It ensures proper authorization and handles errors gracefully.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, Form, HTTPException, status

from commons import logger
from meta_data.src import MetaData
from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin

router = APIRouter(tags=["meta_data"])


@router.get("/lov", status_code=200)
async def fetch(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    lov_name: str,
) -> List[str]:
    """
    Retrieve LOV data for a specific LOV name.

    Args:
        admin_user_id (int): The ID of the admin user making the request.
        lov_name (str): The name of the LOV to retrieve.

    Returns:
        List[str]: A list of strings containing the LOV key and LOV value.

    Raises:
        HTTPException: If a permission error occurs or if an internal server error occurs.
    """
    if not Admin(admin_user_id).is_authorized():
        raise PermissionError("User is not authorized to perform this action")
    try:
        return await MetaData().fetch(lov_name)
    except ValueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put("/lov", status_code=200)
async def add(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    lov_name: str = Form(...),
    lov_value: str = Form(...),
) -> dict:
    """
    Add a new value to a given LOV.

    Args:
        admin_user_id (int): The ID of the admin user making the request.
        lov_name (str): The name of the LOV to add to.
        lov_value (str): The value to add to the LOV.

    Returns:
        dict: A dictionary containing a message indicating the success of the operation.

    Raises:
        PermissionError: If the user is not authorized to perform this action.
        HTTPException: If a permission error occurs or if an internal server error occurs.
    """
    if not Admin(admin_user_id).is_authorized():
        raise PermissionError("User is not authorized to perform this action")
    try:
        await MetaData().add(lov_name, lov_value)
        return {"message": f"{lov_name} {lov_value} added successfully"}
    except ValueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# delete
@router.delete("/lov", status_code=200)
async def delete(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    lov_name: str = Form(...),
    lov_value: str = Form(...),
) -> dict:
    """
    Delete a value from a given LOV.

    Args:
        admin_user_id (int): The ID of the admin user making the request.
        lov_name (str): The name of the LOV to delete from.
        lov_value (str): The value to delete from the LOV.

    Returns:
        dict: A dictionary containing a message indicating the success of the operation.

    Raises:
        PermissionError: If the user is not authorized to perform this action.
        HTTPException: If a permission error occurs or if an internal server error occurs.
    """
    if not Admin(admin_user_id).is_authorized():
        raise PermissionError("User is not authorized to perform this action")
    try:
        await MetaData().delete(lov_name, lov_value)
        return {"message": f"{lov_name} {lov_value} deleted successfully"}
    except ValueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
