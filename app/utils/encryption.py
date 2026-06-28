"""
Flora OS — Token Encryption
Fernet symmetric encryption for storing OAuth tokens in the database.
"""

import base64
import os

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Dev fallback — generate deterministic key from secret
        raw = settings.app_secret_key.encode()[:32].ljust(32, b"0")
        key = base64.urlsafe_b64encode(raw)
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return a base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string and return the original plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def generate_key() -> str:
    """Generate a new Fernet key. Run once to get ENCRYPTION_KEY value."""
    return Fernet.generate_key().decode()
