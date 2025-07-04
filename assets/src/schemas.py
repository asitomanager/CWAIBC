"""
This module defines Pydantic models and schemas for file uploading functionality.

It includes the BulkProfile model which validates uploaded files for bulk profile operations.
"""

import os
from typing import Set

import magic
from fastapi import File, UploadFile
from pydantic import BaseModel, field_validator

from commons import (
    logger,
    InvalidExtensionException,
    InvalidMimeTypeException,
    InvalidFilenameException,
)


class FileValidations(BaseModel):
    """
    A Pydantic model that defines validation rules for uploaded files.

    This class provides a way to validate uploaded files by checking
    their MIME type and file extension.
    """

    @field_validator("uploaded_file", check_fields=False)
    @classmethod
    def validate_file(cls, value: UploadFile) -> UploadFile:
        """
        Validates an uploaded file by checking its MIME type and file extension.

        This function checks if the uploaded file's MIME type is in the list of
        allowed content types and if the file extension is in the list of allowed
        file extensions. If the file does not meet these criteria, a ValueError
        is raised.

        Args:
            value (UploadFile): The file to validate, provided by the client.

        Returns:
            UploadFile: The validated file.

        Raises:
            ValueError: If the file's MIME type or extension is not allowed.
        """
        if value.content_type not in cls.Config.allowed_mime_types:
            logger.error("Invalid file type: %s", value.content_type)
            raise ValueError(
                f"Invalid file type. Allowed types are: {', '.join(cls.Config.allowed_extensions)}"
            )
        file_extension = os.path.splitext(value.filename)[1].lower()
        if file_extension not in cls.Config.allowed_extensions:
            logger.error("Invalid file extension: %s", file_extension)
            raise ValueError(
                "Invalid file extension. Allowed extensions are: "
                + ", ".join(cls.Config.allowed_extensions)
            )
        return value


class SpreadsheetModel(FileValidations):
    """
    Pydantic model for validating bulk profile upload files.

    This class defines the structure and validation rules for files
    uploaded for bulk profile operations.
    """

    uploaded_file: UploadFile

    class Config:
        """
        The configuration class for the SpreadsheetModel.

        This class defines the configuration options for the SpreadsheetModel.
        """

        allowed_mime_types: Set[str] = {
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        allowed_extensions: Set[str] = {".xlsx"}


class DocumentModel(FileValidations):
    """
    Pydantic model for validating uploaded documents.

    This class defines the structure and validation rules for files
    uploaded for document storage.
    """

    uploaded_file: UploadFile = File(...)

    class Config:
        """
        Configuration for validating uploaded documents.

        This class defines the allowed MIME types and file extensions
        for documents that can be uploaded.
        """

        allowed_mime_types: Set[str] = {
            # "application/pdf",
            # "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        # allowed_extensions: Set[str] = {".pdf", ".doc", ".docx"}
        allowed_extensions: Set[str] = {".docx"}


class ResumeDocumentModel(FileValidations):
    """
    Pydantic model for validating uploaded resume files.

    This class defines the structure and validation rules for files
    uploaded for resume storage.
    """

    uploaded_file: UploadFile = File(...)

    class Config:
        """
        Configuration for validating uploaded PDF files.

        This class defines the allowed MIME types and file extensions
        for PDFs that can be uploaded.
        """

        allowed_mime_types: Set[str] = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }
        allowed_extensions: Set[str] = {".pdf", ".docx", ".doc"}


class ResumeInfo(ResumeDocumentModel):
    """
    Represents a resume uploaded for a candidate.

    Attributes:
        candidate_id (int): The ID of the candidate who uploaded the resume.
    """

    candidate_id: int


class JobInfo(BaseModel):
    """
    Represents job-related data for a candidate.

    Attributes:
        skill (str): The skill set associated with the job.
        designation (str): The role or position for the job.
    """

    skill: str
    designation: str

    @field_validator("skill", "designation")
    @classmethod
    def sanitize_input(cls, value: str) -> str:
        return value.strip().upper()


class ZipModel(FileValidations):
    """
    Pydantic model for validating uploaded zip files.

    This class defines the structure and validation rules for files
    uploaded for zip storage.
    """

    uploaded_file: UploadFile = File(...)

    class Config:
        """
        Configuration for validating uploaded zip files.

        This class defines the allowed MIME types and file extensions
        for zip files that can be uploaded.
        """

        allowed_mime_types: Set[str] = {
            "application/zip",
            "application/x-zip-compressed",
        }
        allowed_extensions: Set[str] = {".zip"}


magic_mime = magic.Magic(mime=True)


class BulkResumeInfo(BaseModel):
    """
    Pydantic model for validating bulk resume files.

    This class defines the structure and validation rules for files
    uploaded for bulk resume storage.
    """

    file_path: str

    @property
    def candidate_id(self):
        """
        Returns the candidate ID extracted from the file path.
        """
        return int(os.path.splitext(os.path.basename(self.file_path))[0])

    @property
    def extension(self):
        """
        Returns the file extension extracted from the file path.
        """
        return os.path.splitext(os.path.basename(self.file_path))[1].lower()

    @field_validator("file_path", mode="after")
    @classmethod
    def validate_file(cls, v):
        """
        Validates the file path for candidate_id, extension, and MIME type.
        """
        allowed_extensions = ResumeDocumentModel.Config.allowed_extensions
        allowed_mime_types = ResumeDocumentModel.Config.allowed_mime_types

        # Check if file name without extension is valid integer
        candidate_id, extension = os.path.splitext(os.path.basename(v))
        if not candidate_id.isdigit():
            raise InvalidFilenameException(candidate_id)

        extension = extension.lower()
        if extension not in allowed_extensions:
            raise InvalidExtensionException(extension)

        # Check MIME type using python-magic
        content_type = magic_mime.from_file(v)
        if content_type not in allowed_mime_types:
            raise InvalidMimeTypeException(content_type)

        return v
