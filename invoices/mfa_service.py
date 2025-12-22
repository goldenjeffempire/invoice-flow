# type: ignore
"""
Complete MFA Service (TOTP + Backup Codes)
Handles all multi-factor authentication logic
"""
import secrets
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode
from typing import Tuple, List
from django.utils import timezone
from django.conf import settings
from .models import MFAProfile


class MFAService:
    """Complete MFA (Multi-Factor Authentication) service"""
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a new TOTP secret for user"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(user_email: str, secret: str) -> str:
        """Generate QR code for authenticator app"""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=getattr(settings, 'MFA_ISSUER_NAME', 'InvoiceFlow')
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes for account recovery"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        return codes
    
    @staticmethod
    def verify_totp(secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token from authenticator app"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    @staticmethod
    def verify_backup_code(user, code: str) -> bool:
        """Verify and consume a backup code"""
        try:
            mfa_profile = user.mfa_profile
        except:
            return False
        
        if not mfa_profile.backup_codes:
            return False
        
        codes = mfa_profile.backup_codes
        code_upper = code.upper().strip()
        
        if code_upper in codes:
            # Remove used code
            codes.remove(code_upper)
            mfa_profile.backup_codes = codes
            mfa_profile.save()
            return True
        
        return False
    
    @staticmethod
    def enable_mfa(user, secret: str, backup_codes: List[str]) -> MFAProfile:
        """Enable MFA for user"""
        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret = secret
        mfa_profile.backup_codes = backup_codes
        mfa_profile.is_enabled = True
        mfa_profile.save()
        return mfa_profile
    
    @staticmethod
    def disable_mfa(user) -> bool:
        """Disable MFA for user"""
        try:
            mfa_profile = user.mfa_profile
            mfa_profile.is_enabled = False
            mfa_profile.secret = ""
            mfa_profile.backup_codes = []
            mfa_profile.save()
            return True
        except:
            return False
    
    @staticmethod
    def is_mfa_enabled(user) -> bool:
        """Check if MFA is enabled for user"""
        try:
            return user.mfa_profile.is_enabled
        except:
            return False
    
    @staticmethod
    def update_last_used(user):
        """Update MFA last used timestamp"""
        try:
            mfa_profile = user.mfa_profile
            mfa_profile.last_used = timezone.now()
            mfa_profile.save()
        except:
            pass
