import logging
from typing import Dict, Any, Tuple, Optional, List
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from ..models import UserProfile

logger = logging.getLogger(__name__)

ONBOARDING_STEPS = [
    {"id": 1, "name": "Welcome", "slug": "welcome", "icon": "hand-wave", "duration": 1},
    {"id": 2, "name": "Business Profile", "slug": "business", "icon": "building", "duration": 3},
    {"id": 3, "name": "Branding", "slug": "branding", "icon": "palette", "duration": 2},
    {"id": 4, "name": "Tax & Compliance", "slug": "tax", "icon": "receipt", "duration": 2},
    {"id": 5, "name": "Payments", "slug": "payments", "icon": "credit-card", "duration": 3},
    {"id": 6, "name": "Data Import", "slug": "import", "icon": "upload", "duration": 2},
    {"id": 7, "name": "Templates", "slug": "templates", "icon": "file-text", "duration": 1},
    {"id": 8, "name": "Team", "slug": "team", "icon": "users", "duration": 2},
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
    },
    "us": {
        "currency": "USD",
        "timezone": "America/New_York",
        "locale": "en-US",
        "date_format": "MM/DD/YYYY",
        "vat_rate": Decimal("0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "EIN",
    },
    "gb": {
        "currency": "GBP",
        "timezone": "Europe/London",
        "locale": "en-GB",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("20.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
    },
    "eu": {
        "currency": "EUR",
        "timezone": "Europe/Berlin",
        "locale": "en-EU",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("19.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
    },
    "za": {
        "currency": "ZAR",
        "timezone": "Africa/Johannesburg",
        "locale": "en-ZA",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("15.0"),
        "wht_rate": Decimal("0"),
        "tax_id_type": "VAT",
    },
    "gh": {
        "currency": "GHS",
        "timezone": "Africa/Accra",
        "locale": "en-GH",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("15.0"),
        "wht_rate": Decimal("5.0"),
        "tax_id_type": "TIN",
    },
    "ke": {
        "currency": "KES",
        "timezone": "Africa/Nairobi",
        "locale": "en-KE",
        "date_format": "DD/MM/YYYY",
        "vat_rate": Decimal("16.0"),
        "wht_rate": Decimal("5.0"),
        "tax_id_type": "PIN",
    },
}

BUSINESS_TYPE_SUGGESTIONS = {
    "freelancer": {
        "invoice_prefix": "INV",
        "invoice_style": "minimal",
    },
    "agency": {
        "invoice_prefix": "AGY",
        "invoice_style": "modern",
    },
    "consulting": {
        "invoice_prefix": "CON",
        "invoice_style": "professional",
    },
    "ecommerce": {
        "invoice_prefix": "ORD",
        "invoice_style": "modern",
    },
    "saas": {
        "invoice_prefix": "SUB",
        "invoice_style": "minimal",
    },
    "services": {
        "invoice_prefix": "SVC",
        "invoice_style": "classic",
    },
    "construction": {
        "invoice_prefix": "PRJ",
        "invoice_style": "bold",
    },
    "healthcare": {
        "invoice_prefix": "MED",
        "invoice_style": "professional",
    },
}


class OnboardingService:
    @classmethod
    def get_steps(cls) -> List[Dict[str, Any]]:
        return ONBOARDING_STEPS.copy()
    
    @classmethod
    def get_total_steps(cls) -> int:
        return len(ONBOARDING_STEPS)
    
    @classmethod
    def get_step_by_slug(cls, slug: str) -> Optional[Dict[str, Any]]:
        for step in ONBOARDING_STEPS:
            if step["slug"] == slug:
                return step
        return None
    
    @classmethod
    def get_onboarding_status(cls, user) -> Dict[str, Any]:
        profile = user.profile
        total_steps = cls.get_total_steps()
        current_step = min(profile.onboarding_step, total_steps)
        
        steps = []
        for step in ONBOARDING_STEPS:
            steps.append({
                **step,
                "completed": step["id"] < current_step,
                "current": step["id"] == current_step,
                "locked": step["id"] > current_step and not profile.onboarding_completed,
            })
        
        completed_steps = current_step - 1 if not profile.onboarding_completed else total_steps
        progress_percent = int((completed_steps / total_steps) * 100)
        
        time_to_first_invoice = None
        if profile.first_invoice_created_at and profile.onboarding_started_at:
            delta = profile.first_invoice_created_at - profile.onboarding_started_at
            time_to_first_invoice = {
                "days": delta.days,
                "hours": delta.seconds // 3600,
                "minutes": (delta.seconds % 3600) // 60,
                "total_minutes": int(delta.total_seconds() / 60),
            }
        
        estimated_time_remaining = sum(
            step["duration"] for step in ONBOARDING_STEPS 
            if step["id"] >= current_step
        )
        
        return {
            "current_step": current_step,
            "current_step_slug": ONBOARDING_STEPS[current_step - 1]["slug"] if current_step <= total_steps else "complete",
            "total_steps": total_steps,
            "is_completed": profile.onboarding_completed,
            "steps": steps,
            "progress_percent": progress_percent,
            "completed_steps": completed_steps,
            "started_at": profile.onboarding_started_at,
            "completed_at": profile.onboarding_completed_at,
            "time_to_first_invoice": time_to_first_invoice,
            "estimated_time_remaining": estimated_time_remaining,
        }
    
    @classmethod
    def get_checklist(cls, user) -> List[Dict[str, Any]]:
        profile = user.profile
        
        checklist = [
            {
                "id": "business_profile",
                "title": "Complete business profile",
                "completed": bool(profile.company_name and profile.business_type),
                "step": 2,
            },
            {
                "id": "branding",
                "title": "Set up branding",
                "completed": profile.onboarding_step > 3 or profile.onboarding_completed,
                "step": 3,
            },
            {
                "id": "tax_setup",
                "title": "Configure tax settings",
                "completed": profile.onboarding_step > 4 or profile.onboarding_completed,
                "step": 4,
            },
            {
                "id": "payment_info",
                "title": "Add payment information",
                "completed": bool(profile.bank_name or profile.accept_card_payments),
                "step": 5,
            },
            {
                "id": "first_invoice",
                "title": "Create your first invoice",
                "completed": profile.first_invoice_created_at is not None,
                "step": None,
            },
        ]
        
        return checklist
    
    @classmethod
    def get_region_defaults(cls, region: str) -> Dict[str, Any]:
        return REGION_DEFAULTS.get(region, REGION_DEFAULTS.get("ng", {}))
    
    @classmethod
    def get_business_type_suggestions(cls, business_type: str) -> Dict[str, Any]:
        return BUSINESS_TYPE_SUGGESTIONS.get(business_type, {})
    
    @classmethod
    def apply_contextual_defaults(cls, profile: UserProfile, region: str = None, business_type: str = None) -> None:
        if region:
            defaults = cls.get_region_defaults(region)
            profile.default_currency = defaults.get("currency", profile.default_currency)
            profile.timezone = defaults.get("timezone", profile.timezone)
            profile.locale = defaults.get("locale", profile.locale)
            profile.date_format = defaults.get("date_format", profile.date_format)
            profile.vat_rate = defaults.get("vat_rate", profile.vat_rate)
            profile.wht_rate = defaults.get("wht_rate", profile.wht_rate)
            profile.tax_id_type = defaults.get("tax_id_type", profile.tax_id_type)
        
        if business_type:
            suggestions = cls.get_business_type_suggestions(business_type)
            if not profile.invoice_prefix or profile.invoice_prefix == "INV":
                profile.invoice_prefix = suggestions.get("invoice_prefix", profile.invoice_prefix)
            if profile.invoice_style == "modern":
                profile.invoice_style = suggestions.get("invoice_style", profile.invoice_style)
    
    @classmethod
    def start_onboarding(cls, user) -> None:
        profile = user.profile
        if not profile.onboarding_started_at:
            profile.onboarding_started_at = timezone.now()
            profile.save(update_fields=["onboarding_started_at"])
    
    @classmethod
    @transaction.atomic
    def save_welcome_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        region = data.get("region", "").strip()
        if region and region in dict(UserProfile.REGION_CHOICES):
            profile.region = region
            cls.apply_contextual_defaults(profile, region=region)
        
        if profile.onboarding_step == 1:
            profile.onboarding_step = 2
        
        if not profile.onboarding_started_at:
            profile.onboarding_started_at = timezone.now()
        
        profile.save()
        return True, "Welcome step completed", errors
    
    @classmethod
    @transaction.atomic
    def save_business_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        company_name = data.get("company_name", "").strip()
        if not company_name:
            errors["company_name"] = "Company name is required"
        elif len(company_name) > 255:
            errors["company_name"] = "Company name must be 255 characters or less"
        
        business_type = data.get("business_type", "").strip()
        if not business_type:
            errors["business_type"] = "Business type is required"
        
        business_email = data.get("business_email", "").strip()
        if business_email:
            try:
                validate_email(business_email)
            except ValidationError:
                errors["business_email"] = "Enter a valid email address"
        
        if errors:
            return False, "Please fix the errors below", errors
        
        profile.company_name = company_name
        profile.business_type = business_type
        profile.business_email = business_email or user.email
        profile.business_phone = data.get("business_phone", "").strip()
        profile.business_address = data.get("business_address", "").strip()
        profile.business_city = data.get("business_city", "").strip()
        profile.business_state = data.get("business_state", "").strip()
        profile.business_country = data.get("business_country", "").strip()
        profile.business_postal_code = data.get("business_postal_code", "").strip()
        profile.business_website = data.get("business_website", "").strip()
        
        region = data.get("region", profile.region).strip()
        if region and region != profile.region:
            profile.region = region
            cls.apply_contextual_defaults(profile, region=region)
        
        cls.apply_contextual_defaults(profile, business_type=business_type)
        
        if profile.onboarding_step <= 2:
            profile.onboarding_step = 3
        
        profile.save()
        return True, "Business profile saved", errors
    
    @classmethod
    @transaction.atomic
    def save_branding_step(cls, user, data: Dict[str, Any], logo_file=None) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        primary_color = data.get("primary_color", "").strip()
        if primary_color:
            if not primary_color.startswith("#") or len(primary_color) != 7:
                errors["primary_color"] = "Invalid color format (use #RRGGBB)"
            else:
                profile.primary_color = primary_color
        
        secondary_color = data.get("secondary_color", "").strip()
        if secondary_color:
            if not secondary_color.startswith("#") or len(secondary_color) != 7:
                errors["secondary_color"] = "Invalid color format (use #RRGGBB)"
            else:
                profile.secondary_color = secondary_color
        
        accent_color = data.get("accent_color", "").strip()
        if accent_color:
            if not accent_color.startswith("#") or len(accent_color) != 7:
                errors["accent_color"] = "Invalid color format (use #RRGGBB)"
            else:
                profile.accent_color = accent_color
        
        invoice_style = data.get("invoice_style", "").strip()
        if invoice_style and invoice_style in dict(UserProfile.INVOICE_STYLE_CHOICES):
            profile.invoice_style = invoice_style
        
        if logo_file:
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if hasattr(logo_file, "content_type") and logo_file.content_type not in allowed_types:
                errors["company_logo"] = "Please upload a valid image (JPEG, PNG, GIF, or WebP)"
            elif logo_file.size > 5 * 1024 * 1024:
                errors["company_logo"] = "Logo must be less than 5MB"
            else:
                profile.company_logo = logo_file
        
        if errors:
            return False, "Please fix the errors below", errors
        
        if profile.onboarding_step <= 3:
            profile.onboarding_step = 4
        
        profile.save()
        return True, "Branding settings saved", errors
    
    @classmethod
    @transaction.atomic
    def save_tax_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        tax_id_number = data.get("tax_id_number", "").strip()
        tax_id_type = data.get("tax_id_type", "").strip()
        profile.tax_id_number = tax_id_number
        profile.tax_id_type = tax_id_type
        
        vat_registered = data.get("vat_registered") in [True, "true", "on", "1"]
        profile.vat_registered = vat_registered
        
        if vat_registered:
            vat_number = data.get("vat_number", "").strip()
            if not vat_number:
                errors["vat_number"] = "VAT number is required when VAT registered"
            profile.vat_number = vat_number
            
            try:
                vat_rate = Decimal(str(data.get("vat_rate", "0")))
                if vat_rate < 0 or vat_rate > 100:
                    errors["vat_rate"] = "VAT rate must be between 0 and 100"
                profile.vat_rate = vat_rate
            except (ValueError, TypeError):
                errors["vat_rate"] = "Invalid VAT rate"
        
        wht_applicable = data.get("wht_applicable") in [True, "true", "on", "1"]
        profile.wht_applicable = wht_applicable
        
        if wht_applicable:
            try:
                wht_rate = Decimal(str(data.get("wht_rate", "0")))
                if wht_rate < 0 or wht_rate > 100:
                    errors["wht_rate"] = "WHT rate must be between 0 and 100"
                profile.wht_rate = wht_rate
            except (ValueError, TypeError):
                errors["wht_rate"] = "Invalid WHT rate"
        
        try:
            default_tax_rate = Decimal(str(data.get("default_tax_rate", "0")))
            if default_tax_rate < 0 or default_tax_rate > 100:
                errors["default_tax_rate"] = "Tax rate must be between 0 and 100"
            profile.default_tax_rate = default_tax_rate
        except (ValueError, TypeError):
            errors["default_tax_rate"] = "Invalid tax rate"
        
        if errors:
            return False, "Please fix the errors below", errors
        
        if profile.onboarding_step <= 4:
            profile.onboarding_step = 5
        
        profile.save()
        return True, "Tax settings saved", errors
    
    @classmethod
    @transaction.atomic
    def save_payments_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        accept_bank_transfers = data.get("accept_bank_transfers") in [True, "true", "on", "1"]
        accept_card_payments = data.get("accept_card_payments") in [True, "true", "on", "1"]
        accept_mobile_money = data.get("accept_mobile_money") in [True, "true", "on", "1"]
        
        if not accept_bank_transfers and not accept_card_payments and not accept_mobile_money:
            errors["payment_methods"] = "Please select at least one payment method"
        
        profile.accept_bank_transfers = accept_bank_transfers
        profile.accept_card_payments = accept_card_payments
        profile.accept_mobile_money = accept_mobile_money
        
        if accept_bank_transfers:
            bank_name = data.get("bank_name", "").strip()
            bank_account_name = data.get("bank_account_name", "").strip()
            bank_account_number = data.get("bank_account_number", "").strip()
            
            if not bank_name:
                errors["bank_name"] = "Bank name is required for bank transfers"
            if not bank_account_name:
                errors["bank_account_name"] = "Account name is required for bank transfers"
            if not bank_account_number:
                errors["bank_account_number"] = "Account number is required for bank transfers"
            
            profile.bank_name = bank_name
            profile.bank_account_name = bank_account_name
            profile.bank_account_number = bank_account_number
            profile.bank_routing_number = data.get("bank_routing_number", "").strip()
            profile.bank_swift_code = data.get("bank_swift_code", "").strip()
        
        profile.payment_instructions = data.get("payment_instructions", "").strip()
        
        if errors:
            return False, "Please fix the errors below", errors
        
        if profile.onboarding_step <= 5:
            profile.onboarding_step = 6
        
        profile.save()
        return True, "Payment settings saved", errors
    
    @classmethod
    @transaction.atomic
    def save_import_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        skip_import = data.get("skip_import") in [True, "true", "on", "1"]
        
        if not skip_import:
            profile.onboarding_data["import_preferences"] = {
                "import_customers": data.get("import_customers") in [True, "true", "on", "1"],
                "import_products": data.get("import_products") in [True, "true", "on", "1"],
                "import_invoices": data.get("import_invoices") in [True, "true", "on", "1"],
            }
        
        if profile.onboarding_step <= 6:
            profile.onboarding_step = 7
        
        profile.save()
        return True, "Import preferences saved", errors
    
    @classmethod
    @transaction.atomic
    def save_templates_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        invoice_style = data.get("invoice_style", "").strip()
        if invoice_style and invoice_style in dict(UserProfile.INVOICE_STYLE_CHOICES):
            profile.invoice_style = invoice_style
        
        invoice_prefix = data.get("invoice_prefix", "").strip()
        if invoice_prefix:
            if len(invoice_prefix) > 10:
                errors["invoice_prefix"] = "Invoice prefix must be 10 characters or less"
            else:
                profile.invoice_prefix = invoice_prefix.upper()
        
        try:
            invoice_start_number = int(data.get("invoice_start_number", 1))
            if invoice_start_number < 1:
                errors["invoice_start_number"] = "Invoice start number must be at least 1"
            else:
                profile.invoice_start_number = invoice_start_number
        except (ValueError, TypeError):
            pass
        
        if errors:
            return False, "Please fix the errors below", errors
        
        if profile.onboarding_step <= 7:
            profile.onboarding_step = 8
        
        profile.save()
        return True, "Template settings saved", errors
    
    @classmethod
    @transaction.atomic
    def save_team_step(cls, user, data: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        profile = user.profile
        errors = {}
        
        skip_invites = data.get("skip_invites") in [True, "true", "on", "1"]
        
        if not skip_invites:
            team_emails = data.get("team_emails", "").strip()
            if team_emails:
                emails = [e.strip() for e in team_emails.split(",") if e.strip()]
                valid_emails = []
                for email in emails:
                    try:
                        validate_email(email)
                        valid_emails.append(email)
                    except ValidationError:
                        errors["team_emails"] = f"Invalid email: {email}"
                        break
                
                if not errors:
                    profile.onboarding_data["pending_invites"] = valid_emails
                    profile.team_invites_sent = len(valid_emails)
        
        if errors:
            return False, "Please fix the errors below", errors
        
        profile.onboarding_completed = True
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_step = 9
        profile.save()
        
        return True, "Setup complete! Welcome to InvoiceFlow", errors
    
    @classmethod
    def complete_onboarding(cls, user) -> None:
        profile = user.profile
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.onboarding_completed_at = timezone.now()
            profile.save(update_fields=["onboarding_completed", "onboarding_completed_at"])
    
    @classmethod
    def record_first_invoice(cls, user) -> None:
        profile = user.profile
        if not profile.first_invoice_created_at:
            profile.first_invoice_created_at = timezone.now()
            profile.save(update_fields=["first_invoice_created_at"])
