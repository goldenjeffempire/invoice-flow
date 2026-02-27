"""
Field-level encryption utilities for sensitive invoice data.
Implements AES-256 encryption for sensitive fields like bank account numbers.
"""

import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from django.conf import settings


class FieldEncryption:
    """
    Handles field-level encryption and decryption for sensitive data.
    Uses Fernet (symmetric encryption) with AES-256.
    """

    @staticmethod
    def _get_encryption_key():
        """
        Derive encryption key from Django SECRET_KEY using PBKDF2.
        This ensures the encryption key is derived securely.
        """
        # Get encryption salt from settings (enforced in production)
        salt_str = settings.ENCRYPTION_SALT
        salt = salt_str.encode() if isinstance(salt_str, str) else salt_str

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        return key

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            key = cls._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            # Log error in production
            raise ValueError(f"Encryption failed: {str(e)}")

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return ""

        try:
            key = cls._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_text.encode())
            return decrypted.decode()
        except Exception as e:
            # Log error in production
            raise ValueError(f"Decryption failed: {str(e)}")

    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """
        Create a one-way hash of sensitive data for searching/indexing.
        Useful for bank account numbers where you need to check duplicates
        but don't need to decrypt.

        Args:
            data: The sensitive data to hash

        Returns:
            SHA-256 hash of the data
        """
        if not data:
            return ""

        return hashlib.sha256(data.encode()).hexdigest()


def encrypt_bank_details(account_number: str) -> str:
    """
    Convenience function to encrypt bank account numbers.

    Args:
        account_number: The bank account number to encrypt

    Returns:
        Encrypted account number
    """
    return FieldEncryption.encrypt(account_number)


def decrypt_bank_details(encrypted_account: str) -> str:
    """
    Convenience function to decrypt bank account numbers.

    Args:
        encrypted_account: The encrypted bank account number

    Returns:
        Decrypted account number
    """
    return FieldEncryption.decrypt(encrypted_account)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for display purposes (e.g., ****1234).

    Args:
        data: The sensitive data to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""

    return "*" * (len(data) - visible_chars) + data[-visible_chars:]
