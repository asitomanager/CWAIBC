"""
This module defines enumerations used throughout the application.

It includes:
- UploadFileTpe: An enumeration of file types that can be uploaded.
- InterviewStatus: An enumeration of possible interview statuses.
"""

from enum import Enum


class FileName(Enum):
    """
    An enumeration of file types that can be uploaded.

    The string values of each enumeration are used to determine the directory
    where the file will be uploaded.

    Attributes:
        BULK_PROFILE: Files containing multiple candidate profiles.
        JD: Job description files.
        QUESTION_BANK: Files containing questions that can be used for interviews.
        RESUME: Candidate resume files.
        VIDEO: Video files containing interview responses.
        TRANSCRIPT: Transcripts of interview responses.
        QA: Question and answer pairs.
    """

    BULK_PROFILE = "bulk_profiles"
    JD = "jd"
    QUESTION_BANK = "Question_Bank"
    RESUME = "resume"
    VIDEO = "video"
    TRANSCRIPT = "transcript"
    ANALYSIS_REPORT = "analysis"
    BULK_RESUME = "bulk_resumes"


class InterviewStatus(Enum):
    """
    An enumeration of possible interview statuses.
    Attributes:
        SCHEDULED: The interview is scheduled.
        IN_PROGRESS: The interview is in progress.
        COMPLETED: The interview is completed.
    """

    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    NOT_SCHEDULED = "Not Scheduled"
    INVITE_EXPIRED = "Invite Expired"
    REJECTED = "Rejected"
    SELECTED = "Selected"
    HIRED = "Hired"
