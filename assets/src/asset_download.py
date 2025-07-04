"""
Module for handling asset downloads.

This module contains the functionality to download assets
from the server. It includes routes and functions to manage the
download process, validate requests, and handle errors.
"""

import glob
import os
import shutil
from typing import Tuple

from dotenv import load_dotenv

from commons import FileName, logger, DBEnterExitMixin

load_dotenv()
FILES_DIR = os.environ.get("FILES_DIR")


class AssetDownload(DBEnterExitMixin):
    """
    Class for handling asset downloads.

    This class provides methods to download assets from the server.
    It includes functionality to handle the download process, validate
    requests, and handle errors.
    """

    def __init__(self, candidate_id: int, db_helper=None):
        self._db_helper = db_helper
        self.candidate_id = candidate_id

    def get_resume(self) -> Tuple[str, str]:
        """
        Retrieve a candidate's resume file.

        This method searches for the resume file in the candidate's directory
        using a pattern match. It supports any file extension for the resume.

        Returns:
            Tuple[str, str]: A tuple containing:
                - str: The full path to the resume file
                - str: The filename for download purposes

        Raises:
            FileNotFoundError: If no resume file is found for the candidate
        """
        pattern = os.path.join(
            FILES_DIR, str(self.candidate_id), f"{FileName.RESUME.value}.*"
        )
        matching_files = glob.glob(pattern)
        if matching_files:
            file_path = matching_files[0]
            download_filename = os.path.basename(file_path)
            return file_path, download_filename
        logger.error("Resume not found for candidate ID: %s", self.candidate_id)
        raise FileNotFoundError("Resume not found !")

    def get_documents(self) -> str:
        """
        Retrieve all documents for a candidate as a zip file.

        This method creates and returns a zip file containing all documents
        associated with a specific candidate. The documents are stored in the
        candidate's directory.

        The method performs the following checks:
        1. Verifies if the candidate's directory exists
        2. Verifies if the directory contains any files
        3. Creates a zip file of all documents if they exist

        Returns:
            str: The full path to the zip file containing all documents

        Raises:
            FileNotFoundError: If the candidate's directory does not exist
            FileNotFoundError: If the candidate's directory is empty
        """
        zip_file_path = os.path.join(FILES_DIR, f"{self.candidate_id}_documents.zip")
        if not os.path.exists(zip_file_path):
            candidate_folder = os.path.join(FILES_DIR, str(self.candidate_id))
            # Check if the candidate's folder exists
            if not os.path.exists(candidate_folder):
                logger.error(
                    "The folder for candidate ID %s does not exist.", self.candidate_id
                )
                raise FileNotFoundError(
                    f"The folder for candidate ID {self.candidate_id} does not exist."
                )

            # Check if the folder is empty
            if not os.listdir(candidate_folder):
                logger.error(
                    "The folder for candidate ID %s is empty.", self.candidate_id
                )
                raise FileNotFoundError(
                    f"The folder for candidate ID {self.candidate_id} is empty."
                )

            logger.info("Creating zip file for candidate ID: %s", self.candidate_id)
            # Create a zip file containing all files in the candidate's folder
            shutil.make_archive(
                zip_file_path.replace(".zip", ""), "zip", candidate_folder
            )
        return zip_file_path

    def get_analysis_report(self) -> Tuple[str, str]:
        """
        Retrieve the analysis report for a candidate.

        This method locates and returns the path to the analysis report
        for a specific candidate. The report is stored as a PDF file
        in the candidate's directory.

        Returns:
            Tuple[str, str]: A tuple containing:
                - str: The full path to the analysis report file
                - str: The filename for download purposes

        Raises:
            FileNotFoundError: If the analysis report file is not found
        """
        file_path = os.path.join(
            FILES_DIR, str(self.candidate_id), f"{FileName.ANALYSIS_REPORT.value}.pdf"
        )
        if not os.path.exists(file_path):
            logger.error(
                "Analysis report not found for candidate ID: %s", self.candidate_id
            )
            raise FileNotFoundError("Analysis report not found !")
        download_filename = f"{self.candidate_id}_{FileName.ANALYSIS_REPORT.value}.pdf"
        return file_path, download_filename
