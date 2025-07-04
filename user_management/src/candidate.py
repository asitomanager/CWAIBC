"""
This module contains the Candidate class, which represents a candidate in user management system.
It provides methods for managing candidate data and interactions.
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from commons import ConfigLoader, InterviewStatus, RecordNotFoundException, logger
from interview import InterviewORM
from user_management.models.candidate import CandidateORM
from user_management.src.user import User

load_dotenv(override=True)
FILES_DIR = os.environ.get("FILES_DIR")


class Candidate(User):
    """
    Represents a candidate in the user management system.

    This class extends the User class and provides additional functionality
    specific to candidates, such as managing candidate data and interactions.
    """

    __CONFIG_PATH = os.path.join("commons", "config.jsonc")

    def __init__(self, user_id: int = None, db_helper=None):
        super().__init__(user_id, db_helper)
        self.__config = ConfigLoader.get_config(self.__CONFIG_PATH)
        if user_id:
            self.user_id = user_id
            self._set_user_record_by_id()

    def credentials_expired(self) -> bool:
        """
        Check if the user's interview period has expired.

        This method checks whether the interview period for the user identified
        by the current user ID has expired based on the email timestamp and the
        configured expiration hours. If the period has expired, the user is
        deactivated.

        Returns:
            bool: True if the interview period has expired, False otherwise.

        """
        with self:
            interview = (
                self._db_session.query(InterviewORM)
                .filter(InterviewORM.candidate_id == self.user_id)
                .filter(InterviewORM.status == InterviewStatus.SCHEDULED.value)
                .first()
            )
            if not interview:
                return True

            if datetime.now() > (
                interview.email_datetime
                + timedelta(hours=self.__config["email_expiration_hours"])
            ):
                self.deactivate()
                logger.warning(
                    "Candidate %s's interview period has expired.", self.user_id
                )
                return True
        return False

    def _set_user_record_by_id(self):
        if not self.user_id:
            raise ValueError("User ID is required")
        with self:
            self.user_profile = (
                self._db_session.query(CandidateORM)
                .filter(CandidateORM.id == self.user_id)
                .first()
            )
        if not self.user_profile:
            raise RecordNotFoundException(self.user_id)

    def update_interview_status(self, status: InterviewStatus):
        """
        Update the interview status of the candidate.

        This method updates the interview status of the candidate identified by
        the current user ID to the given status. The status is updated in the
        database and the method returns after committing the changes.

        Args:
            status (InterviewStatus): The new status of the candidate.

        Returns:
            None
        """
        with self:
            self._db_session.query(InterviewORM).filter(
                InterviewORM.candidate_id == self.user_id
            ).update({"status": status.value})
            self._db_session.commit()
            logger.info(
                "Interview status updated to %s for candidate %s",
                status,
                self.user_id,
            )
