"""
Module for handling profile downloads.

This module contains the functionality to download user profiles
from the server. It includes routes and functions to manage the
download process, validate requests, and handle errors.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from user_management.routes.lib import get_current_user
from user_management.src.admin import Admin
from assets.src.asset_download import AssetDownload

router = APIRouter(tags=["assets"], prefix="/assets")


@router.get("/resume", status_code=200)
async def get_resume(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    candidate_id: int = Query(...),
):
    """
    Retrieve the resume for a specific candidate.

    This endpoint allows an admin user to download a candidate's resume if
    they have the appropriate permissions. The resume file is returned as a
    downloadable file.

    Parameters:
    - candidate_user_id (int): The ID of the candidate whose resume is being requested.
    - admin_user_id (int): The ID of the admin user making the request,
      extracted from the access token.

    Returns:
    - FileResponse: A response containing the resume file to be downloaded.

    Raises:
    - HTTPException: If the resume is not found.
    """
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    try:
        file_path, filename = AssetDownload(candidate_id).get_resume()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return FileResponse(file_path, filename=filename)


@router.get("/documents", status_code=200, response_class=FileResponse)
async def get_documents(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    candidate_id: int = Query(...),
):
    """
    Retrieve the documents for a specific candidate.

    This endpoint allows an admin user to download a candidate's documents if
    they have the appropriate permissions. The documents are returned as a
    downloadable file.

    Parameters:
    - candidate_user_id (int): The ID of the candidate whose documents are being requested.
    - admin_user_id (int): The ID of the admin user making the request,
      extracted from the access token.

    Returns:
    - FileResponse: A response containing the documents file to be downloaded.

    Raises:
    - HTTPException: If the documents are not found.
    """
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    try:
        file_path = AssetDownload(candidate_id).get_documents()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return FileResponse(
        file_path,
        media_type="application/zip",
        filename=f"{candidate_id}_documents.zip",
    )


# Analysis report download
@router.get("/analysis-report", status_code=200, response_class=FileResponse)
async def get_analysis_report(
    admin_user_id: Annotated[int, Depends(get_current_user)],
    candidate_id: int = Query(...),
):
    """
    Retrieve the analysis report for a specific candidate.

    This endpoint allows an admin user to download an analysis report for a candidate
    if they have the appropriate permissions. The report is returned as a downloadable
    file.

    Parameters:
    - candidate_user_id (int): The ID of the candidate whose analysis report is being requested.
    - admin_user_id (int): The ID of the admin user making the request,
      extracted from the access token.

    Returns:
    - FileResponse: A response containing the analysis report file to be downloaded.

    Raises:
    - HTTPException: If the analysis report is not found.
    """
    if not Admin(admin_user_id).is_authorized():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    try:
        file_path, filename = AssetDownload(candidate_id).get_analysis_report()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
    )
