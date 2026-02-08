import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from ..models import Client, ClientPortalToken, ClientPortalSession

logger = logging.getLogger(__name__)

class ClientPortalService:
    @staticmethod
    def generate_magic_link(client, ip_address=None, user_agent=""):
        token_str = secrets.token_urlsafe(64)
        expires_at = timezone.now() + timedelta(hours=1)
        ClientPortalToken.objects.create(
            client=client,
            token=token_str,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return f"{settings.SITE_URL}{reverse('invoices:portal_authenticate', kwargs={'token': token_str})}"

    @staticmethod
    def send_magic_link(client, magic_link):
        try:
            context = {
                'client_name': client.name,
                'magic_link': magic_link,
                'business_name': client.workspace.profile.company_name or "InvoiceFlow",
                'expires_in': "1 hour"
            }
            subject = f"Secure access to your client portal - {context['business_name']}"
            html_message = render_to_string('invoices/emails/portal_magic_link.html', context)
            plain_message = render_to_string('invoices/emails/portal_magic_link.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending magic link to {client.email}: {e}")
            return False

    @staticmethod
    def create_session(client, request):
        session_key = secrets.token_urlsafe(64)
        expires_at = timezone.now() + timedelta(days=7)
        return ClientPortalSession.objects.create(
            client=client,
            session_key=session_key,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            expires_at=expires_at,
            device_info={
                'browser': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'last_ip': request.META.get('REMOTE_ADDR')
            }
        )
