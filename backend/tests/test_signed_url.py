"""
test_signed_url.py — Signed download token generation and verification.

This module is pure stdlib (hmac, hashlib, base64) so these tests run
against the real implementation with zero mocking required.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from app.utils.signed_url import (
    generate_download_token,
    verify_download_token,
    token_expiry,
)


class TestBasicRoundTrip:

    def test_token_is_nonempty_string(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = generate_download_token("record-1", future)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_token_contains_dot_separator(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = generate_download_token("record-1", future)
        assert "." in token

    def test_verify_returns_correct_record_id(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = generate_download_token("record-abc-123", future)
        assert verify_download_token(token) == "record-abc-123"

    def test_uuid_style_record_id_roundtrips(self):
        uuid_like = "550e8400-e29b-41d4-a716-446655440000"
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = generate_download_token(uuid_like, future)
        assert verify_download_token(token) == uuid_like


class TestExpiryEnforcement:

    def test_expired_token_fails_verification(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = generate_download_token("record-x", past)
        assert verify_download_token(token) is None

    def test_not_yet_expired_token_verifies(self):
        soon = datetime.now(timezone.utc) + timedelta(seconds=30)
        token = generate_download_token("record-soon", soon)
        assert verify_download_token(token) == "record-soon"

    def test_token_at_exact_boundary(self):
        """A token expiring 1 second ago should be rejected."""
        just_past = datetime.now(timezone.utc) - timedelta(seconds=1)
        token = generate_download_token("record-boundary", just_past)
        assert verify_download_token(token) is None


class TestTamperDetection:

    def test_tampered_signature_rejected(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = generate_download_token("record-1", future)
        # Flip the last character of the signature
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        assert verify_download_token(tampered) is None

    def test_mismatched_payload_and_signature_rejected(self):
        """
        Splicing the payload from one valid token with the signature from
        another must fail — this is the core HMAC guarantee.
        """
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token_a = generate_download_token("record-a", future)
        token_b = generate_download_token("record-b", future)

        payload_a, _ = token_a.split(".")
        _, sig_b = token_b.split(".")
        frankenstein = f"{payload_a}.{sig_b}"

        assert verify_download_token(frankenstein) is None

    def test_extending_expiry_without_resigning_fails(self):
        """
        An attacker who tries to extend a token's life by editing the
        embedded expiry timestamp (without knowing the secret) must fail,
        since that changes the payload and invalidates the signature.
        """
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = generate_download_token("record-1", past)
        # This tampered token can't be constructed correctly without the
        # secret, so any hand-edited payload will fail signature check.
        payload, sig = token.split(".")
        edited_payload = payload + "X"  # corrupt the base64 payload
        assert verify_download_token(f"{edited_payload}.{sig}") is None


class TestMalformedTokenHandling:

    @pytest.mark.parametrize(
        "bad_token",
        ["", "just-garbage-no-dot", ".", "!!!not-base64!!!.somesig", "cmVjb3JkOjE.deadbeef"],
    )
    def test_malformed_tokens_return_none(self, bad_token):
        assert verify_download_token(bad_token) is None

    def test_none_input_handled(self):
        assert verify_download_token(None) is None


class TestSecretRotation:

    def test_different_secrets_produce_different_tokens(self, monkeypatch):
        from app.config import settings

        future = datetime.now(timezone.utc) + timedelta(hours=1)

        monkeypatch.setattr(settings, "JWT_SECRET", "secret-one")
        token1 = generate_download_token("same-record", future)

        monkeypatch.setattr(settings, "JWT_SECRET", "secret-two")
        token2 = generate_download_token("same-record", future)

        assert token1 != token2

    def test_token_invalid_after_secret_rotation(self, monkeypatch):
        from app.config import settings

        future = datetime.now(timezone.utc) + timedelta(hours=1)

        monkeypatch.setattr(settings, "JWT_SECRET", "original-secret")
        token = generate_download_token("record-1", future)
        assert verify_download_token(token) == "record-1"

        monkeypatch.setattr(settings, "JWT_SECRET", "rotated-secret")
        assert verify_download_token(token) is None


class TestTokenExpiryIntrospection:

    def test_extracted_expiry_matches_input(self):
        known = datetime.now(timezone.utc) + timedelta(hours=5)
        token = generate_download_token("rec", known)
        extracted = token_expiry(token)
        assert abs((extracted - known).total_seconds()) < 1

    def test_works_on_expired_tokens_too(self):
        """Introspection should work even for tokens that fail verification."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = generate_download_token("rec", past)
        assert token_expiry(token) is not None

    def test_returns_none_for_garbage(self):
        assert token_expiry("not.valid") is None


class TestNaiveDatetimeHandling:

    def test_naive_datetime_treated_as_utc(self):
        naive_future = datetime.now() + timedelta(hours=1)
        token = generate_download_token("record-naive", naive_future)
        assert verify_download_token(token) == "record-naive"
