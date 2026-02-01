"""SendGrid dynamic template email service for all email types."""

import base64
import json
import logging
import os

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import (
        Attachment,
        Content,
        FileContent,
        FileName,
        FileType,
        From,
        Mail,
        Personalization,
        ReplyTo,
        TemplateId,
        To,
    )
except ImportError:
    SendGridAPIClient = None
    Attachment = None
    Content = None
    FileContent = None
    FileName = None
    FileType = None
    From = None
    Mail = None
    Personalization = None
    ReplyTo = None
    TemplateId = None
    To = None
try:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception):
    WEASYPRINT_AVAILABLE = False
    HTML = None
    FontConfiguration = None


class SendGridEmailService:
    """Service for sending emails using SendGrid dynamic templates.

    Smart Direct Sending:
    - Emails send FROM platform owner's verified email (technical requirement)
    - Emails show user's business details prominently
    - Reply-To header routes replies directly to user's business email
    - Users can send directly without SendGrid verification!
    """

    # Template IDs - set these in your environment variables
    TEMPLATE_IDS = {
        "invoice_ready": os.environ.get("SENDGRID_INVOICE_READY_TEMPLATE_ID"),
        "invoice_paid": os.environ.get("SENDGRID_INVOICE_PAID_TEMPLATE_ID"),
        "payment_reminder": os.environ.get("SENDGRID_PAYMENT_REMINDER_TEMPLATE_ID"),
        "new_user_welcome": os.environ.get("SENDGRID_NEW_USER_WELCOME_TEMPLATE_ID"),
        "password_reset": os.environ.get("SENDGRID_PASSWORD_RESET_TEMPLATE_ID"),
        "admin_alert": os.environ.get("SENDGRID_ADMIN_ALERT_TEMPLATE_ID"),
    }

    def __init__(self):
        self.api_key = os.environ.get("SENDGRID_API_KEY")
        # Custom identities configuration
        self.IDENTITIES = {
            "admin": "admin@invoiceflow.com.ng",
            "support": "support@invoiceflow.com.ng",
            "hello": "hello@invoiceflow.com.ng",
            "info": "info@invoiceflow.com.ng",
            "noreply": os.environ.get("SENDGRID_FROM_EMAIL", "noreply@invoiceflow.com.ng")
        }
        self.from_email = self.IDENTITIES["noreply"]
        self.PLATFORM_FROM_EMAIL = self.from_email
        self.platform_from_name = "InvoiceFlow"
        self.is_configured = bool(self.api_key)

        if self.is_configured and self.api_key and SendGridAPIClient is not None:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None

    def _get_api_with_validation(self, url: str, headers: dict, timeout: int = 5) -> dict | None:
        """Safely get API response with proper URL validation."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return None
            
            import requests
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def _get_invoice_view_url(self, invoice):
        """Generate public URL for the invoice."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/public/invoice/{invoice.invoice_id}/"

    def _get_dashboard_url(self):
        """Generate dashboard URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/dashboard/"

    def _get_help_url(self):
        """Generate help/FAQ URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/faq/"

    def _get_verification_url(self, token):
        """Generate email verification URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/verify-email/{token}/"

    def _get_password_reset_url(self, token):
        """Generate password reset URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/password-reset/confirm/{token}/"

    # ============ INVOICE EMAILS ============

    def send_invoice_ready(self, invoice, recipient_email, template_id=None):
        """Send 'Invoice Ready' notification to client."""
        template_id = template_id or self.TEMPLATE_IDS.get("invoice_ready")

        subtotal = invoice.subtotal
        tax_rate = invoice.tax_rate
        discount = invoice.discount
        discount_amount = (subtotal * discount) / 100
        tax_amount = ((subtotal - discount_amount) * tax_rate) / 100

        template_data = {
            "invoice_id": invoice.invoice_id,
            "invoice_date": invoice.invoice_date.strftime("%B %d, %Y"),
            "due_date": invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "N/A",
            "client_name": invoice.client_name,
            "business_name": invoice.business_name,
            "business_email": invoice.business_email,
            "business_phone": invoice.business_phone,
            "currency": invoice.currency,
            "subtotal": float(subtotal),
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "discount_amount": float(discount_amount),
            "total_amount": f"{invoice.currency} {invoice.total:.2f}",
            "invoice_url": self._get_invoice_view_url(invoice),
            "line_items": [
                {"description": item.description, "quantity": item.quantity, "total": item.total}
                for item in invoice.line_items.all()
            ],
            "notes": invoice.notes
        }

        # If no SendGrid template ID is set, use local HTML/Text templates
        if not template_id:
            html_content = render_to_string("invoices/emails/invoice_ready.html", template_data)
            text_content = render_to_string("invoices/emails/invoice_ready.txt", template_data)
            return self._send_html_email(
                to_email=recipient_email,
                subject=f"Invoice #{invoice.invoice_id} Ready",
                plain_text=text_content,
                html_content=html_content
            )

        return self._send_email(
            user_business_email=invoice.business_email,
            from_name=invoice.business_name,
            to_email=recipient_email,
            template_id=template_id,
            template_data=template_data,
            subject=f"Invoice #{invoice.invoice_id} Ready",
            invoice=invoice,
        )

    def send_invoice_paid(self, invoice, recipient_email, template_id=None):
        """Send 'Invoice Paid' notification.

        Sends from platform owner's verified email with Reply-To user's business email.
        No SendGrid verification needed for users!
        """
        template_id = template_id or self.TEMPLATE_IDS.get("invoice_paid")

        template_data = {
            "invoice_id": invoice.invoice_id,
            "client_name": invoice.client_name,
            "business_name": invoice.business_name,
            "currency": invoice.currency,
            "total_amount": f"{invoice.currency} {invoice.total:.2f}",
            "paid_date": invoice.updated_at.strftime("%B %d, %Y"),
        }

        return self._send_email(
            user_business_email=invoice.business_email,
            from_name=invoice.business_name,
            to_email=recipient_email,
            template_id=template_id,
            template_data=template_data,
            subject=f"Invoice #{invoice.invoice_id} - Payment Received",
        )

    def send_invoice_email(self, invoice, recipient_email=None, template_id=None, subject_override=None, body_override=None):
        """Generic method to send invoice email with possible overrides."""
        recipient_email = recipient_email or invoice.client_email
        
        if subject_override and body_override:
            # Send simple HTML email with custom content
            return self._send_html_email(
                to_email=recipient_email,
                subject=subject_override,
                plain_text=body_override,
                html_content="<div style='font-family: sans-serif;'>" + body_override.replace('\n', '<br>') + "</div>"
            )
        
        # Fallback to standard reminder template
        return self.send_payment_reminder(invoice, recipient_email, template_id)

    @staticmethod
    def send_invoice_email_static(invoice, recipient_email=None, subject_override=None, body_override=None):
        """Static wrapper for backward compatibility and easy access."""
        service = SendGridEmailService()
        return service.send_invoice_email(invoice, recipient_email, subject_override=subject_override, body_override=body_override)

    # Alias for existing code that calls SendGridService.send_invoice_email
    # Note: I'll need to check if there's a SendGridService alias or if I should rename the class

    # ============ USER EMAILS ============

    def send_welcome_email(self, user, template_id=None):
        """Send welcome email to new user."""
        template_id = template_id or self.TEMPLATE_IDS.get("new_user_welcome")

        template_data = {
            "first_name": user.first_name or user.username,
            "username": user.username,
            "email": user.email,
            "dashboard_url": self._get_dashboard_url(),
            "help_url": self._get_help_url(),
        }

        return self._send_email(
            user_business_email=None,
            from_name="InvoiceFlow",
            to_email=user.email,
            template_id=template_id,
            template_data=template_data,
            subject="Welcome to InvoiceFlow!",
        )

    def send_verification_email(self, user, verification_token):
        """Send email verification link to user using hello@ identity."""
        verification_url = self._get_verification_url(verification_token)
        first_name = user.first_name or user.username
        from_email = self.IDENTITIES.get("hello", self.from_email)

        plain_text = f"""Hello {first_name},

Thank you for signing up for InvoiceFlow!

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
The InvoiceFlow Team"""

        html_content = f"""
<div style="font-family: Inter, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #6366f1;">Welcome to InvoiceFlow!</h2>
    <p>Hello {first_name},</p>
    <p>Thank you for signing up for InvoiceFlow! Please verify your email address to complete your registration.</p>
    <p style="margin: 30px 0;">
        <a href="{verification_url}" style="background: linear-gradient(135deg, #6366f1, #818cf8); color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">Verify Email Address</a>
    </p>
    <p style="color: #6b7280; font-size: 14px;">This link will expire in 24 hours.</p>
    <p style="color: #6b7280; font-size: 14px;">If you didn't create an account, please ignore this email.</p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="color: #9ca3af; font-size: 12px;">Best regards,<br>The InvoiceFlow Team</p>
</div>
"""

        return self._send_html_email(
            to_email=user.email,
            subject="Verify your InvoiceFlow account",
            plain_text=plain_text,
            html_content=html_content,
            from_email_override=from_email
        )

    def send_password_reset_email(self, user, reset_token, template_id=None):
        """Send password reset email using support@ identity."""
        template_id = template_id or self.TEMPLATE_IDS.get("password_reset")
        reset_url = self._get_password_reset_url(reset_token)
        first_name = user.first_name or user.username
        from_email = self.IDENTITIES.get("support", self.from_email)

        if template_id:
            template_data = {
                "first_name": first_name,
                "username": user.username,
                "reset_url": reset_url,
                "expires_in": "24 hours",
                "support_email": "support@invoiceflow.com.ng",
            }
            return self._send_email(
                user_business_email=None,
                from_name="InvoiceFlow Support",
                to_email=user.email,
                template_id=template_id,
                template_data=template_data,
                subject="Password Reset Request",
                from_email_override=from_email
            )

        plain_text = f"""Hello {first_name},

You requested a password reset for your InvoiceFlow account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request a password reset, please ignore this email.

Best regards,
The InvoiceFlow Team"""

        html_content = f"""
<div style="font-family: Inter, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #6366f1;">Password Reset Request</h2>
    <p>Hello {first_name},</p>
    <p>You requested a password reset for your InvoiceFlow account.</p>
    <p style="margin: 30px 0;">
        <a href="{reset_url}" style="background: linear-gradient(135deg, #6366f1, #818cf8); color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">Reset Password</a>
    </p>
    <p style="color: #6b7280; font-size: 14px;">This link will expire in 24 hours.</p>
    <p style="color: #6b7280; font-size: 14px;">If you didn't request a password reset, please ignore this email.</p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="color: #9ca3af; font-size: 12px;">Best regards,<br>The InvoiceFlow Team</p>
</div>
"""

        return self._send_html_email(
            to_email=user.email,
            subject="Password Reset Request",
            plain_text=plain_text,
            html_content=html_content,
            from_email_override=from_email
        )

    # ============ ADMIN EMAILS ============

    def send_admin_alert(self, alert_type, data, admin_email, template_id=None):
        """Send admin alert email (invoice viewed, etc)."""
        template_id = template_id or self.TEMPLATE_IDS.get("admin_alert")

        template_data = {
            "alert_type": alert_type,
            "timestamp": data.get("timestamp", ""),
            "details": data.get("details", ""),
            "action_url": data.get("action_url", ""),
            "invoice_id": data.get("invoice_id", ""),
            "user_name": data.get("user_name", "Unknown User"),
            "action_taken": data.get("action_taken", "Unknown Action"),
        }

        return self._send_email(
            user_business_email=None,
            from_name="InvoiceFlow Admin",
            to_email=admin_email,
            template_id=template_id,
            template_data=template_data,
            subject=f"Admin Alert: {alert_type}",
        )

    def send_payment_reminder(self, invoice, recipient_email, template_id=None):
        """Send payment reminder to client."""
        template_id = template_id or self.TEMPLATE_IDS.get("payment_reminder")

        template_data = {
            "invoice_id": invoice.invoice_id,
            "due_date": invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "N/A",
            "client_name": invoice.client_name,
            "business_name": invoice.business_name,
            "currency": invoice.currency,
            "total_amount": f"{invoice.currency} {invoice.total:.2f}",
            "invoice_url": self._get_invoice_view_url(invoice),
        }

        if not template_id:
            html_content = render_to_string("invoices/emails/payment_reminder.html", template_data)
            text_content = render_to_string("invoices/emails/payment_reminder.txt", template_data)
            return self._send_html_email(
                to_email=recipient_email,
                subject=f"Reminder: Invoice #{invoice.invoice_id} Payment Due",
                plain_text=text_content,
                html_content=html_content
            )

        return self._send_email(
            user_business_email=invoice.business_email,
            from_name=invoice.business_name,
            to_email=recipient_email,
            template_id=template_id,
            template_data=template_data,
            subject=f"Reminder: Invoice #{invoice.invoice_id} Payment Due",
            invoice=invoice,
        )

    def _get_invoice_view_url(self, invoice):
        """Generate public URL for the invoice."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/public/invoice/{invoice.invoice_id}/"

    def _get_dashboard_url(self):
        """Generate dashboard URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/dashboard/"

    def _get_help_url(self):
        """Generate help/FAQ URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/faq/"

    def _get_verification_url(self, token):
        """Generate email verification URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/verify-email/{token}/"

    def _get_password_reset_url(self, token):
        """Generate password reset URL."""
        domain = os.environ.get("PRODUCTION_DOMAIN", "localhost:5000")
        if os.environ.get("REPLIT_DEV_DOMAIN"):
            domain = os.environ.get("REPLIT_DEV_DOMAIN")
        return f"https://{domain}/password-reset/confirm/{token}/"

    # ============ HELPER METHODS ============

    def _send_email(
        self,
        user_business_email,
        from_name,
        to_email,
        template_id,
        template_data,
        subject,
        invoice=None,
        from_email_override=None,
    ):
        """Send email using SendGrid dynamic template."""
        if not self.is_configured:
            error_msg = "SendGrid API key not configured. Email sending is disabled."
            logger.warning(f"⚠️  {error_msg}")
            return {"status": "error", "message": error_msg, "configured": False}

        try:
            if not Mail or not From or not To:
                return {"status": "error", "message": "SendGrid helper classes not available"}

            sender = From(from_email_override or self.from_email, from_name)
            message = Mail(
                from_email=sender,
                to_emails=To(to_email),
                subject=subject,
            )

            if user_business_email and ReplyTo is not None:
                message.reply_to = ReplyTo(user_business_email)

            if template_id and TemplateId is not None and Personalization is not None:
                message.template_id = TemplateId(template_id)
                personalization = Personalization()
                personalization.add_to(To(to_email))
                personalization.dynamic_template_data = template_data
                message.add_personalization(personalization)
            else:
                return self._send_simple_email(
                    self.from_email, from_name, to_email, subject, template_data, user_business_email
                )

            if invoice and Attachment is not None and FileContent is not None and FileName is not None and FileType is not None:
                pdf_data = self._generate_invoice_pdf(invoice)
                if pdf_data:
                    attachment = Attachment(
                        FileContent(base64.b64encode(pdf_data).decode()),
                        FileName(f"Invoice_{invoice.invoice_id}.pdf"),
                        FileType("application/pdf"),
                    )
                    message.attachment = attachment

            if self.client is None:
                return {"status": "error", "message": "SendGrid client not initialized"}
            
            # Send with timeout and credit handling
            response = self.client.send(message)
            
            # Handle credit exceeded or other non-2xx but non-exception cases if any
            if 400 <= response.status_code < 600:
                logger.error(f"SendGrid returned error status: {response.status_code}")
                return {"status": "error", "message": f"SendGrid error: {response.status_code}", "response": response.status_code}

            return {
                "status": "sent",
                "response": response.status_code,
                "from_email": self.from_email,
                "reply_to": user_business_email,
            }

        except Exception as e:
            error_detail = self._parse_sendgrid_error(e)
            status_code = getattr(e, "status_code", None)
            
            # Specifically log credit exceeded (403 or similar)
            if status_code == 403:
                logger.error(f"❌ SendGrid Credit Exceeded or Forbidden: {error_detail}")
            else:
                logger.error(f"❌ SendGrid API Error: {error_detail}")
                
            return {"status": "error", "message": error_detail, "code": status_code}

    def _send_simple_email(self, from_email, from_name, to_email, subject, data, reply_to_email=None):
        """Fallback: Send simple HTML email without dynamic template."""
        if not self.is_configured:
            error_msg = "SendGrid API key not configured. Email sending is disabled."
            logger.warning(f"⚠️  {error_msg}")
            return {"status": "error", "message": error_msg, "configured": False}

        try:
            if not Mail or not From or not To:
                return {"status": "error", "message": "SendGrid helper classes not available"}

            plain_text = self._format_plain_text(data)

            sender = From(from_email, from_name)
            message = Mail(
                from_email=sender,
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", plain_text),
            )

            if reply_to_email and ReplyTo is not None:
                message.reply_to = ReplyTo(reply_to_email)

            if self.client is None:
                return {"status": "error", "message": "SendGrid client not initialized"}
            response = self.client.send(message)
            return {"status": "sent", "response": response.status_code}

        except Exception as e:
            error_detail = self._parse_sendgrid_error(e)
            status_code = getattr(e, "status_code", None)
            logger.error(f"❌ SendGrid API Error: {error_detail}")
            return {"status": "error", "message": error_detail, "code": status_code}

    def _send_html_email(self, to_email, subject, plain_text, html_content, from_email_override=None):
        """Send an HTML email with plain text fallback."""
        if not self.is_configured:
            error_msg = "SendGrid API key not configured. Email sending is disabled."
            logger.warning(f"⚠️  {error_msg}")
            return {"status": "error", "message": error_msg, "configured": False}

        try:
            if not Mail or not From or not To:
                return {"status": "error", "message": "SendGrid helper classes not available"}

            sender = From(from_email_override or self.from_email, self.platform_from_name)
            message = Mail(
                from_email=sender,
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", plain_text) if plain_text else None,
                html_content=Content("text/html", html_content) if html_content else None,
            )

            if self.client is None:
                return {"status": "error", "message": "SendGrid client not initialized"}
            response = self.client.send(message)
            logger.info(f"✅ Email sent to {to_email}")
            return {"status": "sent", "response": response.status_code}

        except Exception as e:
            error_detail = self._parse_sendgrid_error(e)
            status_code = getattr(e, "status_code", None)
            logger.error(f"❌ SendGrid API Error: {error_detail}")
            return {"status": "error", "message": error_detail, "code": status_code}

    def _parse_sendgrid_error(self, error):
        """Parse SendGrid API error and provide helpful diagnostics."""
        try:
            status_code = error.status_code if hasattr(error, "status_code") else "Unknown"

            # Try to parse error body for details
            try:
                if hasattr(error, "body") and error.body:
                    error_data = json.loads(error.body)
                    if isinstance(error_data, dict):
                        errors = error_data.get("errors", [])
                        if errors and len(errors) > 0:
                            messages = [e.get("message", "") for e in errors]
                            error_msg = "; ".join(messages)

                            # Provide specific guidance based on error type
                            if "sender" in error_msg.lower() or "from" in error_msg.lower():
                                return f"[{status_code}] SENDER VERIFICATION ISSUE: {error_msg}\n→ Fix: Go to SendGrid → Sender Authentication → Verify your business email"
                            elif "api key" in error_msg.lower() or "invalid" in error_msg.lower():
                                return f"[{status_code}] INVALID API KEY: {error_msg}\n→ Fix: Check your API key has Full Access permissions and is valid"
                            elif "permission" in error_msg.lower() or "403" in str(status_code):
                                return f"[{status_code}] PERMISSION DENIED: API key lacks required permissions\n→ Fix: Create new API key with 'Full Access' at SendGrid → API Keys"
                            else:
                                return f"[{status_code}] {error_msg}"
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

            # Fallback with status code specific guidance
            if status_code == 401 or status_code == 403:
                return f"[{status_code}] Authentication/Permission Error: Check API key has 'Full Access' and verify sender email in SendGrid"
            elif status_code == 400:
                return f"[{status_code}] Bad Request: Check email format and invoice data"
            elif status_code == 429:
                return f"[{status_code}] Rate Limited: Too many requests, try again later"
            else:
                return f"[{status_code}] SendGrid API Error: {str(error)}"

        except Exception as parse_error:
            return f"Error encountered: {str(error)}\n(Unable to parse details: {str(parse_error)})"

    def _generate_invoice_pdf(self, invoice):
        """Generate PDF bytes for invoice using PDFService."""
        try:
            from .services import PDFService
            return PDFService.generate_pdf_bytes(invoice)
        except (ImportError, ValueError) as e:
            logger.error(f"Failed to generate PDF for email attachment: {e}")
            return None

    def _format_plain_text(self, data):
        """Format template data as plain text."""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _calculate_days_overdue(self, invoice):
        """Calculate days overdue for payment reminder."""
        from datetime import datetime

        if invoice.due_date:
            delta = datetime.now().date() - invoice.due_date
            if delta.days > 0:
                return str(delta.days)
        return "0"

    def _format_payment_info(self, invoice):
        """Format payment information for email."""
        if invoice.bank_name:
            return f"Bank: {invoice.bank_name}\nAccount: {invoice.account_name}\nAccount #: {invoice.account_number}"
        return "N/A"

    def _get_base_url(self):
        """Get base URL from environment or default to production domain."""
        base_url = os.environ.get("WEBHOOK_BASE_URL") or os.environ.get("API_BASE_URL")
        if base_url:
            return base_url.rstrip("/")
        return "https://invoiceflow.com.ng"

    def _get_invoice_view_url(self, invoice):
        """Get invoice view URL for email links."""
        return f"{self._get_base_url()}/invoices/invoice/{invoice.id}/"

    def _get_dashboard_url(self):
        """Get dashboard URL."""
        return f"{self._get_base_url()}/invoices/dashboard/"

    def _get_help_url(self):
        """Get help/documentation URL."""
        return f"{self._get_base_url()}/faq/"

    def _get_password_reset_url(self, token):
        """Get password reset URL."""
        return f"{self._get_base_url()}/password-reset-confirm/{token}/"

    def _get_verification_url(self, token):
        """Get email verification URL."""
        return f"{self._get_base_url()}/verify-email/{token}/"

    def send_generic_email(self, to_email, subject, html_content, text_content=None):
        """Send a generic email with custom HTML content.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email
            text_content: Optional plain text version

        Returns:
            dict: Result with 'status' and 'message' keys
        """
        if not self.is_configured:
            return {
                "status": "error",
                "configured": False,
                "message": "SendGrid API key not configured",
            }

        try:
            message = Mail()
            message.from_email = From(self.from_email, self.platform_from_name)
            message.to = To(to_email)
            message.subject = subject
            
            content_list = []
            if text_content:
                content_list.append(Content("text/plain", text_content))
            content_list.append(Content("text/html", html_content))
            message.content = content_list

            if self.client is None:
                return {"status": "error", "message": "SendGrid client not initialized"}
            response = self.client.send(message)

            logger.info(f"Generic email sent to {to_email}: {subject}")
            return {
                "status": "sent",
                "message": f"Email sent successfully to {to_email}",
                "status_code": response.status_code,
            }
        except Exception as e:
            logger.error(f"Failed to send generic email: {str(e)}")
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

    def send_test_email(self, recipient_email):
        """Send a test email to verify SendGrid configuration.

        Args:
            recipient_email: Email address to send test to

        Returns:
            dict: Result with 'status' and 'message' keys
        """
        if not self.is_configured:
            return {
                "status": "error",
                "configured": False,
                "message": "SendGrid API key not configured",
            }

        try:
            message = Mail()
            message.from_email = From(self.from_email, self.platform_from_name)
            message.to = To(recipient_email)
            message.subject = "InvoiceFlow - Email Test"
            message.content = [
                Content(
                    "text/plain",
                    "If you received this email, your SendGrid configuration is working correctly!",
                ),
                Content(
                    "text/html",
                    "<strong>Success!</strong> If you received this email, your SendGrid configuration is working correctly!",
                ),
            ]

            if self.client is None:
                return {"status": "error", "message": "SendGrid client not initialized"}
            response = self.client.send(message)

            return {
                "status": "sent",
                "message": f"Test email sent successfully to {recipient_email}",
                "status_code": response.status_code,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to send test email: {str(e)}"}


# Convenience function
def get_email_service():
    """Get SendGrid email service instance."""
    return SendGridEmailService()
