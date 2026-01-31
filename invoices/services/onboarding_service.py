import logging
from typing import Dict, Any, Tuple
from django.db import transaction
from ..models import UserProfile

logger = logging.getLogger(__name__)

class OnboardingService:
    @classmethod
    def get_onboarding_status(cls, user) -> Dict[str, Any]:
        profile = user.profile
        steps = [
            {"id": 1, "name": "Welcome", "completed": profile.onboarding_step > 1},
            {"id": 2, "name": "Business Profile", "completed": profile.onboarding_step > 2},
            {"id": 3, "name": "Branding", "completed": profile.onboarding_step > 3},
            {"id": 4, "name": "Tax & Compliance", "completed": profile.onboarding_step > 4},
            {"id": 5, "name": "Payments", "completed": profile.onboarding_step > 5},
            {"id": 6, "name": "Final Setup", "completed": profile.onboarding_completed},
        ]
        return {
            "current_step": profile.onboarding_step,
            "is_completed": profile.onboarding_completed,
            "steps": steps,
            "progress_percent": int((profile.onboarding_step - 1) / 6 * 100)
        }

    @classmethod
    @transaction.atomic
    def save_step(cls, user, step_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        profile = user.profile
        try:
            if step_id == 2:
                profile.company_name = data.get("company_name", profile.company_name)
                profile.business_type = data.get("business_type", profile.business_type)
                profile.business_email = data.get("business_email", profile.business_email)
                profile.business_phone = data.get("business_phone", profile.business_phone)
                profile.business_address = data.get("business_address", profile.business_address)
            elif step_id == 3:
                profile.primary_color = data.get("primary_color", profile.primary_color)
                profile.invoice_style = data.get("invoice_style", profile.invoice_style)
                if "company_logo" in data:
                    profile.company_logo = data["company_logo"]
            elif step_id == 4:
                profile.default_tax_rate = data.get("tax_rate", profile.default_tax_rate)
                profile.onboarding_data["tax_compliance"] = data
            elif step_id == 5:
                profile.default_currency = data.get("currency", profile.default_currency)
                profile.onboarding_data["payment_settings"] = data
            
            if step_id >= profile.onboarding_step:
                profile.onboarding_step = step_id + 1
            
            if step_id == 6:
                profile.onboarding_completed = True
                
            profile.save()
            return True, "Step saved successfully"
        except Exception as e:
            logger.error(f"Error saving onboarding step {step_id}: {e}")
            return False, str(e)
