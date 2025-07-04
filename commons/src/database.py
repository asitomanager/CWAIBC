"""Abstract base class for database interaction."""
from abc import abstractmethod
from commons.src.singleton_meta import SingletonMeta


class IDatabase(metaclass=SingletonMeta):
    """Represents an abstract base class for a database.
    Base class IDatabase already specifies SingletonMeta as its metaclass.
    So, Python will automatically inherit the metaclass from the base class.
    """

    @abstractmethod
    def disconnect(self):
        """Close the connection to the database."""

    @abstractmethod
    def fetch_data(self, query, params):
        """
        Fetch data from the database.

        :param query: The query string to execute.
        :return: The result set of the query.
        """

    @abstractmethod
    def execute_query(self, query, params, commit=True):
        """
        Execute a query on the database.

        :param query: The query string to execute.
        :param params: The parameters to pass to the query.
        :return: The number of rows affected by the query.
        """
    @abstractmethod
    def commit_transactions(self):
        """
        Commits all current transactions.
        """
