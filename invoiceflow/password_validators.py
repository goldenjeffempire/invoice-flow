"""
Custom Password Validators for InvoiceFlow.
Implements enterprise-grade password security with breach detection.
"""

import hashlib
import logging
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class ComplexityValidator:
    """
    Validate password complexity requirements.
    Requires uppercase, lowercase, digit, and special character.
    """

    def __init__(self, min_uppercase=1, min_lowercase=1, min_digits=1, min_special=1):
        self.min_uppercase = min_uppercase
        self.min_lowercase = min_lowercase
        self.min_digits = min_digits
        self.min_special = min_special

    def validate(self, password, user=None):
        errors = []

        if len(re.findall(r"[A-Z]", password)) < self.min_uppercase:
            errors.append(
                _("Password must contain at least %(count)d uppercase letter(s).")
                % {"count": self.min_uppercase}
            )

        if len(re.findall(r"[a-z]", password)) < self.min_lowercase:
            errors.append(
                _("Password must contain at least %(count)d lowercase letter(s).")
                % {"count": self.min_lowercase}
            )

        if len(re.findall(r"\d", password)) < self.min_digits:
            errors.append(
                _("Password must contain at least %(count)d digit(s).") % {"count": self.min_digits}
            )

        special_chars = r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/`~;\']'
        if len(re.findall(special_chars, password)) < self.min_special:
            errors.append(
                _("Password must contain at least %(count)d special character(s).")
                % {"count": self.min_special}
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must contain at least: "
            "%(uppercase)d uppercase letter, "
            "%(lowercase)d lowercase letter, "
            "%(digits)d digit, and "
            "%(special)d special character."
        ) % {
            "uppercase": self.min_uppercase,
            "lowercase": self.min_lowercase,
            "digits": self.min_digits,
            "special": self.min_special,
        }


class BreachedPasswordValidator:
    """
    Check if password has been exposed in known data breaches.
    Uses the Have I Been Pwned API with k-anonymity (only sends first 5 chars of SHA1 hash).
    Falls back gracefully if the API is unavailable.
    """

    API_URL = "https://api.pwnedpasswords.com/range/"
    THRESHOLD = 3  # Minimum number of breaches to trigger rejection

    def __init__(self, threshold=None):
        if threshold is not None:
            self.threshold = threshold
        else:
            self.threshold = self.THRESHOLD

    def _get_pwned_count(self, password):
        """
        Check password against Have I Been Pwned database.
        Uses k-anonymity: only sends first 5 chars of SHA1 hash.
        Returns the number of times password appears in breaches, or -1 on error.
        """
        try:
            import requests

            sha1_password = (
                hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
            )
            prefix = sha1_password[:5]
            suffix = sha1_password[5:]

            response = requests.get(
                f"{self.API_URL}{prefix}",
                timeout=3,
                headers={"Add-Padding": "true"},
            )

            if response.status_code != 200:
                logger.warning(f"HIBP API returned status {response.status_code}")
                return -1

            for line in response.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    hash_suffix, count = parts
                    if hash_suffix == suffix:
                        return int(count)

            return 0

        except ImportError:
            logger.warning("requests library not available for breach checking")
            return -1
        except Exception as e:
            logger.warning(f"Error checking breached passwords: {e}")
            return -1

    def validate(self, password, user=None):
        pwned_count = self._get_pwned_count(password)

        if pwned_count >= self.threshold:
            raise ValidationError(
                _(
                    "This password has appeared in %(count)d data breaches and cannot be used. "
                    "Please choose a different password."
                )
                % {"count": pwned_count},
                code="password_breached",
            )

        if pwned_count > 0:
            logger.info(f"Password found in {pwned_count} breach(es) but below threshold")

    def get_help_text(self):
        return _("Your password cannot be one that has been exposed in known data breaches.")


class NoPersonalInfoValidator:
    """
    Validates that password doesn't contain personal information like email parts or username.
    """

    def validate(self, password, user=None):
        if user is None:
            return

        password_lower = password.lower()

        if user.username and len(user.username) >= 4:
            if user.username.lower() in password_lower:
                raise ValidationError(
                    _("Your password cannot contain your username."),
                    code="password_contains_username",
                )

        if hasattr(user, "email") and user.email:
            email_local = user.email.split("@")[0].lower()
            if len(email_local) >= 4 and email_local in password_lower:
                raise ValidationError(
                    _("Your password cannot contain parts of your email address."),
                    code="password_contains_email",
                )

        if hasattr(user, "first_name") and user.first_name:
            if len(user.first_name) >= 3 and user.first_name.lower() in password_lower:
                raise ValidationError(
                    _("Your password cannot contain your first name."),
                    code="password_contains_first_name",
                )

        if hasattr(user, "last_name") and user.last_name:
            if len(user.last_name) >= 3 and user.last_name.lower() in password_lower:
                raise ValidationError(
                    _("Your password cannot contain your last name."),
                    code="password_contains_last_name",
                )

    def get_help_text(self):
        return _("Your password cannot contain your username, email, or name.")
