""" This script creates the tables in the database. """

from commons.src.db_generic import Database
from commons.src.log_helper import logger

from commons.src.models import Base


generic_db = Database(db_schema="cwintwagent", env="DEV")

try:
    Base.metadata.create_all(bind=generic_db.engine)
    logger.info("Tables created successfully.")
except Exception as err:
    logger.exception("An error occurred while creating tables: %s", err)
    raise
