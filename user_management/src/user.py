"""Abstract class for all users."""

import os
import re

from sqlalchemy import exists
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from commons import (
    AuthenticationException,
    AuthorizationException,
    ConfigLoader,
    DBEnterExitMixin,
    RecordNotFoundException,
    logger,
)
from user_management.models import UserORM
from user_management.src.schemas import ChangePasswordRequest


class User(DBEnterExitMixin):
    """Abstract class for all users."""

    __CONFIG_PATH = os.path.join("commons", "config.jsonc")

    def __init__(self, user_id: int = None, db_helper=None):

        self._id = user_id
        self.user_profile: UserORM = None
        self._db_helper = db_helper
        self._db_session = None
        self._config = ConfigLoader.get_config(self.__CONFIG_PATH)

    def login(self, email: str, password: str) -> None:
        """Authenticate a user by their email and password.

        This method checks whether a user with the given email exists in the database
        and whether the provided password matches the stored password hash. If authentication
        is successful, it logs the event and returns user details; otherwise, it raises an AuthenticationException.

        Args:
            email (str): The email of the user attempting to log in.
            password (str): The plaintext password provided by the user.

        Returns:
            Tuple[int, str, str]: A tuple containing user ID, name, and role.

        Raises:
            AuthenticationException: If authentication fails due to incorrect email
            or password.
            AuthorizationException: If the user is not active or the email verification period has expired.
        """
        try:
            user = self.__get_user_record_by_email(email)
        except RecordNotFoundException as exc:
            raise AuthenticationException(email) from exc
        with self:
            if not user.is_active:
                logger.warning("User %s attempted to log in but is inactive.", email)
                raise AuthorizationException(email, message="User is not active !")
            if check_password_hash(user.passwordhash, password):
                logger.info("User %s authentication successful", email)
                return (user.id, user.name, user.role)
            logger.warning(
                "User %s authentication failed due to incorrect username or password.",
                email,
            )
            raise AuthenticationException(email)

    def _user_exists(self) -> bool:
        user_exists = self._db_session.query(
            exists().where(UserORM.email == self.user_profile.email)
        ).scalar()
        return user_exists

    def __get_user_record_by_email(self, email):
        with self:
            user = (
                self._db_session.query(UserORM).filter(UserORM.email == email).first()
            )
            if user:
                return user
            raise RecordNotFoundException(email)

    def _set_user_record_by_id(self):
        if not self._id:
            raise ValueError("User ID is required")
        with self:
            self.user_profile = (
                self._db_session.query(UserORM).filter(UserORM.id == self._id).first()
            )
        if not self.user_profile:
            raise RecordNotFoundException(self._id)

    def deactivate(self) -> None:
        """Deactivate a user."""
        try:
            with self:
                self._db_session.query(UserORM).filter(
                    UserORM.email == self.user_profile.email
                ).update({"is_active": False})
                self._db_session.commit()
                logger.info("User %s deactivated", self.user_profile.email)
        except SQLAlchemyError as e:
            logger.error("Database error occurred: %s", e)
            raise e

    def set_password(self, request: ChangePasswordRequest) -> None:
        """Set the user's password."""
        if not self._id:
            raise ValueError("User ID is required")
        self._set_user_record_by_id()
        # Check if the old password is correct
        if not check_password_hash(
            self.user_profile.passwordhash, request.current_password.get_secret_value()
        ):
            logger.warning(
                "User %s provided incorrect current password", self.user_profile.email
            )
            raise AuthenticationException(
                self.user_profile.email, "Current password is incorrect"
            )
        new_password = request.new_password.get_secret_value()
        # Check strength and minimum requirements
        if len(new_password) < self._config["password_length"]:
            raise ValueError(
                f"Password must be at least {self._config['password_length']} characters long"
            )
        if not re.match(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[~@$!%*?&#^()])[A-Za-z\d~@$!%*?&#^()]{8,20}$",
            new_password,
        ):
            raise ValueError(
                "Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character"
                "(Allowed special characters: ~!@#$%^&*()_+\-=[\]{}|\\;':,./?)"
                "Must be between 8 and 20 characters long"
            )
        with self:
            # Update the password hash
            self._db_session.query(UserORM).filter(UserORM.id == self._id).update(
                {"passwordhash": generate_password_hash(new_password)}
            )
            self._db_session.commit()
            logger.info("User %s password updated", self.user_profile.email)
