"""Skills and Roles ORM model"""

from sqlalchemy import Column, Integer, String, UniqueConstraint
from commons import Base


class SkillsORM(Base):
    """
    Represents a skill in the Skills table.

    Attributes:
        id (int): The primary key of the row.
        name (str): The name of the skill.
    """

    __tablename__ = "Skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)


class DesignationsORM(Base):
    """
    Represents a role in the Designations table.

    Attributes:
        id (int): The primary key of the row.
        name (str): The name of the role.
    """

    __tablename__ = "Designations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)


class MetaDataORM(Base):
    """Represents a metadata in the MetaData table."""

    __tablename__ = "MetaData"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)

    # Combination of name and value should be unique
    __table_args__ = (UniqueConstraint("name", "value", name="unique_name_value"),)
