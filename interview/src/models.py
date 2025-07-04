"""
This module contains SQLAlchemy models for the interview system.
It defines the database schema and ORM classes for managing interviews.
"""

from datetime import datetime

import pytz
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from commons import Base, InterviewStatus
from user_management.models.candidate import CandidateORM


class InterviewORM(Base):
    """ORM class for managing interviews."""

    __tablename__ = "Interviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("Candidates.id"), nullable=False)
    status = Column(
        Enum(InterviewStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    email_datetime = Column(
        DateTime,
        nullable=True,
        default=datetime.now(pytz.utc).astimezone(pytz.timezone("Asia/Kolkata")),
    )
    interview_datetime = Column(DateTime, nullable=True)

    candidate = relationship("CandidateORM", back_populates="interviews")

    def to_dict(self):
        """Convert interview object to dictionary."""
        return {
            "status": self.status.value if self.status else None,
            "email_datetime": (
                self.email_datetime.isoformat() if self.email_datetime else None
            ),
            "interview_datetime": (
                self.interview_datetime.isoformat() if self.interview_datetime else None
            ),
        }
