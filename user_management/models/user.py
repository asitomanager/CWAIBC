""" ORM class for managing users. """

from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, String, Enum, Boolean

from commons import Base


class UserORM(Base):
    """The User class inherits from Base and represents rows in the users table."""

    # Below tells SQLAlchemy name of the table to which this class should be mapped.
    __tablename__ = "Users"  # Case sensitive in *nix
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(Enum("Candidate", "Admin"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    passwordhash = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("1"))

    def __repr__(self):
        return f"UserORM(role={self.role!r}, name={self.name!r}, email={self.email!r}"

    def to_dict(self):
        """Convert the UserORM object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
        }
