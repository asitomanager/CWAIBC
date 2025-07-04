"""Schemas for the user service"""

from pydantic import BaseModel, EmailStr, Field, SecretStr, StrictStr, field_validator


# pylint: disable=no-self-argument
class PasswordValidations(BaseModel):
    """Validations for password"""

    @field_validator("password", "old_password", "new_password", check_fields=False)
    def validate_password(cls, value):
        """Checking that the password is between 8-20 chars"""
        min_length, max_length = 8, 20

        if len(value) < min_length or len(value) > max_length:
            raise ValueError(
                f"Password must be between {min_length} and {max_length} characters long"
            )

        # Uncomment the following lines if you want to enforce digit and letter requirements
        # if not any(char.isdigit() for char in value):
        #     raise ValueError("Password must contain at least one digit")
        # if not any(char.isalpha() for char in value):
        #     raise ValueError("Password must contain at least one letter")

        return value

    class Config:
        """Pydantic model configuration."""

        # underscore_attrs_are_private = True
        json_schema_extra = {
            # Sample expected input
            "example": {
                "name": "Owner Name",
                "email": "contact@adminone.com",
                "mobile": "9876543210",
                "password": "****",
            }
        }


class LoginInfo(BaseModel):
    """Login info Pydantic model"""

    # TO DO: Extend to have mobile
    email: EmailStr
    password: SecretStr


class CandidateInfo(BaseModel):
    """Candidate profile Pydantic model"""

    name: StrictStr
    email: EmailStr
    grade: StrictStr
    location: StrictStr
    skill: StrictStr
    designation: StrictStr
    department: StrictStr

    # Convert skill and designation to uppercase and remove spaces
    @field_validator("skill", "designation")
    def __sanitize_input(cls, value: str) -> str:
        return value.strip().upper()


class CandidateResponseInfo(CandidateInfo):
    """Candidate profile response model"""

    id: int
    resume: int | None
    interview_status: StrictStr


class ChangePasswordRequest(BaseModel):
    """Password change request Pydantic model"""

    current_password: SecretStr = Field(..., description="Current password of the user")
    new_password: SecretStr = Field(..., description="New password for the user")
