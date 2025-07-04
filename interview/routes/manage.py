"""
manage.py

This module defines the FastAPI router for managing interview scheduling and related operations.
It includes endpoints for inviting candidates to interviews, checking prerequisites, and handling errors
related to missing candidates or interview documents.

Key functionalities:
- Invite candidates to interviews.
- Check if required documents are present.
- Handle exceptions and log errors for better traceability.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from commons import logger
from commons.src.exceptions import RecordNotFoundException
from interview.src.interview_manager import InterviewManager
from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin

router = APIRouter(tags=["interview"], prefix="/interview")


class CandidateIdListInfo(BaseModel):
    id_list: List[int]


@router.patch("/schedule")
async def schedule_interview(
    admin_id: Annotated[int, Depends(get_current_user)],
    candidate_id_info: CandidateIdListInfo,
) -> dict[str, str]:
    """
    Schedules an interview for a list of candidates.

    Parameters:
    - admin_id (Annotated[int, Depends(get_current_user)]): The ID of the admin user inviting the candidates.
    - candidate_id_list (List[int]): A list of IDs of the candidates being invited.

    Returns:
    - dict[str, str]: A dictionary containing a message indicating the success of the operation.

    Raises:
    - HTTPException: If the admin user lacks permission to schedule an interview or if the
      candidate is not found.
    """
    if not candidate_id_info.id_list:
        raise HTTPException(status_code=400, detail="No candidates specified")

    admin_obj = Admin(admin_id)
    candidate_not_found_list, docs_not_found_list, scheduled_list = [], [], []
    for candidate_id in candidate_id_info.id_list:
        try:
            interview_obj = InterviewManager(candidate_id)
            if not interview_obj.pre_requisites():
                docs_not_found_list.append(candidate_id)
                continue
            admin_obj.invite_candidate(candidate_id)
            scheduled_list.append(candidate_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except RecordNotFoundException:
            candidate_not_found_list.append(candidate_id)

    response_messages = []
    if candidate_not_found_list:
        response_messages.append(
            f"Candidates not found: {', '.join(map(str, candidate_not_found_list))}"
        )
    if docs_not_found_list:
        response_messages.append(
            f"JD or resume or questionnaire not found for: {', '.join(map(str, docs_not_found_list))}"
        )
    if scheduled_list:
        response_messages.append(
            f"Interview scheduled for: {', '.join(map(str, scheduled_list))}"
        )

    message = "\n".join(response_messages)
    logger.info(message)
    return {"message": message}
