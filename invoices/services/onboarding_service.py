"""
Production-Grade Onboarding Service
Stepper-based onboarding with smart defaults, progress tracking, and workspace setup.
"""
import logging
from typing import Dict, Any, Tuple, Optional, List
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from ..models import UserProfile, Workspace, WorkspaceMember

logger = logging.getLogger(__name__)

ONBOARDING_STEPS = [
    {"id": 1, "name": "Welcome", "slug": "welcome", "icon": "hand-wave", "duration": 1, "required": True},
    {"id": 2, "name": "Business Profile", "slug": "business", "icon": "building", "duration": 3, "required": True},
    {"id": 3, "name": "Branding", "slug": "branding", "icon": "palette", "duration": 2, "required": False},
    {"id": 4, "name": "Tax & Compliance", "slug": "tax", "icon": "receipt", "duration": 2, "required": False},
    {"id": 5, "name": "Payments", "slug": "payments", "icon": "credit-card", "duration": 3, "required": False},
    {"id": 6, "name": "Data Import", "slug": "import", "icon": "upload", "duration": 2, "required": False},
    {"id": 7, "name": "Templates", "slug": "templates", "icon": "file-text", "duration": 1, "required": False},
    {"id": 8, "name": "Team", "slug": "team", "icon": "users", "duration": 2, "required": False},
]

