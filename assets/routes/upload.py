"""
Module for handling bulk profile uploads.

This module contains the functionality to upload multiple user profiles
at once. It includes routes and functions to manage the upload process,
validate input data, and handle errors.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from assets.src.asset_upload import AssetUpload
from assets.src.schemas import (
    DocumentModel,
    JobInfo,
    ResumeInfo,
    SpreadsheetModel,
    ZipModel,
)
from commons import FileName, RecordNotFoundException
from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin

router = APIRouter(tags=["assets"], prefix="/assets")


@router.post("/bulk_profile", status_code=201)
async def bulk_profile_upload(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    bulk_profile: UploadFile = File(...),
):
    """
    Upload a bulk profile file to be processed.

    The file is stored in the uploads directory and the filename and location
    of the uploaded file are returned to the caller.
    """
    try:
        validated_file = SpreadsheetModel.validate_file(bulk_profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not AssetUpload.upload(validated_file, FileName.BULK_PROFILE):
        raise HTTPException(status_code=500, detail="Failed to upload file")
    return Admin(admin_user_id).process_bulk_profiles()


@router.post("/jd", status_code=201)
async def jd_upload(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    skill: str = Form(...),
    designation: str = Form(...),
    jd: UploadFile = File(...),
):
    """
    Upload a job description file to be processed.

    The file is stored in the uploads directory and the filename and location
    of the uploaded file are returned to the caller.
    """
    try:
        validated_file = DocumentModel.validate_file(jd)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Construct and validate the model; sanitization happens via validators.
    job_info = JobInfo(skill=skill, designation=designation)
    if not AssetUpload.upload(validated_file, FileName.JD, job_info):
        raise HTTPException(status_code=500, detail="Failed to upload file")
    return {"message": "File uploaded successfully"}


@router.post("/question_bank", status_code=201)
async def question_bank_upload(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    skill: str = Form(...),
    designation: str = Form(...),
    question_bank: UploadFile = File(...),
):
    """
    Upload a question bank file to be processed.

    The file is stored in the uploads directory and the filename and location
    of the uploaded file are returned to the caller.
    """
    try:
        validated_file = DocumentModel.validate_file(question_bank)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Construct and validate the model; sanitization happens via validators.
    job_info = JobInfo(skill=skill, designation=designation)
    if not AssetUpload.upload(validated_file, FileName.QUESTION_BANK, job_info):
        raise HTTPException(status_code=500, detail="Failed to upload file")
    return {"message": "File uploaded successfully"}


@router.post("/resume", status_code=201)
async def resume_upload(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    candidate_id: int = Form(...),
    resume: UploadFile = File(...),
):
    """
    Upload a resume file for a specific candidate.

    This endpoint allows an admin user to upload a resume file for a candidate.
    The file is stored in the uploads directory and the filename and location
    of the uploaded file are returned to the caller.

    Parameters:
    - admin_user_id (int): The ID of the admin user making the request,
      extracted from the access token.
    - candidate_id (int): The ID of the candidate whose resume is being uploaded.
    - resume (UploadFile): The resume file to be uploaded.

    Returns:
    - dict: A dictionary with a message indicating the success of the operation.

    Raises:
    - HTTPException: If the file upload fails, or if the admin user is unauthorized to
      access candidate profiles.
    """
    try:
        resume_info = ResumeInfo(candidate_id=candidate_id, uploaded_file=resume)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        if not AssetUpload(resume_info.candidate_id).upload_resume(resume_info):
            raise HTTPException(status_code=500, detail="Failed to upload file")
    except RecordNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return {"message": "File uploaded successfully"}


@router.post("/bulk_resume", status_code=201)
async def bulk_resume_upload(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    bulk_resume: UploadFile = File(...),
):
    """
    Upload a zip file containing resumes to be processed.

    The file is stored in the uploads directory and the filename and location
    of the uploaded file are returned to the caller.
    """
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(status_code=403, detail="Unauthorized")
    try:
        zip_file = ZipModel(uploaded_file=bulk_resume)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AssetUpload().upload_bulk_resumes(zip_file)
