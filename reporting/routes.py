"""Routes for reporting-related endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from reporting.src.reports import Reports
from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin

router = APIRouter(tags=["reporting"], prefix="/reporting")


@router.get("/dashboard", status_code=200)
async def dashboard(user_id: Annotated[int, Depends(get_current_user)]):
    """
    Retrieves the dashboard information for the given user.

    This endpoint retrieves the dashboard information for the given user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        dict: A dictionary containing the dashboard information.

    Raises:
        HTTPException: If the user does not have permission to access the dashboard.
    """
    # Can be refactored and moved to reporting/src/reports.py
    try:
        return Admin(user_id).get_dashboard()
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get("/timeline", status_code=200)
async def get_timeline_data(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    duration: Annotated[
        str,
        Query(
            description="Time period: '3 months', '30 days', or '7 days'",
            enum=["3 Months", "30 Days", "7 Days"],
        ),
    ] = "3 Months",
):
    """
    Retrieves the timeline data for the given user.

    This endpoint retrieves the timeline data for the given user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        dict: A dictionary containing the timeline data.

    Raises:
        HTTPException: If the user does not have permission to access the timeline data.
    """
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(status_code=403, detail="Unauthorized")
    try:
        reports = Reports()
        if "Days" in duration:
            return reports.get_completed_interviews_counts_by_days(duration=duration)
        return reports.get_completed_interviews_counts_by_month(duration=duration)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