REGION_DEFAULTS = {
    "ng": {
        "currency": "NGN",
        "timezone": "Africa/Lagos",
        "locale": "en-NG",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("7.5"),
        "wht_rate": Decimal("5.0"),
        "tax_id_type": "TIN",
        "bank_format": "NG",
    },
    "us": {
        "currency": "USD",
        "timezone": "America/New_York",
        "locale": "en-US",
        "date_format": "MM/DD/YYYY",
        "vat_rate": Decimal("0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "EIN",
        "bank_format": "US",
    },
    "gb": {
        "currency": "GBP",
        "timezone": "Europe/London",
        "locale": "en-GB",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("20.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
        "bank_format": "UK",
    },
    "eu": {
        "currency": "EUR",
        "timezone": "Europe/Paris",
        "locale": "en-EU",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("20.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
        "bank_format": "EU",
    },
    "za": {
        "currency": "ZAR",
        "timezone": "Africa/Johannesburg",
        "locale": "en-ZA",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("15.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
        "bank_format": "ZA",
    },
    "gh": {
        "currency": "GHS",
        "timezone": "Africa/Accra",
        "locale": "en-GH",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("15.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "TIN",
        "bank_format": "GH",
    },
    "ke": {
        "currency": "KES",
        "timezone": "Africa/Nairobi",
        "locale": "en-KE",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("16.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "PIN",
        "bank_format": "KE",
    },
}

BUSINESS_TYPE_TEMPLATES = {
    "freelancer": {
        "invoice_prefix": "INV",
        "invoice_style": "modern",
        "payment_terms": 14,
        "suggested_colors": {"primary": "#6366f1", "accent": "#10b981"},
    },
    "agency": {
        "invoice_prefix": "AGY",
        "invoice_style": "professional",
        "payment_terms": 30,
        "suggested_colors": {"primary": "#3b82f6", "accent": "#f59e0b"},
    },
    "consulting": {
        "invoice_prefix": "CON",
        "invoice_style": "classic",
        "payment_terms": 30,
        "suggested_colors": {"primary": "#1f2937", "accent": "#6366f1"},
    },
    "ecommerce": {
        "invoice_prefix": "ORD",
        "invoice_style": "modern",
        "payment_terms": 0,
        "suggested_colors": {"primary": "#059669", "accent": "#8b5cf6"},
    },
    "saas": {
        "invoice_prefix": "SUB",
        "invoice_style": "minimal",
        "payment_terms": 0,
        "suggested_colors": {"primary": "#7c3aed", "accent": "#06b6d4"},
    },
    "services": {
        "invoice_prefix": "SVC",
        "invoice_style": "professional",
        "payment_terms": 15,
        "suggested_colors": {"primary": "#2563eb", "accent": "#10b981"},
    },
    "construction": {
        "invoice_prefix": "PRJ",
        "invoice_style": "classic",
        "payment_terms": 30,
        "suggested_colors": {"primary": "#b45309", "accent": "#1f2937"},
    },
    "healthcare": {
        "invoice_prefix": "MED",
        "invoice_style": "professional",
        "payment_terms": 30,
        "suggested_colors": {"primary": "#0891b2", "accent": "#22c55e"},
    },
}


class OnboardingService:
    @classmethod
    def get_onboarding_state(cls, user) -> Dict[str, Any]:
        try:
            profile = UserProfile.objects.get(user=user)
            current_step = profile.onboarding_step
            
            steps_with_status = []
            for step in ONBOARDING_STEPS:
                step_copy = step.copy()
                if step["id"] < current_step:
                    step_copy["status"] = "completed"
                elif step["id"] == current_step:
                    step_copy["status"] = "current"
                else:
                    step_copy["status"] = "pending"
                steps_with_status.append(step_copy)
            
            progress_percentage = ((current_step - 1) / len(ONBOARDING_STEPS)) * 100
            
            return {
                "current_step": current_step,
                "total_steps": len(ONBOARDING_STEPS),
                "steps": steps_with_status,
                "progress_percentage": round(progress_percentage),
                "is_completed": profile.onboarding_completed,
                "started_at": profile.onboarding_started_at,
                "data": profile.onboarding_data or {},
            }
        except UserProfile.DoesNotExist:
            return {
                "current_step": 1,
                "total_steps": len(ONBOARDING_STEPS),
                "steps": ONBOARDING_STEPS,
                "progress_percentage": 0,
                "is_completed": False,
                "started_at": None,
                "data": {},
            }

    @classmethod
    def get_step_by_slug(cls, slug: str) -> Optional[Dict]:
        for step in ONBOARDING_STEPS:
            if step["slug"] == slug:
                return step
        return None

    @classmethod
    def get_step_url(cls, step_number: int) -> str:
        if step_number <= 0:
            step_number = 1
        if step_number > len(ONBOARDING_STEPS):
            return "invoices:onboarding_complete"
        
        step = ONBOARDING_STEPS[step_number - 1]
        return f"invoices:onboarding_{step['slug']}"

    @classmethod
    @transaction.atomic
    def save_welcome_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            region = data.get("region", "ng")
            business_type = data.get("business_type", "freelancer")
            
            region_defaults = REGION_DEFAULTS.get(region, REGION_DEFAULTS["ng"])
            business_defaults = BUSINESS_TYPE_TEMPLATES.get(business_type, BUSINESS_TYPE_TEMPLATES["freelancer"])
            
            profile.region = region
            profile.business_type = business_type
            profile.default_currency = region_defaults["currency"]
            profile.timezone = region_defaults["timezone"]
            profile.locale = region_defaults["locale"]
            profile.date_format = region_defaults["date_format"]
            profile.invoice_prefix = business_defaults["invoice_prefix"]
            profile.invoice_style = business_defaults["invoice_style"]
            profile.primary_color = business_defaults["suggested_colors"]["primary"]
            profile.accent_color = business_defaults["suggested_colors"]["accent"]
            
            if region_defaults["vat_rate"] > 0:
                profile.vat_registered = True
                profile.vat_rate = region_defaults["vat_rate"]
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["welcome"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 1:
                profile.onboarding_step = 2
            
            profile.save()
            
            return True, "Welcome step completed!"
            
        except Exception as e:
            logger.error(f"Welcome step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_business_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            company_name = data.get("company_name", "").strip()
            if not company_name:
                return False, "Company name is required."
            
            profile.company_name = company_name
            profile.business_email = data.get("business_email", user.email).strip()
            profile.business_phone = data.get("business_phone", "").strip()
            profile.business_address = data.get("business_address", "").strip()
            profile.business_city = data.get("business_city", "").strip()
            profile.business_state = data.get("business_state", "").strip()
            profile.business_country = data.get("business_country", "").strip()
            profile.business_postal_code = data.get("business_postal_code", "").strip()
            profile.business_website = data.get("business_website", "").strip()
            
            if profile.current_workspace:
                workspace = profile.current_workspace
                workspace.name = company_name
                workspace.save(update_fields=["name"])
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["business"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 2:
                profile.onboarding_step = 3
            
            profile.save()
            
            return True, "Business profile saved!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Business step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_branding_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            if data.get("primary_color"):
                profile.primary_color = data["primary_color"]
            if data.get("secondary_color"):
                profile.secondary_color = data["secondary_color"]
            if data.get("accent_color"):
                profile.accent_color = data["accent_color"]
            if data.get("invoice_style"):
                profile.invoice_style = data["invoice_style"]
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["branding"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 3:
                profile.onboarding_step = 4
            
            profile.save()
            
            return True, "Branding saved!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Branding step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_tax_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            profile.tax_id_number = data.get("tax_id_number", "").strip()
            profile.tax_id_type = data.get("tax_id_type", "").strip()
            profile.vat_registered = data.get("vat_registered", False)
            
            if profile.vat_registered:
                profile.vat_number = data.get("vat_number", "").strip()
                try:
                    profile.vat_rate = Decimal(str(data.get("vat_rate", "0")))
                except:
                    profile.vat_rate = Decimal("0")
            
            profile.wht_applicable = data.get("wht_applicable", False)
            if profile.wht_applicable:
                try:
                    profile.wht_rate = Decimal(str(data.get("wht_rate", "0")))
                except:
                    profile.wht_rate = Decimal("0")
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["tax"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 4:
                profile.onboarding_step = 5
            
            profile.save()
            
            return True, "Tax settings saved!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Tax step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_payments_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            profile.bank_name = data.get("bank_name", "").strip()
            profile.bank_account_name = data.get("bank_account_name", "").strip()
            profile.bank_account_number = data.get("bank_account_number", "").strip()
            profile.bank_routing_number = data.get("bank_routing_number", "").strip()
            profile.bank_swift_code = data.get("bank_swift_code", "").strip()
            profile.accept_card_payments = data.get("accept_card_payments", False)
            profile.accept_bank_transfers = data.get("accept_bank_transfers", True)
            profile.accept_mobile_money = data.get("accept_mobile_money", False)
            profile.payment_instructions = data.get("payment_instructions", "").strip()
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["payments"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 5:
                profile.onboarding_step = 6
            
            profile.save()
            
            return True, "Payment settings saved!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Payments step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_import_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["import"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 6:
                profile.onboarding_step = 7
            
            profile.save()
            
            return True, "Import step completed!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Import step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_templates_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            if data.get("invoice_prefix"):
                profile.invoice_prefix = data["invoice_prefix"]
            if data.get("invoice_start_number"):
                try:
                    profile.invoice_start_number = int(data["invoice_start_number"])
                except:
                    pass
            if data.get("invoice_numbering_format"):
                profile.invoice_numbering_format = data["invoice_numbering_format"]
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["templates"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 7:
                profile.onboarding_step = 8
            
            profile.save()
            
            return True, "Template settings saved!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Templates step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def save_team_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            onboarding_data = profile.onboarding_data or {}
            onboarding_data["team"] = data
            profile.onboarding_data = onboarding_data
            
            if profile.onboarding_step == 8:
                profile.onboarding_step = 9
            
            profile.save()
            
            return True, "Team step completed!"
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Team step error: {e}")
            return False, "Failed to save. Please try again."

    @classmethod
    @transaction.atomic
    def complete_onboarding(cls, user) -> Tuple[bool, str]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            profile.onboarding_completed = True
            profile.onboarding_completed_at = timezone.now()
            profile.save(update_fields=["onboarding_completed", "onboarding_completed_at"])
            
            return True, "Onboarding completed! Welcome to InvoiceFlow."
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found."
        except Exception as e:
            logger.error(f"Complete onboarding error: {e}")
            return False, "Failed to complete. Please try again."

    @classmethod
    def skip_step(cls, user) -> Tuple[bool, str, int]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            current_step = profile.onboarding_step
            if current_step < len(ONBOARDING_STEPS):
                profile.onboarding_step = current_step + 1
                profile.save(update_fields=["onboarding_step"])
                return True, "Step skipped.", profile.onboarding_step
            else:
                return True, "Onboarding complete.", current_step
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found.", 1
        except Exception as e:
            logger.error(f"Skip step error: {e}")
            return False, "Failed to skip. Please try again.", 1

    @classmethod
    def go_back(cls, user) -> Tuple[bool, str, int]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            current_step = profile.onboarding_step
            if current_step > 1:
                profile.onboarding_step = current_step - 1
                profile.save(update_fields=["onboarding_step"])
                return True, "Going back.", profile.onboarding_step
            else:
                return True, "Already at first step.", current_step
            
        except UserProfile.DoesNotExist:
            return False, "Profile not found.", 1
        except Exception as e:
            logger.error(f"Go back error: {e}")
            return False, "Failed. Please try again.", 1

    @classmethod
    def get_smart_defaults(cls, user) -> Dict[str, Any]:
        try:
            profile = UserProfile.objects.get(user=user)
            
            region_defaults = REGION_DEFAULTS.get(profile.region, {})
            business_defaults = BUSINESS_TYPE_TEMPLATES.get(profile.business_type, {})
            
            return {
                "region": region_defaults,
                "business": business_defaults,
                "profile": {
                    "company_name": profile.company_name,
                    "business_email": profile.business_email or user.email,
                    "currency": profile.default_currency,
                    "timezone": profile.timezone,
                }
            }
        except UserProfile.DoesNotExist:
            return {"region": {}, "business": {}, "profile": {}}
