"""
Validation API Views

Exposes validation constraints to the frontend for client-side validation.
Server remains authoritative; client mirrors constraints for UX.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from invoices.validation.schemas import get_validation_constraints
from invoices.validation.errors import create_success_response


@api_view(["GET"])
@permission_classes([AllowAny])
def validation_constraints(request):
    """
    Returns validation constraints for all domain objects.
    
    Use this to mirror server-side validation rules on the client
    for immediate UX feedback before form submission.
    """
    constraints = get_validation_constraints()
    return Response(create_success_response(data=constraints))
