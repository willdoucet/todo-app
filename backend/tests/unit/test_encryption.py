"""Unit tests for Fernet encryption utilities."""

import os
import pytest
from unittest.mock import patch
from cryptography.fernet import Fernet


class TestEncryptDecryptRoundTrip:
    """Test encrypt_password and decrypt_password together."""

    @pytest.fixture(autouse=True)
    def set_fernet_key(self):
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"FERNET_KEY": key}):
            yield

    def test_round_trip(self):
        from app.utils.encryption import encrypt_password, decrypt_password

        plain = "my-app-specific-password-1234"
        encrypted = encrypt_password(plain)
        assert encrypted != plain
        assert decrypt_password(encrypted) == plain

    def test_different_ciphertexts_per_call(self):
        from app.utils.encryption import encrypt_password

        a = encrypt_password("same-input")
        b = encrypt_password("same-input")
        assert a != b  # Fernet uses random IV each time


class TestDecryptWithWrongKey:
    """Decrypt with a different key should raise."""

    def test_wrong_key_raises(self):
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"FERNET_KEY": key1}):
            from app.utils.encryption import encrypt_password
            encrypted = encrypt_password("secret")

        with patch.dict(os.environ, {"FERNET_KEY": key2}):
            from app.utils.encryption import decrypt_password
            with pytest.raises(RuntimeError, match="Failed to decrypt"):
                decrypt_password(encrypted)


class TestMissingFernetKey:
    """Missing FERNET_KEY env var should raise."""

    def test_encrypt_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FERNET_KEY", None)
            from app.utils.encryption import encrypt_password
            with pytest.raises(RuntimeError, match="FERNET_KEY"):
                encrypt_password("test")

    def test_decrypt_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FERNET_KEY", None)
            from app.utils.encryption import decrypt_password
            with pytest.raises(RuntimeError, match="FERNET_KEY"):
                decrypt_password("some-ciphertext")
