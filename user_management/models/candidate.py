"""
This module defines the CandidateORM class, which represents a candidate 
in the user management system.

It extends the UserORM class and includes additional attributes specific 
to candidates such as job ID, grade, location, technology, and department.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship

from user_management.models.user import UserORM


class CandidateORM(UserORM):
    """
    Represents a candidate in the user management system.

    This class extends the UserORM class and includes additional attributes
    specific to candidates such as grade, location, skill, designation, department,
    resume, email timestamp, and interview status.

    Attributes:
        id (int): Primary key of the CandidateORM object.
        grade (str): Grade of the candidate.
        location (str): Location of the candidate.
        skill (str): Skill of the candidate.
        designation (str): Designation of the candidate.
        department (str): Department of the candidate.
        resume (bool): Whether the candidate has a resume or not.
        interviews (list): List of interviews associated with the candidate.
    """

    __tablename__ = "Candidates"
    id = Column(Integer, ForeignKey("Users.id"), primary_key=True)
    grade = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    skill = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    resume = Column(Boolean, nullable=False, server_default=text("0"))
    interviews = relationship("InterviewORM", back_populates="candidate")

    def to_dict(self):
        return {
            **super().to_dict(),
            "skill": self.skill,
            "designation": self.designation,
            "resume": self.resume,
            "interviews": [i.to_dict() for i in self.interviews],
        }

    def __repr__(self):
        return (
            f"CandidateORM(id={self.id!r}, grade={self.grade!r}, "
            f"location={self.location!r}, skill={self.skill!r}, "
            f"designation={self.designation!r}, department={self.department!r}, "
            f"resume={self.resume!r}, "
            f"interviews={self.interviews!r})"
        )
