"""
Comprehensive Authentication Tests
Tests for signup, login, email verification, password reset, MFA, and session management.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from invoices.models import (
    UserProfile, MFAProfile, EmailToken, SecurityEvent,
    UserSession, LoginAttempt, KnownDevice, WorkspaceInvitation
)
from invoices.auth_services import (
    AuthService, MFAService, SessionService, InvitationService,
    SecurityService, PasswordValidator
)

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='TestPass123!'
    )
    user.is_active = True
    user.save()
    UserProfile.objects.create(user=user, email_verified=True)
    return user


@pytest.fixture
def inactive_user(db):
    user = User.objects.create_user(
        username='inactiveuser',
        email='inactive@example.com',
        password='TestPass123!'
    )
    user.is_active = False
    user.save()
    UserProfile.objects.create(user=user, email_verified=False)
    return user


@pytest.fixture
def authenticated_client(client, user):
    client.login(username='testuser', password='TestPass123!')
    return client


class TestPasswordValidator:
    def test_valid_password(self):
        is_valid, errors = PasswordValidator.validate('StrongPass1!', check_breach=False)
        assert is_valid is True
        assert len(errors) == 0

    def test_password_too_short(self):
        is_valid, errors = PasswordValidator.validate('Short1!', check_breach=False)
        assert is_valid is False
        assert any('8 characters' in e for e in errors)

    def test_password_missing_uppercase(self):
        is_valid, errors = PasswordValidator.validate('lowercase1!', check_breach=False)
        assert is_valid is False
        assert any('uppercase' in e for e in errors)

    def test_password_missing_lowercase(self):
        is_valid, errors = PasswordValidator.validate('UPPERCASE1!', check_breach=False)
        assert is_valid is False
        assert any('lowercase' in e for e in errors)

    def test_password_missing_number(self):
        is_valid, errors = PasswordValidator.validate('NoNumber!', check_breach=False)
        assert is_valid is False
        assert any('number' in e for e in errors)

    def test_password_missing_special(self):
        is_valid, errors = PasswordValidator.validate('NoSpecial1', check_breach=False)
        assert is_valid is False
        assert any('special' in e for e in errors)

    def test_common_password(self):
        is_valid, errors = PasswordValidator.validate('password', check_breach=False)
        assert is_valid is False
        assert any('common' in e for e in errors)


@pytest.mark.django_db
class TestSignup:
    def test_signup_page_loads(self, client):
        response = client.get(reverse('invoices:signup'))
        assert response.status_code == 200

    def test_signup_with_valid_data(self, client):
        with patch('invoices.auth_services.EmailService.send_verification_email', return_value=True):
            response = client.post(reverse('invoices:signup'), {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'StrongPass1!',
                'confirm_password': 'StrongPass1!',
                'terms_accepted': True,
            })
        assert response.status_code == 302
        assert User.objects.filter(username='newuser').exists()

    def test_signup_duplicate_email(self, client, user):
        response = client.post(reverse('invoices:signup'), {
            'username': 'anotheruser',
            'email': 'test@example.com',
            'password': 'StrongPass1!',
            'confirm_password': 'StrongPass1!',
            'terms_accepted': True,
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='anotheruser').exists()

    def test_signup_password_mismatch(self, client):
        response = client.post(reverse('invoices:signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass1!',
            'confirm_password': 'DifferentPass1!',
            'terms_accepted': True,
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='newuser').exists()

    def test_signup_weak_password(self, client):
        response = client.post(reverse('invoices:signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'weak',
            'confirm_password': 'weak',
            'terms_accepted': True,
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='newuser').exists()


@pytest.mark.django_db
class TestLogin:
    def test_login_page_loads(self, client):
        response = client.get(reverse('invoices:login'))
        assert response.status_code == 200

    def test_login_with_username(self, client, user):
        response = client.post(reverse('invoices:login'), {
            'username_or_email': 'testuser',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302

    def test_login_with_email(self, client, user):
        response = client.post(reverse('invoices:login'), {
            'username_or_email': 'test@example.com',
            'password': 'TestPass123!',
        })
        assert response.status_code == 302

    def test_login_invalid_password(self, client, user):
        response = client.post(reverse('invoices:login'), {
            'username_or_email': 'testuser',
            'password': 'wrongpassword',
        })
        assert response.status_code == 200

    def test_login_inactive_user(self, client, inactive_user):
        response = client.post(reverse('invoices:login'), {
            'username_or_email': 'inactiveuser',
            'password': 'TestPass123!',
        })
        assert response.status_code == 200

    def test_logout(self, authenticated_client):
        response = authenticated_client.get(reverse('invoices:logout'))
        assert response.status_code == 302


@pytest.mark.django_db
class TestEmailVerification:
    def test_verify_email_valid_token(self, client, inactive_user):
        token = EmailToken.create_token(inactive_user, EmailToken.TokenType.VERIFY)
        response = client.get(reverse('invoices:verify_email', args=[token.token]))
        assert response.status_code == 302
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True

    def test_verify_email_invalid_token(self, client):
        response = client.get(reverse('invoices:verify_email', args=['invalid-token']))
        assert response.status_code == 200

    def test_verify_email_expired_token(self, client, inactive_user):
        token = EmailToken.create_token(inactive_user, EmailToken.TokenType.VERIFY)
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()
        response = client.get(reverse('invoices:verify_email', args=[token.token]))
        assert response.status_code == 200

    def test_resend_verification_page_loads(self, client):
        response = client.get(reverse('invoices:resend_verification'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestPasswordReset:
    def test_password_reset_request_page_loads(self, client):
        response = client.get(reverse('invoices:password_reset'))
        assert response.status_code == 200

    def test_password_reset_request_creates_token(self, client, user):
        with patch('invoices.auth_services.EmailService.send_password_reset_email', return_value=True):
            response = client.post(reverse('invoices:password_reset'), {
                'email': 'test@example.com',
            })
        assert response.status_code == 302
        assert EmailToken.objects.filter(user=user, token_type=EmailToken.TokenType.RESET).exists()

    def test_password_reset_confirm_valid_token(self, client, user):
        token = EmailToken.create_token(user, EmailToken.TokenType.RESET, hours=1)
        response = client.post(reverse('invoices:password_reset_confirm', args=[token.token]), {
            'password': 'NewStrongPass1!',
            'confirm_password': 'NewStrongPass1!',
        })
        assert response.status_code == 302

    def test_password_reset_confirm_invalid_token(self, client):
        response = client.get(reverse('invoices:password_reset_confirm', args=['invalid-token']))
        assert response.status_code == 200


@pytest.mark.django_db
class TestMFA:
    def test_mfa_setup_requires_login(self, client):
        response = client.get(reverse('invoices:mfa_setup'))
        assert response.status_code == 302

    def test_mfa_setup_page_loads(self, authenticated_client):
        response = authenticated_client.get(reverse('invoices:mfa_setup'))
        assert response.status_code == 200

    def test_enable_mfa(self, user):
        secret = 'JBSWY3DPEHPK3PXP'
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()

        success, backup_codes, message = MFAService.enable_mfa(user, secret, code)
        assert success is True
        assert len(backup_codes) == 10
        assert MFAService.is_mfa_enabled(user) is True

    def test_verify_mfa_with_totp(self, user):
        import pyotp
        secret = pyotp.random_base32()
        MFAProfile.objects.create(
            user=user,
            secret=secret,
            is_enabled=True,
            recovery_codes=['ABCD1234', 'EFGH5678']
        )

        totp = pyotp.TOTP(secret)
        code = totp.now()
        success, message = MFAService.verify_mfa(user, code)
        assert success is True

    def test_verify_mfa_with_backup_code(self, user):
        MFAProfile.objects.create(
            user=user,
            secret='TESTSECRET',
            is_enabled=True,
            recovery_codes=['ABCD1234', 'EFGH5678']
        )

        success, message = MFAService.verify_mfa(user, 'ABCD1234')
        assert success is True
        user.mfa_profile.refresh_from_db()
        assert 'ABCD1234' not in user.mfa_profile.recovery_codes

    def test_disable_mfa_requires_password(self, user):
        MFAProfile.objects.create(
            user=user,
            secret='TESTSECRET',
            is_enabled=True,
            recovery_codes=[]
        )

        success, message = MFAService.disable_mfa(user, 'wrongpassword')
        assert success is False

        success, message = MFAService.disable_mfa(user, 'TestPass123!')
        assert success is True
        assert MFAService.is_mfa_enabled(user) is False


@pytest.mark.django_db
class TestSessionManagement:
    def test_get_user_sessions(self, user):
        UserSession.objects.create(
            user=user,
            session_key='test-session-1',
            ip_address='192.168.1.1',
            browser='Chrome',
            os='Windows',
            is_active=True,
            is_current=True
        )
        UserSession.objects.create(
            user=user,
            session_key='test-session-2',
            ip_address='192.168.1.2',
            browser='Firefox',
            os='macOS',
            is_active=True,
            is_current=False
        )

        sessions = SessionService.get_user_sessions(user)
        assert len(sessions) == 2

    def test_revoke_session(self, user):
        session = UserSession.objects.create(
            user=user,
            session_key='test-session',
            ip_address='192.168.1.1',
            is_active=True,
            is_current=False
        )

        success, message = SessionService.revoke_session(user, session.id)
        assert success is True
        session.refresh_from_db()
        assert session.is_active is False

    def test_cannot_revoke_current_session(self, user):
        session = UserSession.objects.create(
            user=user,
            session_key='test-session',
            ip_address='192.168.1.1',
            is_active=True,
            is_current=True
        )

        success, message = SessionService.revoke_session(user, session.id)
        assert success is False


@pytest.mark.django_db
class TestSecurityEvents:
    def test_log_security_event(self, user):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'

        SecurityService.log_event(user, 'login_success', request)
        assert SecurityEvent.objects.filter(user=user, event_type='login_success').exists()

    def test_log_login_attempt(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'

        SecurityService.log_login_attempt('testuser', request, success=False, failure_reason='invalid_password')
        assert LoginAttempt.objects.filter(username='testuser', success=False).exists()


@pytest.mark.django_db
class TestWorkspaceInvitation:
    def test_validate_invitation(self, user):
        invitation = WorkspaceInvitation.create_invitation(
            inviter=user,
            email='invited@example.com',
            role='member'
        )

        is_valid, inv, error = InvitationService.validate_invitation(invitation.token)
        assert is_valid is True
        assert inv.email == 'invited@example.com'

    def test_validate_expired_invitation(self, user):
        invitation = WorkspaceInvitation.create_invitation(
            inviter=user,
            email='invited@example.com',
            role='member'
        )
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()

        is_valid, inv, error = InvitationService.validate_invitation(invitation.token)
        assert is_valid is False
        assert 'expired' in error.lower()

    def test_accept_invitation(self, user):
        inviter = User.objects.create_user(
            username='inviter',
            email='inviter@example.com',
            password='TestPass123!'
        )
        invitation = WorkspaceInvitation.create_invitation(
            inviter=inviter,
            email='test@example.com',
            role='member'
        )

        success, message = InvitationService.accept_invitation(invitation.token, user)
        assert success is True
        invitation.refresh_from_db()
        assert invitation.accepted_at is not None


@pytest.mark.django_db
class TestAuthServiceRegistration:
    def test_register_user_success(self):
        with patch('invoices.auth_services.EmailService.send_verification_email', return_value=True):
            user, message = AuthService.register_user(
                username='newuser',
                email='newuser@example.com',
                password='StrongPass1!'
            )
        assert user is not None
        assert user.is_active is False
        assert UserProfile.objects.filter(user=user).exists()

    def test_register_user_duplicate_email(self, user):
        new_user, message = AuthService.register_user(
            username='anotheruser',
            email='test@example.com',
            password='StrongPass1!'
        )
        assert new_user is None
        assert 'already exists' in message.lower()


@pytest.mark.django_db
class TestAuthServiceAuthentication:
    def test_authenticate_user_success(self, user):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'

        authenticated_user, message, requires_mfa = AuthService.authenticate_user(
            request, 'testuser', 'TestPass123!'
        )
        assert authenticated_user is not None
        assert requires_mfa is False

    def test_authenticate_user_invalid_password(self, user):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'

        authenticated_user, message, requires_mfa = AuthService.authenticate_user(
            request, 'testuser', 'wrongpassword'
        )
        assert authenticated_user is None

    def test_authenticate_user_with_mfa(self, user):
        MFAProfile.objects.create(
            user=user,
            secret='TESTSECRET',
            is_enabled=True,
            recovery_codes=[]
        )

        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'

        authenticated_user, message, requires_mfa = AuthService.authenticate_user(
            request, 'testuser', 'TestPass123!'
        )
        assert authenticated_user is not None
        assert requires_mfa is True
