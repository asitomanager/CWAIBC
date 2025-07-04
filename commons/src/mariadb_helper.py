"""MariaDB helper class."""
import os
import mariadb
from commons.src.log_helper import logger
from commons.src.database import IDatabase
from commons.src.config_loader import ConfigLoader


class MariaDBHelper(IDatabase):
    """SingletonMeta controls the creation of MariaDB,
    ensuring that only one instance of MariaDB is created"""

    __CONFIG_PATH = os.path.join("commons", "db_details.json")

    def __init__(self, db_schema: str, env="PROD"):
        logger.info("Creating %s DB MariaDB conn..", db_schema)
        self.__db_schema = db_schema
        self.__env = env.upper()

        conn_str = self.__get_conn_str()
        try:
            self.connection = mariadb.connect(**conn_str)
            self.connection.autocommit = False
            # Creating a cursor that returns rows as named tuples
            self.cursor = self.connection.cursor(named_tuple=True)
        except mariadb.Error as err:
            logger.info("conn_str: %s ", conn_str)
            logger.error(err)
            raise err

    def disconnect(self):
        """Close the connection to the database."""

        logger.info("Closing %s DB MariaDB conn..", self.__db_schema)
        self.connection.close()
        logger.debug("Closed %s DB MariaDB conn", self.__db_schema)

    def fetch_data(self, query, params):
        """
        Execute a SQL query with the given parameters and return the fetched results.

        :param query: SQL query string to be executed.
        :param params: Parameters to be used with the query.
        :return: List of tuples containing the results fetched from the database.
        :raises: mariadb.Error if a database error occurs.
        """
        try:
            logger.debug("\nExecuting Query: %s with parameters: %s\n", query, params)
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except mariadb.Error as err:
            logger.exception("Database error occurred", exc_info=err)
            raise

    def execute_query(self, query, params, commit=True):
        rows_updated = 0
        try:
            logger.debug("\nExecuting Query: %s with parameters: %s\n", query, params)
            self.cursor.execute(query, params)
            rows_updated = self.cursor.rowcount
            logger.info("%d rows were updated.", rows_updated)
            if commit and rows_updated > 0:
                self.commit_transactions()
        except (mariadb.OperationalError, mariadb.Error) as err:
            logger.exception("Query: %s; params: %s", query, params)
            logger.exception(str(err))
        return rows_updated

    def commit_transactions(self):
        logger.debug("Committing.. !")
        self.connection.commit()

    def __get_conn_str(self):
        db_details = ConfigLoader.get_config(self.__CONFIG_PATH)
        conn_str = db_details["MariaDB_" + self.__env]
        conn_str["database"] = self.__db_schema
        return conn_str

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()
