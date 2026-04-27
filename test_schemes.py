"""Tests for Pydantic validation schemas."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    OTPVerifyRequest,
    RegistrationRequest,
)
from app.schemas.bank_details import BankDetailsRequest, BankDetailsResponse
from app.schemas.dashboard import DashboardSummaryResponse, VideoContentResponse
from app.schemas.fraud import FraudCheckRequest, FraudCheckResponse, FraudReportRequest
from app.schemas.notification import (
    NotificationFilter,
    NotificationPayload,
    NotificationResponse,
)
from app.schemas.transaction import (
    TransactionFilter,
    TransactionResponse,
    TransactionSummaryResponse,
)


# --- RegistrationRequest ---


class TestRegistrationRequest:
    def test_valid_registration(self):
        req = RegistrationRequest(
            email="user@example.com",
            phone="+919876543210",
            username="john_doe",
            password="Passw0rd!",
        )
        assert req.email == "user@example.com"
        assert req.username == "john_doe"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="not-an-email",
                phone="+919876543210",
                username="john_doe",
                password="Passw0rd!",
            )

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="ab",
                password="Passw0rd!",
            )

    def test_username_invalid_chars(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john doe!",
                password="Passw0rd!",
            )

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john_doe",
                password="passw0rd!",
            )

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john_doe",
                password="PASSW0RD!",
            )

    def test_password_no_digit(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john_doe",
                password="Password!",
            )

    def test_password_no_special(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john_doe",
                password="Passw0rd1",
            )

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="user@example.com",
                phone="+919876543210",
                username="john_doe",
                password="Pa1!",
            )


# --- LoginRequest ---


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(email="user@example.com", password="mypassword")
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="mypassword")


# --- OTPVerifyRequest ---


class TestOTPVerifyRequest:
    def test_valid_otp(self):
        uid = uuid.uuid4()
        req = OTPVerifyRequest(user_id=uid, otp="123456")
        assert req.otp == "123456"
        assert req.user_id == uid

    def test_otp_not_six_digits(self):
        with pytest.raises(ValidationError):
            OTPVerifyRequest(user_id=uuid.uuid4(), otp="12345")

    def test_otp_with_letters(self):
        with pytest.raises(ValidationError):
            OTPVerifyRequest(user_id=uuid.uuid4(), otp="12345a")

    def test_otp_too_long(self):
        with pytest.raises(ValidationError):
            OTPVerifyRequest(user_id=uuid.uuid4(), otp="1234567")


# --- BankDetailsRequest ---


class TestBankDetailsRequest:
    def test_valid_bank_details(self):
        req = BankDetailsRequest(
            bank_name="State Bank of India",
            account_number="1234567890",
            ifsc_code="SBIN0001234",
            account_type="savings",
        )
        assert req.ifsc_code == "SBIN0001234"

    def test_invalid_ifsc_code(self):
        with pytest.raises(ValidationError):
            BankDetailsRequest(
                bank_name="SBI",
                account_number="1234567890",
                ifsc_code="INVALID",
                account_type="savings",
            )

    def test_ifsc_code_lowercase_rejected(self):
        with pytest.raises(ValidationError):
            BankDetailsRequest(
                bank_name="SBI",
                account_number="1234567890",
                ifsc_code="sbin0001234",
                account_type="savings",
            )

    def test_invalid_account_type(self):
        with pytest.raises(ValidationError):
            BankDetailsRequest(
                bank_name="SBI",
                account_number="1234567890",
                ifsc_code="SBIN0001234",
                account_type="checking",
            )


# --- TransactionFilter ---


class TestTransactionFilter:
    def test_defaults(self):
        f = TransactionFilter()
        assert f.page == 1
        assert f.page_size == 20
        assert f.type is None

    def test_page_must_be_positive(self):
        with pytest.raises(ValidationError):
            TransactionFilter(page=0)

    def test_page_size_max(self):
        with pytest.raises(ValidationError):
            TransactionFilter(page_size=101)


# --- TransactionResponse ---


class TestTransactionResponse:
    def _valid_data(self, **overrides):
        now = datetime.now(timezone.utc)
        data = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "external_transaction_id": "txn_123",
            "provider": "phonepe",
            "type": "credit",
            "amount": Decimal("100.50"),
            "currency": "INR",
            "status": "completed",
            "created_at": now,
            "updated_at": now,
        }
        data.update(overrides)
        return data

    def test_valid_transaction(self):
        resp = TransactionResponse(**self._valid_data())
        assert resp.amount == Decimal("100.50")
        assert resp.currency == "INR"

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            TransactionResponse(**self._valid_data(amount=Decimal("-10.00")))

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            TransactionResponse(**self._valid_data(amount=Decimal("0")))

    def test_invalid_currency_rejected(self):
        with pytest.raises(ValidationError):
            TransactionResponse(**self._valid_data(currency="XYZ"))


# --- NotificationPayload ---


class TestNotificationPayload:
    def test_valid_notification(self):
        payload = NotificationPayload(
            type="transaction",
            title="Payment received",
            body="You received ₹500 from merchant.",
        )
        assert payload.title == "Payment received"

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            NotificationPayload(
                type="transaction",
                title="x" * 201,
                body="Body text",
            )

    def test_body_too_long(self):
        with pytest.raises(ValidationError):
            NotificationPayload(
                type="transaction",
                title="Title",
                body="x" * 5001,
            )

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            NotificationPayload(
                type="transaction",
                title="",
                body="Body text",
            )

    def test_empty_body_rejected(self):
        with pytest.raises(ValidationError):
            NotificationPayload(
                type="transaction",
                title="Title",
                body="",
            )


# --- FraudCheckRequest ---


class TestFraudCheckRequest:
    def test_valid_url(self):
        req = FraudCheckRequest(url="https://example.com/path")
        assert req.url == "https://example.com/path"

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            FraudCheckRequest(url="not-a-url")

    def test_http_url_accepted(self):
        req = FraudCheckRequest(url="http://example.com")
        assert "example.com" in req.url


# --- FraudCheckResponse ---


class TestFraudCheckResponse:
    def test_valid_response(self):
        resp = FraudCheckResponse(
            url="https://example.com",
            risk_score=Decimal("0.75"),
            category="suspicious",
            reasons=["Domain is new"],
            recommendation="Exercise caution.",
        )
        assert resp.risk_score == Decimal("0.75")

    def test_risk_score_out_of_range(self):
        with pytest.raises(ValidationError):
            FraudCheckResponse(
                url="https://example.com",
                risk_score=Decimal("1.50"),
                category="safe",
                reasons=[],
                recommendation="Safe",
            )


# --- FraudReportRequest ---


class TestFraudReportRequest:
    def test_valid_report(self):
        req = FraudReportRequest(
            url="https://phishing-site.com",
            reason="Looks like a phishing page",
        )
        assert req.reason == "Looks like a phishing page"

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            FraudReportRequest(url="bad-url", reason="Suspicious")


# --- DashboardSummaryResponse ---


class TestDashboardSummaryResponse:
    def test_defaults(self):
        resp = DashboardSummaryResponse()
        assert resp.recent_transactions_count == 0
        assert resp.unread_notifications_count == 0
        assert resp.total_credit == Decimal("0.00")


# --- VideoContentResponse ---


class TestVideoContentResponse:
    def test_valid_video(self):
        resp = VideoContentResponse(
            video_id="abc123",
            title="Financial Awareness",
            url="https://youtube.com/watch?v=abc123",
        )
        assert resp.video_id == "abc123"


# --- AuthResponse ---


class TestAuthResponse:
    def test_success_response(self):
        resp = AuthResponse(
            success=True,
            message="OTP sent",
            user_id=uuid.uuid4(),
        )
        assert resp.success is True

    def test_error_response(self):
        resp = AuthResponse(
            success=False,
            error="Email already registered",
        )
        assert resp.success is False
        assert resp.error == "Email already registered"
