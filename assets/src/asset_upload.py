"""
Uploader module.

This module provides functionality for uploading files to a designated directory.
It uses environment variables to determine the upload directory and handles file
uploads for different types of files.

Classes:
    UploadFileTpe: An enumeration of file types that can be uploaded.

Functions:
    (None currently defined at the module level)

Variables:
    FILES_DIR: The directory where files will be uploaded, determined by an
        environment variable.
"""

import os
import tempfile
import zipfile

from dotenv import load_dotenv
from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from assets.src.schemas import JobInfo, ResumeInfo, ZipModel, BulkResumeInfo
from commons import (
    DBEnterExitMixin,
    FileName,
    logger,
    InvalidFilenameException,
    InvalidExtensionException,
    InvalidMimeTypeException,
)
from user_management import CandidateORM, RecordNotFoundException

load_dotenv(override=True)
FILES_DIR = os.environ.get("FILES_DIR")
os.makedirs(FILES_DIR, exist_ok=True)


class AssetUpload(DBEnterExitMixin):
    """
    Provides methods to upload files to a designated directory.

    The class provides methods to upload files of different types and handles
    the process of creating directories and writing the files to disk.

    Attributes:
        candidate_id: The ID of the candidate whose files are being uploaded.
        db_helper: A database helper to interact with the database.

    Methods:
        set_resume: Marks a candidate's resume as uploaded.
        upload: Uploads a file to the FILES_DIR directory.
        upload_resume: Uploads a resume file.
    """

    def __init__(self, candidate_id: int = None, db_helper=None):
        self._db_helper = db_helper
        self.candidate_id = candidate_id

    def set_resume(self) -> bool:
        """
        Mark a candidate's resume as uploaded.

        This method updates the database to indicate that a candidate has uploaded
        their resume. It performs the following steps:
        1. Retrieves the candidate record from the database
        2. Sets the resume field to True
        3. Commits the changes to the database

        Returns:
            bool: True if the operation is successful, False otherwise

        Raises:
            RecordNotFoundException: If the candidate record is not found
            SQLAlchemyError: If a database error occurs during the operation
        """
        with self:
            candidate_record = (
                self._db_session.query(CandidateORM)
                .filter(CandidateORM.id == self.candidate_id)
                .first()
            )
            if not candidate_record:
                raise RecordNotFoundException(
                    self.candidate_id, message="Candidate not found"
                )
            try:
                candidate_record.resume = True
                self._db_session.commit()
                return True
            except SQLAlchemyError as e:
                logger.error("Database error occurred: %s", e)
                return False

    @staticmethod
    def upload(
        input_file: UploadFile,
        input_file_type: FileName,
        job_data: JobInfo = None,
    ) -> bool:
        """
        Upload a file to the FILES_DIR directory.

        Args:
        input_file: The file to upload.
        input_file_type: The type of the file to upload.

        Returns:
        True if the upload was successful, False otherwise.
        """
        input_extension = input_file.filename.split(".")[-1]
        base_location = [FILES_DIR]

        if job_data:
            base_location.append(job_data.skill)
            base_location.append(job_data.designation)

        os.makedirs(os.path.join(*base_location), exist_ok=True)
        base_location.append(f"{input_file_type.value}.{input_extension}")
        file_location = os.path.join(*base_location)

        # Check for empty file
        if input_file.file.seek(0, os.SEEK_END) == 0:
            logger.warning("File is empty: %s", input_file.filename)
            return False

        try:
            input_file.file.seek(0, os.SEEK_SET)  # Reset file pointer
            with open(file_location, "wb") as f:
                content = input_file.file.read()
                logger.info("Uploading file of type: %s", type(content))
                f.write(content)
            logger.info("File uploaded to: %s", file_location)
        except (IOError, OSError, PermissionError) as e:
            logger.exception('Error uploading file "%s": %s', input_file.filename, e)
            return False
        return True

    def upload_resume(self, resume_info: ResumeInfo) -> bool:
        """
        Uploads a resume file.

        Args:
            resume_info: The ResumeInfo that contains the file to upload.

        Returns:
            True if the upload was successful, False otherwise.
        """
        input_file = resume_info.uploaded_file
        self.candidate_id = resume_info.candidate_id
        input_filename: str = input_file.filename
        input_extension = input_file.filename.split(".")[-1]
        to_path: str = os.path.join(
            FILES_DIR,
            str(self.candidate_id),
            f"{FileName.RESUME.value}.{input_extension}",
        )
        try:
            if input_file.file.seek(0, os.SEEK_END) > 0:
                os.makedirs(os.path.dirname(to_path), exist_ok=True)
                with open(to_path, "wb") as f:
                    input_file.file.seek(0, os.SEEK_SET)
                    content: bytes = input_file.file.read()
                    logger.info("Uploading file of type: %s", type(content))
                    f.write(content)
            logger.info("File uploaded to: %s", to_path)
        except (IOError, OSError, PermissionError) as e:
            logger.exception('Error uploading file "%s": %s', input_filename, e)
            return False
        return self.set_resume()

    def upload_bulk_resumes(self, zip_file: ZipModel) -> dict[str, list[str]]:
        """
        Processes a zip file containing resumes. Attempts to upload each valid resume.
        Returns a tuple of (invalid_filenames, upload_failures).
        """
        invalid_filenames: list[str] = []
        invalid_extensions: list[str] = []
        invalid_mime_types: list[str] = []
        upload_failures: list[str] = []
        successful_uploads: list[str] = []
        resume_fh = zip_file.uploaded_file
        with tempfile.TemporaryDirectory() as tmpdirname:
            with zipfile.ZipFile(resume_fh.file) as zip_fh:
                zip_fh.extractall(tmpdirname)
                for filename in os.listdir(tmpdirname):
                    file_path = os.path.join(tmpdirname, filename)
                    try:
                        bulk_resume_info = BulkResumeInfo(file_path=file_path)
                    except InvalidFilenameException:
                        invalid_filenames.append(filename)
                        continue
                    except InvalidExtensionException:
                        invalid_extensions.append(filename)
                        continue
                    except InvalidMimeTypeException:
                        invalid_mime_types.append(filename)
                        continue

                    to_path: str = os.path.join(
                        FILES_DIR,
                        str(bulk_resume_info.candidate_id),
                        f"{FileName.RESUME.value}{bulk_resume_info.extension}",
                    )
                    try:
                        os.makedirs(os.path.dirname(to_path), exist_ok=True)
                        with open(to_path, "wb") as f:
                            with open(file_path, "rb") as resume_fh:
                                content: bytes = resume_fh.read()
                                logger.info("Uploading file of type: %s", type(content))
                                f.write(content)
                        logger.info("File uploaded to: %s", to_path)
                        self.candidate_id = bulk_resume_info.candidate_id
                        if self.set_resume():
                            successful_uploads.append(filename)
                        else:
                            upload_failures.append(filename)
                    except (IOError, OSError, PermissionError) as e:
                        logger.exception('Error uploading file "%s": %s', filename, e)
                        upload_failures.append(filename)
        return {
            "invalid_filenames": invalid_filenames,
            "invalid_extensions": invalid_extensions,
            "invalid_mime_types": invalid_mime_types,
            "upload_failures": upload_failures,
            "successful_uploads": successful_uploads,
        }
