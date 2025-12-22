# type: ignore
"""
Complete MFA Service (TOTP + Backup Codes + Verification)
Comprehensive multi-factor authentication with recovery codes
"""
import secrets
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode
from typing import Tuple, List, Optional
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from .models import MFAProfile


class MFAService:
    """Complete MFA (Multi-Factor Authentication) service with TOTP and backup codes"""
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a new TOTP secret for user (base32 encoded)"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(user_email: str, secret: str) -> str:
        """Generate QR code (PNG base64) for authenticator app provisioning"""
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
        """Generate backup codes (10 codes by default) for account recovery"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        return codes
    
    @staticmethod
    def verify_totp(secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token from authenticator app (6-digit code)"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except:
            return False
    
    @staticmethod
    def verify_backup_code(user, code: str) -> bool:
        """Verify and consume a backup code (removes used code)"""
        try:
            mfa_profile = user.mfa_profile
        except:
            return False
        
        if not mfa_profile.backup_codes:
            return False
        
        codes = mfa_profile.backup_codes
        code_upper = code.upper().strip()
        
        if code_upper in codes:
            codes.remove(code_upper)
            mfa_profile.backup_codes = codes
            mfa_profile.save()
            MFAService.update_last_used(user)
            return True
        
        return False
    
    @staticmethod
    @transaction.atomic
    def enable_mfa(user, secret: str, backup_codes: List[str]) -> MFAProfile:
        """Enable MFA for user with TOTP secret and backup codes"""
        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret = secret
        mfa_profile.backup_codes = backup_codes
        mfa_profile.is_enabled = True
        mfa_profile.save()
        return mfa_profile
    
    @staticmethod
    @transaction.atomic
    def disable_mfa(user) -> bool:
        """Disable MFA for user (requires password confirmation)"""
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
    def get_remaining_backup_codes(user) -> int:
        """Get count of remaining backup codes"""
        try:
            mfa_profile = user.mfa_profile
            return len(mfa_profile.backup_codes or [])
        except:
            return 0
    
    @staticmethod
    def update_last_used(user):
        """Update MFA last used timestamp"""
        try:
            mfa_profile = user.mfa_profile
            mfa_profile.last_used = timezone.now()
            mfa_profile.save(update_fields=['last_used'])
        except:
            pass
    
    @staticmethod
    def verify_mfa(user, token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify MFA token (TOTP or backup code)
        Returns: (success, message)
        """
        if not MFAService.is_mfa_enabled(user):
            return False, "MFA not enabled"
        
        try:
            mfa_profile = user.mfa_profile
            
            # Try TOTP first
            if MFAService.verify_totp(mfa_profile.secret, token):
                MFAService.update_last_used(user)
                return True, "TOTP verified"
            
            # Try backup code
            if MFAService.verify_backup_code(user, token):
                remaining = MFAService.get_remaining_backup_codes(user)
                msg = f"Backup code verified ({remaining} remaining)"
                return True, msg
            
            return False, "Invalid MFA token"
        except Exception as e:
            return False, f"MFA verification error: {str(e)}"
