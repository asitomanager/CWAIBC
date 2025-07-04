""" Generic class """

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from commons.src.log_helper import logger
from commons.src.config_loader import ConfigLoader
from commons.src.singleton_meta import SingletonMeta


class Database(metaclass=SingletonMeta):
    """Generic class to connect to the database using SQLAlchemy."""

    __CONFIG_PATH = os.path.join("commons", "db_details.json")

    def __init__(self, db_schema: str, db_name="MariaDB", env="PROD"):
        logger.info("Creating %s DB conn..", db_schema)
        self.__db_name = db_name
        self.__db_schema = db_schema
        self.__env = env.upper()
        self.engine = self.__create_engine()
        self.session = sessionmaker(bind=self.engine)

    def __create_engine(self):
        """Create an engine to connect to the database.
        :return: engine
        """
        conn_str = self.__get_conn_str()
        try:
            # print("conn_str: %s ", conn_str)
            logger.info('Connecting to "%s" database..', self.__db_schema)
            engine = create_engine(conn_str, echo=True)
            return engine
        except Exception as err:
            logger.info("conn_str: %s ", conn_str)
            logger.error(err)
            raise

    def __get_conn_str(self):
        db_details = ConfigLoader.get_config(self.__CONFIG_PATH)
        conn_details = db_details[f"{self.__db_name}_{self.__env}"]
        user, password, host, port = (
            conn_details["user"],
            conn_details["password"],
            conn_details["host"],
            conn_details["port"],
        )
        password = password.replace("@", "%40")

        # Format the DATABASE_URL using the dictionary values
        conn_str = (
            f"{self.__db_name.lower()}+{self.__db_name.lower()}connector://"
            f"{user}:{password}@{host}:{port}/{self.__db_schema}"
        )
        return conn_str


if __name__ == "__main__":
    print(Database(db_schema="User_Management", env="DEV"))
