"""
Provides functionality for managing metadata, such as skills and designations.

This module contains the [MetaData] class, which handles database operations for lists of values (LOVs).
It supports fetching and updating LOVs like skills and roles, ensuring data integrity and proper error handling.
"""

from typing import List

from sqlalchemy.exc import IntegrityError

from commons import DBEnterExitMixin, logger
from meta_data.models import MetaDataORM


class MetaData(DBEnterExitMixin):
    """
    Provides functionality for managing metadata, such as skills and designations.

    This class handles database operations for lists of values (LOVs).
    It supports fetching and updating LOVs like skills and roles, ensuring data integrity and proper error handling.
    """

    def __init__(self, db_helper=None):
        self._db_helper = db_helper

    async def fetch(self, name: str) -> List[str]:
        """
        Fetches all active skills or roles from the LOV table.

        Args:
            name (str): The name of the LOV table to query.

        Returns:
            List[str]: A list of skills or roles.
        """
        name = name.upper()
        with self:
            logger.info("Fetching all %ss from database..", name)
            results = (
                self._db_session.query(MetaDataORM)
                .filter_by(name=name)
                .order_by(MetaDataORM.value.asc())
                .all()
            )
        return [result.value for result in results]

    async def add(self, name: str, value: str) -> List[str]:
        """
        Adds new skills or roles to the LOV table.

        Args:
            name (str): The name of the LOV to update.
            value (str): A string containing the LOV value.

        Returns:
            List[str]: A list of strings containing the LOV key and LOV value.
        Raises:
            ValueError: If the LOV name is invalid.
            Exception: If an internal server error occurs.
        """
        name = name.upper()
        value = value.upper()
        with self:
            try:
                record = MetaDataORM(name=name, value=value)
                self._db_session.add(record)
                self._db_session.commit()
                logger.info("Added %s %s to database..", name, value)
                return self.fetch(name)
            except IntegrityError as exc:
                raise ValueError(f"{name} {value} already exists in DB") from exc

    async def delete(self, name: str, value: str) -> List[str]:
        """
        Deletes a value from a given LOV.

        Args:
            name (str): The name of the LOV to delete from.
            value (str): A string containing the LOV value.

        Returns:
            List[str]: A list of strings containing the LOV key and LOV value.
        Raises:
            ValueError: If the LOV name is invalid.
            Exception: If an internal server error occurs.
        """
        name = name.upper()
        value = value.upper()
        with self:
            record = (
                self._db_session.query(MetaDataORM)
                .filter_by(name=name, value=value)
                .first()
            )
            if record:
                self._db_session.delete(record)
                self._db_session.commit()
                logger.info("Deleted %s %s from database..", name, value)
            else:
                raise ValueError(f"{name} {value} not found in DB")
