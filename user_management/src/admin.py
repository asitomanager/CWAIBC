"""Admin class for the user service."""

import os
import secrets
import string
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Union

import pandas as pd
import pytz
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from jinja2 import Template
from sqlalchemy import and_, case, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from commons import (
    EmailHelper,
    InterviewStatus,
    RecordNotFoundException,
    UserExistsException,
    logger,
)
from interview.src.models import InterviewORM
from user_management.models.candidate import CandidateORM
from user_management.models.user import UserORM
from user_management.src.schemas import CandidateInfo, CandidateResponseInfo
from user_management.src.user import User

load_dotenv(override=True)
FILES_DIR = os.environ.get("FILES_DIR")


class Admin(User):
    """Represents an admin user in the user service."""

    def __init__(self, user_id):
        super().__init__(user_id)
        self.__authorized = False
        if user_id:
            self._set_user_record_by_id()

    def __enter__(self):
        super().__enter__()
        if self.is_authorized():
            return self
        raise PermissionError("User is not authorized to perform this action")

    def is_authorized(self) -> bool:
        """
        Check if the current user is authorized.

        This method checks if the user is authorized by verifying their role and
        whether they are active or not.

        Returns:
            bool: True if the user is authorized, False otherwise.
        """
        logger.info("Checking if user is authorized...")
        if not self.__authorized:
            if self._db_session is None:
                super().__enter__()
            user = (
                self._db_session.query(UserORM).filter(UserORM.id == self._id).first()
            )
            if user and user.role == "Admin" and user.is_active:
                self.__authorized = True
            else:
                self.__authorized = False
        return self.__authorized

    def __fetch_all_candidates_with_latest_status(self, interview_status: str = "ALL"):
        logger.info("Fetching all candidates..")
        with self:
            # Subquery for latest interviews
            latest_interviews = self._db_session.query(
                InterviewORM.candidate_id,
                InterviewORM.status,
                InterviewORM.interview_datetime,
                func.row_number()
                .over(
                    partition_by=InterviewORM.candidate_id,
                    order_by=[
                        InterviewORM.interview_datetime.is_(None).desc(),  # NULLs first
                        InterviewORM.interview_datetime.desc(),  # Among non-NULLs, latest first
                    ],
                )
                .label("rn"),
            ).subquery("latest_interviews")

            # Build base query with join
            query = self._db_session.query(
                CandidateORM,
                latest_interviews.c.status.label("latest_interview_status"),
            ).join(
                latest_interviews,
                and_(
                    CandidateORM.id == latest_interviews.c.candidate_id,
                    latest_interviews.c.rn == 1,  # Only get the top row per candidate
                ),
            )
            if interview_status != "ALL":
                query = query.filter(latest_interviews.c.status == interview_status)
            return query

    def get_all_candidates(
        self, page_number, interview_status: str, results_per_page=10
    ) -> Dict[str, Union[List[CandidateResponseInfo], int]]:
        """
        Retrieve a paginated list of candidate profiles.

        Parameters:
        - page_number (int): The current page number to retrieve.
        - interview_status (str): Status of the interview to filter candidates.
        - results_per_page (int, optional): Number of profiles per page, defaulting to 10.

        Returns:
        - Dict[str, Union[List[CandidateResponseInfo], int]]:
            A dictionary containing the list of candidate profiles for the specified page and the total count of
            candidates.
        """
        if interview_status != "ALL" and interview_status not in [
            status.value for status in InterviewStatus
        ]:
            raise ValueError("Invalid interview status")

        query = self.__fetch_all_candidates_with_latest_status(interview_status)

        # Get count and paginated results
        count = query.count()
        paginated_candidates = (
            query.limit(results_per_page)
            .offset((page_number - 1) * results_per_page)
            .all()
        )

        response_data = [
            CandidateResponseInfo(
                id=candidate.id,
                name=candidate.name,
                email=candidate.email,
                grade=candidate.grade,
                location=candidate.location,
                skill=candidate.skill,
                designation=candidate.designation,
                department=candidate.department,
                interview_status=(interview_status.value if interview_status else None),
                resume=candidate.resume,
            )
            for candidate, interview_status in paginated_candidates
        ]
        return {"data": response_data, "count": count}

    def export_candidates_to_excel(self) -> StreamingResponse:
        """
        Fetch all candidates and export as an Excel file.
        """
        with self:
            candidates = (
                self._db_session.query(CandidateORM)
                .options(joinedload(CandidateORM.interviews))
                .all()
            )

        if not candidates:
            raise RecordNotFoundException("No candidates found")

        # Convert ORM objects to dicts
        candidate_dicts = [c.to_dict() for c in candidates]
        for candidate in candidate_dicts:
            candidate.pop("_sa_instance_state", None)  # Remove SQLAlchemy metadata

        # Convert to DataFrame and write to Excel
        df = pd.DataFrame(candidate_dicts)
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name="Candidates")
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=candidates.xlsx"},
        )

    def get_dashboard(self):
        """
        Retrieve the admin dashboard statistics.

        This method retrieves the current statistics for the admin dashboard and returns
        them as a dictionary with the following keys: total_applications, scheduled_interviews,
        inprogress_interviews, and completed_interviews.

        Returns:
            dict: A dictionary containing the admin dashboard statistics.
        """
        logger.info("Getting admin dashboard..")
        with self:
            result = self._db_session.query(
                # pylint: disable=E1102
                func.count(InterviewORM.candidate_id).label("total_applications"),
                func.sum(
                    case(
                        (
                            InterviewORM.status == InterviewStatus.SCHEDULED.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label("scheduled_interviews"),
                func.sum(
                    case(
                        (
                            InterviewORM.status == InterviewStatus.IN_PROGRESS.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label("inprogress_interviews"),
                func.sum(
                    case(
                        (
                            InterviewORM.status == InterviewStatus.COMPLETED.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label("completed_interviews"),
            ).one()
            return {
                "total_applicants": result.total_applications,
                "scheduled_interviews": result.scheduled_interviews,
                "inprogress_interviews": result.inprogress_interviews,
                "completed_interviews": result.completed_interviews,
            }

    def process_bulk_profiles(self) -> StreamingResponse:
        """
        Process a bulk upload of candidate profiles from an Excel spreadsheet.

        Reads the Excel spreadsheet, creates a new candidate profile for each row
        in the spreadsheet, and updates the status of each row in the DataFrame
        based on the processing result. Generates a response with the updated
        DataFrame saved to an Excel file.

        Returns:
            StreamingResponse: A response containing the processed Excel file.
        """
        spreadsheet_path = os.path.join(FILES_DIR, "bulk_profiles.xlsx")
        logger.info("Processing bulk profiles...")
        try:
            df = pd.read_excel(spreadsheet_path)
        except FileNotFoundError:
            logger.error("Bulk profiles spreadsheet not found.")
            raise

        df.columns = df.columns.str.upper()
        logger.info("Total Records: %s", len(df))
        df["STATUS"] = ""
        errored_records = 0
        existing_candidates_skipped_count = 0
        new_candidates_added_count = 0
        for idx, row in df.iterrows():
            try:
                candidate_info = CandidateInfo(
                    name=row["NAME"],
                    grade=row["GRADE"],
                    location=row["LOCATION"],
                    skill=row["SKILL"],
                    designation=row["DESIGNATION"],
                    department=row["DEPARTMENT"],
                    email=row["EMAIL"],
                )
            except KeyError as e:
                logger.error("Missing column in spreadsheet: %s", e)
                logger.error("Row: %s", row)
                errored_records += 1
                df.at[idx, "STATUS"] = f"Missing column: {e}"
                continue
            try:
                self.__create_candidate(candidate_info)
                new_candidates_added_count += 1
                df.at[idx, "STATUS"] = "Success"
            except UserExistsException as e:
                logger.error("%s. No action will be taken", e)
                existing_candidates_skipped_count += 1
                df.at[idx, "STATUS"] = "User Exists. Skipped"

        logger.info("Processed %s records", new_candidates_added_count)
        logger.info("Skipped %s records", existing_candidates_skipped_count)
        logger.info("Errored %s records", errored_records)

        # Save the DataFrame to a BytesIO buffer
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=bulk_profiles_processed.xlsx"
            },
        )

    def invite_candidate(self, candidate_id: int) -> bool:
        """
        Send a candidate invite to the specified candidate ID.

        This method sends an email invitation to the specified candidate ID. The
        email contains a temporary password that the candidate can use to log in
        to the system. The candidate's password is also updated in the database.

        Args:
            candidate_id (int): The ID of the candidate to whom the email invite
              should be sent.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        logger.info("Sending invite to candidate ID: %s", candidate_id)
        with self:
            # Retrieve the candidate record from the database
            candidate: CandidateORM = (
                self._db_session.query(CandidateORM)
                .filter(CandidateORM.id == candidate_id)
                .first()
            )
            if not candidate:
                raise RecordNotFoundException(
                    candidate_id, message=f"Candidate {candidate_id} not found"
                )

            # Generate a temporary password and update in the database
            current_password: str = self.generate_password()
            candidate.passwordhash = generate_password_hash(current_password)
            candidate.is_active = True

            scheduled_datetime = datetime.now(pytz.utc).astimezone(
                pytz.timezone("Asia/Kolkata")
            )
            # Check existing interviews for this candidate
            existing_interviews = (
                self._db_session.query(InterviewORM)
                .filter(InterviewORM.candidate_id == candidate_id)
                .all()
            )

            # Check for existing interviews with specific statuses
            active_interview = next(
                (
                    i
                    for i in existing_interviews
                    if i.status
                    in [
                        InterviewStatus.SCHEDULED,
                        InterviewStatus.NOT_SCHEDULED,
                        InterviewStatus.IN_PROGRESS,
                    ]
                ),
                None,
            )
            if active_interview:
                # Update existing active interview
                active_interview.status = InterviewStatus.SCHEDULED
                active_interview.email_datetime = scheduled_datetime
                active_interview.interview_datetime = None
            else:
                # All existing interviews are COMPLETED, create a new one
                interview: InterviewORM = InterviewORM(
                    candidate_id=candidate_id,
                    status=InterviewStatus.SCHEDULED,
                    email_datetime=scheduled_datetime,
                )
                self._db_session.add(interview)
            self._db_session.commit()

            with open(
                os.path.join("user_management", "src", "candidate_invite.html"),
                "r",
                encoding="utf-8",
            ) as f:
                email_template: Template = Template(f.read())
            email_body: str = email_template.render(
                applicant=candidate.name,
                username=candidate.email,
                password=current_password,
            )
            EmailHelper(candidate.email).send_candidate_invite(email_body)
            return True

    def __create_candidate(self, candidate_info: CandidateInfo) -> None:
        logger.info("Candidate creation request received")
        self.user_profile = candidate_info
        try:
            with self:
                if self._user_exists():
                    raise UserExistsException(candidate_info.email)

                new_user = CandidateORM(
                    role="Candidate",
                    name=candidate_info.name,
                    email=candidate_info.email,
                    grade=candidate_info.grade,
                    location=candidate_info.location,
                    skill=candidate_info.skill,
                    designation=candidate_info.designation,
                    department=candidate_info.department,
                )

                self._db_session.add(new_user)
                self._db_session.flush()  # Commit first to get the ID
                new_interview = InterviewORM(
                    candidate_id=new_user.id,
                    status=InterviewStatus.NOT_SCHEDULED,
                )
                self._db_session.add(new_interview)
                self._db_session.commit()
                logger.info("Candidate %s created successfully", candidate_info.email)
        except SQLAlchemyError as e:
            # No need for explicit rollback, handled by context manager
            logger.error("Database error occurred: %s", e)
            raise e

    def generate_password(self, length: int = None) -> str:
        """
        Generate a temporary password of random characters.

        Args:
            length (int): The length of the password to generate.

        Returns:
            str: The generated password as a string.
        """
        if length is None:
            length = self._config["password_length"]
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def get_candidate(self, candidate_id: int) -> CandidateResponseInfo:
        """
        Retrieve a candidate's profile.

        This method retrieves the profile of a candidate identified by the given
        candidate ID. The method returns the candidate's profile as a
        CandidateResponseInfo object.

        Args:
            candidate_id (int): The ID of the candidate whose profile is to be retrieved.

        Returns:
            CandidateResponseInfo: The profile of the candidate identified by the given candidate ID.

        Raises:
            RecordNotFoundException: If a candidate with the given ID does not exist.
        """
        with self:
            candidate = (
                self._db_session.query(CandidateORM)
                .filter(CandidateORM.id == candidate_id)
                .first()
            )
            if not candidate:
                raise RecordNotFoundException(
                    candidate_id, message="Candidate not found"
                )
            return CandidateResponseInfo(
                id=candidate.id,
                name=candidate.name,
                email=candidate.email,
                grade=candidate.grade,
                location=candidate.location,
                skill=candidate.skill,
                designation=candidate.designation,
                department=candidate.department,
                resume=candidate.resume,
            )

    def search_candidates(self, search_text: str) -> List[CandidateResponseInfo]:
        """
        Search for candidates by name or email.

        This method searches for candidates based on the provided search text.
        The search is case-insensitive and returns a list of candidate profiles
        matching the search text.

        Parameters:
        - search_text (str): The text to search for in candidate profiles.

        Returns:
        - List[CandidateResponseInfo]: A list of candidate profiles matching the search text.
        """
        search_text = search_text.strip().lower()
        logger.info("Searching for candidates with text: %s", search_text)
        query = self.__fetch_all_candidates_with_latest_status()
        with self:
            candidates = query.filter(
                or_(
                    func.lower(CandidateORM.id).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.name).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.email).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.skill).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.designation).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.department).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.location).ilike(f"%{search_text}%"),
                    func.lower(CandidateORM.grade).ilike(f"%{search_text}%"),
                )
            ).all()
            logger.info("Search results: %d", len(candidates))
            response_data = [
                CandidateResponseInfo(
                    id=candidate.id,
                    name=candidate.name,
                    email=candidate.email,
                    grade=candidate.grade,
                    location=candidate.location,
                    skill=candidate.skill,
                    designation=candidate.designation,
                    department=candidate.department,
                    interview_status=(
                        interview_status.value if interview_status else None
                    ),
                    resume=candidate.resume,
                )
                for candidate, interview_status in candidates
            ]
            return response_data
