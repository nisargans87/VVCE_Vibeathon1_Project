"""Pydantic schemas for bank details endpoints."""

import re
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AccountTypeEnum(str, Enum):
    """Account type choices for bank details."""

    savings = "savings"
    current = "current"
    salary = "salary"


class BankDetailsRequest(BaseModel):
    """Schema for creating/updating bank details.

    Validates: Requirements 6.1, 6.2
    """

    model_config = {"strict": False}

    bank_name: str = Field(..., min_length=1, max_length=255)
    account_number: str = Field(..., min_length=1, max_length=50)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    account_type: AccountTypeEnum
    is_primary: bool = False

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc_code(cls, v: str) -> str:
        """IFSC code must match pattern: 4 letters + 0 + 6 alphanumeric."""
        if not re.fullmatch(r"^[A-Z]{4}0[A-Z0-9]{6}$", v):
            raise ValueError(
                "IFSC code must be 4 uppercase letters, followed by 0, "
                "followed by 6 alphanumeric characters (e.g., SBIN0001234)"
            )
        return v


class BankDetailsResponse(BaseModel):
    """Schema for bank details response."""

    model_config = {"strict": False, "from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    bank_name: str
    ifsc_code: str
    account_type: AccountTypeEnum
    is_primary: bool
    created_at: datetime
    updated_at: datetime

