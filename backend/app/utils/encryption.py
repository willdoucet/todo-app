import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY environment variable is not set")
    return Fernet(key.encode())


def encrypt_password(plain_text: str) -> str:
    """Encrypt a password string. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a password string. Raises RuntimeError on failure."""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt password — FERNET_KEY may have changed")
        raise RuntimeError("Failed to decrypt stored credentials")
