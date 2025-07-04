"""
This module contains the admin routes for the user management system.

It provides endpoints for admins to manage candidate profiles and other admin-related tasks.
"""

from typing import Annotated, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from commons import AuthorizationException, RecordNotFoundException
from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin
from user_management.src.schemas import CandidateResponseInfo

router = APIRouter(tags=["admin"])


@router.get(
    "/candidates",
    response_model=Dict[str, Union[List[CandidateResponseInfo], int]],
    status_code=status.HTTP_200_OK,
)
def get_all_candidates(
    user_id: Annotated[int, Depends(get_current_user)],
    page_num: Optional[int] = Query(
        1, alias="page_num", description="Page number of the results"
    ),
    results_per_page: Optional[int] = Query(
        10, alias="results_per_page", description="Number of results per page"
    ),
    interview_status: Optional[str] = Query(
        "ALL", description="Status of the interview to filter candidates"
    ),
):
    """
    Retrieve a paginated list of candidate profiles for an admin user.

    This endpoint returns a paginated list of candidate profiles based on the
    provided page number. The admin user must be authorized to access this
    information.

    Parameters:
    - user_id (int): The ID of the current user, extracted from the access token.
    - page_num (int, optional): The page number for retrieving candidate profiles,
      defaulting to 1.
    - results_per_page (int, optional): Number of profiles per page, defaulting to 10.
    - interview_status (str, optional): Status of the interview to filter candidates, defaulting to 'ALL'.

    Returns:
    - Dict[str, Union[List[CandidateResponseInfo], int]]: A dictionary containing the list of candidate profiles for
    the specified page and the total count of candidates.

    Raises:
    - HTTPException: If the user is unauthorized to access candidate profiles.
    """

    try:
        return Admin(user_id).get_all_candidates(
            page_num, interview_status, results_per_page
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except AuthorizationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.get("/candidates/export", response_class=StreamingResponse)
def export_candidates(user_id: Annotated[int, Depends(get_current_user)]):
    """
    Export all candidate details to a spreadsheet.
    """
    try:
        return Admin(user_id).export_candidates_to_excel()
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/candidate/{candidate_id}",
    response_model=CandidateResponseInfo,
    status_code=status.HTTP_200_OK,
)
def get_candidate(
    user_id: Annotated[int, Depends(get_current_user)],
    candidate_id: int,
):
    """
    Retrieve a candidate's profile.

    This endpoint retrieves a candidate's profile for an admin user. The admin
    user must be authorized to access this information.

    Parameters:
    - user_id (int): The ID of the current user, extracted from the access token.
    - candidate_id (int): The ID of the candidate whose profile is to be retrieved.

    Returns:
    - CandidateResponseInfo: The profile of the candidate identified by the given candidate ID.

    Raises:
    - HTTPException: If the user is unauthorized to access candidate profiles or if the candidate is not found.
    """
    try:
        return Admin(user_id).get_candidate(candidate_id)
    except AuthorizationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/search",
    response_model=List[CandidateResponseInfo],
    status_code=status.HTTP_200_OK,
)
def search_candidates(
    user_id: Annotated[int, Depends(get_current_user)],
    search_text: str = Query(
        "", description="Text to search for in candidate profiles"
    ),
):
    """
    Search for candidates by name or email.

    This endpoint searches for candidates based on the provided search text.
    The admin user must be authorized to access this information.

    Parameters:
    - user_id (int): The ID of the current user, extracted from the access token.
    - search_text (str): The text to search for in candidate profiles.

    Returns:
    - List[CandidateResponseInfo]: A list of candidate profiles matching the search text.

    Raises:
    - HTTPException: If the user is unauthorized to access candidate profiles.
    """
    try:
        return Admin(user_id).search_candidates(search_text)
    except AuthorizationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
