"""Pydantic schemas for transaction endpoints."""

import re
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TransactionTypeEnum(str, Enum):
    """Transaction direction."""

    credit = "credit"
    debit = "debit"


class TransactionProviderEnum(str, Enum):
    """Payment provider."""

    phonepe = "phonepe"
    bank_transfer = "bank_transfer"
    upi = "upi"
    other = "other"


class TransactionStatusEnum(str, Enum):
    """Transaction processing status."""

    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


# ISO 4217 currency codes (common subset used in financial apps)
_ISO_4217_CODES = frozenset({
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS",
    "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS", "KHR",
    "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD",
    "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
    "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLE", "SOS", "SRD", "SSP", "STN", "SVC", "SYP", "SZL",
    "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH",
    "UGX", "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF", "XCD",
    "XOF", "XPF", "YER", "ZAR", "ZMW", "ZWL",
})


def _validate_currency_code(v: str) -> str:
    """Validate ISO 4217 currency code."""
    code = v.upper()
    if code not in _ISO_4217_CODES:
        raise ValueError(f"'{v}' is not a valid ISO 4217 currency code")
    return code


class TransactionFilter(BaseModel):
    """Schema for filtering transaction history.

    Validates: Requirements 8.1, 8.2
    """

    model_config = {"strict": False}

    date_from: datetime | None = None
    date_to: datetime | None = None
    type: TransactionTypeEnum | None = None
    provider: TransactionProviderEnum | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TransactionResponse(BaseModel):
    """Schema for a single transaction in responses.

    Validates: Requirements 8.3, 15.2
    """

    model_config = {"strict": False, "from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    external_transaction_id: str
    provider: TransactionProviderEnum
    type: TransactionTypeEnum
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    status: TransactionStatusEnum
    merchant_name: str | None = None
    description: str | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: Decimal) -> Decimal:
        """Transaction amounts must be positive."""
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Currency must be a valid ISO 4217 code."""
        return _validate_currency_code(v)


class TransactionSummaryResponse(BaseModel):
    """Schema for transaction summary/analytics.

    Validates: Requirements 8.4
    """

    model_config = {"strict": False}

    total_credit: Decimal = Field(default=Decimal("0.00"))
    total_debit: Decimal = Field(default=Decimal("0.00"))
    transaction_count: int = Field(default=0, ge=0)
    period_start: datetime | None = None
    period_end: datetime | None = None
