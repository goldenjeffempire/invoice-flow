"""Reusable MFA helpers for InvoiceFlow.

This module provides lightweight TOTP and recovery-code utilities that can be
used by views, services, or middleware without coupling them directly to a
specific persistence strategy.
"""

from __future__ import annotations

import base64
import hashlib
import io
import secrets
from typing import Iterable, List

import pyotp
import qrcode
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse


def require_mfa(user) -> bool:
    """Return True when the user has MFA enabled and should complete a challenge."""
    if not getattr(user, 'is_authenticated', False):
        return False
    profile = getattr(user, 'profile', None)
    return bool(profile and getattr(profile, 'mfa_enabled', False))


def generate_secret() -> str:
    """Generate a new TOTP secret compatible with authenticator apps."""
    return pyotp.random_base32()


def _issuer_name() -> str:
    return getattr(settings, 'MFA_ISSUER_NAME', 'InvoiceFlow')


def _account_name(user) -> str:
    return getattr(user, 'email', None) or getattr(user, 'username', 'user')


def provisioning_uri(user, secret: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=_account_name(user), issuer_name=_issuer_name())


def generate_qr_code(user, secret: str) -> str:
    """Return a base64 data URL PNG for the given user's provisioning URI."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(provisioning_uri(user, secret))
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def generate_recovery_codes(count: int = 10) -> List[str]:
    """Generate user-friendly recovery codes."""
    codes = []
    for _ in range(max(1, count)):
        token = secrets.token_hex(4).upper()
        codes.append(f'{token[:4]}-{token[4:]}')
    return codes


def hash_recovery_codes(codes: Iterable[str]) -> List[str]:
    return [hashlib.sha256(code.encode('utf-8')).hexdigest() for code in codes]


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    try:
        return bool(pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1))
    except Exception:
        return False


def mfa_setup(request: HttpRequest):
    return redirect(reverse('invoices:mfa_setup'))


def mfa_verify(request: HttpRequest):
    return redirect(reverse('invoices:mfa_verify'))


def mfa_disable(request: HttpRequest):
    return redirect(reverse('invoices:mfa_disable'))


def mfa_regenerate_recovery(request: HttpRequest):
    return redirect(reverse('invoices:mfa_backup_codes'))
