from io import BytesIO
from typing import Any, Dict, Optional, Type, cast

from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from invoices.models import Invoice, InvoiceActivity
from invoices.services import ReportsService, PDFService

from .response import APIResponse
from .serializers import (
    InvoiceCreateSerializer,
    InvoiceDetailSerializer,
    InvoiceHistorySerializer,
    InvoiceListSerializer,
    InvoiceStatusSerializer,
    InvoiceTemplateSerializer,
)

# Define common path parameters
INVOICE_ID_PARAM = OpenApiParameter(
    name="pk",
    description="Invoice ID",
    required=True,
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
)

TEMPLATE_ID_PARAM = OpenApiParameter(
    name="pk",
    description="Template ID",
    required=True,
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
)

# ------------------------------
# Invoice ViewSet
# ------------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List invoices",
        description="Retrieve a paginated list of invoices for the authenticated user.",
        parameters=[
            OpenApiParameter(name="status", description="Filter by status (paid/unpaid)", required=False, type=str),
            OpenApiParameter(name="search", description="Search by client name or invoice ID", required=False, type=str),
            OpenApiParameter(name="ordering", description="Order by field (e.g., -created_at, due_date)", required=False, type=str),
        ],
    ),
    retrieve=extend_schema(
        summary="Get invoice details",
        description="Retrieve detailed information about a specific invoice including line items.",
        parameters=[INVOICE_ID_PARAM],
    ),
    create=extend_schema(
        summary="Create invoice",
        description="Create a new invoice with line items.",
    ),
    update=extend_schema(
        summary="Update invoice",
        description="Update an existing invoice and its line items.",
        parameters=[INVOICE_ID_PARAM],
    ),
    partial_update=extend_schema(
        summary="Partial update invoice",
        description="Partially update an invoice.",
        parameters=[INVOICE_ID_PARAM],
    ),
    destroy=extend_schema(
        summary="Delete invoice",
        description="Delete an invoice.",
        parameters=[INVOICE_ID_PARAM],
    ),
)
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.none()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_id", "client_name", "client_email"]
    ordering_fields = ["created_at", "invoice_date", "due_date", "total", "status"]
    ordering = ["-created_at"]
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_serializer_class(self) -> Type[Any]:
        if self.action == "list":
            return InvoiceListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return InvoiceCreateSerializer
        elif self.action == "update_status":
            return InvoiceStatusSerializer
        return InvoiceDetailSerializer

    def get_queryset(self):
        return Invoice.objects.filter(workspace=self.request.user.profile.current_workspace).prefetch_related("items")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        ReportsService.invalidate_workspace_cache(instance.workspace_id)
        return instance

    def perform_destroy(self, instance):
        workspace_id = instance.workspace_id
        instance.delete()
        ReportsService.invalidate_workspace_cache(workspace_id)

    @extend_schema(
        summary="Update invoice status",
        description="Update the status of an invoice (draft/sent/unpaid/paid/overdue). Status transitions are enforced.",
        request=InvoiceStatusSerializer,
        responses={200: InvoiceDetailSerializer},
        parameters=[INVOICE_ID_PARAM],
    )
    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request: Request, pk: Optional[int] = None, version: Optional[str] = None) -> Response:
        invoice = self.get_object()
        serializer = InvoiceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(Dict[str, Any], serializer.validated_data)
        
        from invoices.services import InvoiceService
        success, error_message = InvoiceService.transition_status(
            invoice,
            validated_data["status"],
            user=request.user,
            force=validated_data.get("force", False),
        )
        if success:
            invoice.refresh_from_db()
            return APIResponse.success(
                data=InvoiceDetailSerializer(invoice).data,
                message="Invoice status updated.",
            )
        return APIResponse.error(message=error_message or "Invalid status transition.", status=400)

    @extend_schema(
        summary="Get available status transitions",
        description="Get list of valid status transitions for this invoice.",
        responses={200: {"type": "object", "properties": {"current_status": {"type": "string"}, "available_transitions": {"type": "array", "items": {"type": "string"}}}}},
        parameters=[INVOICE_ID_PARAM],
    )
    @action(detail=True, methods=["get"], url_path="available-transitions")
    def available_transitions(self, request: Request, pk: Optional[int] = None, version: Optional[str] = None) -> Response:
        invoice = self.get_object()
        return APIResponse.success(
            data={
                "current_status": invoice.status,
                "available_transitions": invoice.get_available_transitions(),
            },
            message="Available transitions retrieved.",
        )

    @extend_schema(
        summary="Get invoice history",
        description="Get the audit log/history for an invoice, showing all changes and status transitions.",
        responses={200: InvoiceHistorySerializer(many=True)},
        parameters=[INVOICE_ID_PARAM],
    )
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request: Request, pk: Optional[int] = None, version: Optional[str] = None) -> Response:
        invoice = self.get_object()
        history_entries = invoice.activities.all().order_by("-timestamp")
        serializer = InvoiceHistorySerializer(history_entries, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Invoice history retrieved.",
        )

    @extend_schema(
        summary="Generate PDF",
        description="Generate and download PDF for an invoice.",
        responses={200: {"type": "string", "format": "binary"}},
        parameters=[INVOICE_ID_PARAM],
    )
    @action(detail=True, methods=["get"], url_path="pdf")
    def generate_pdf(self, request: Request, pk: Optional[int] = None, version: Optional[str] = None) -> FileResponse:
        invoice = self.get_object()
        pdf_bytes = PDFService.generate_pdf_bytes(invoice)
        return FileResponse(
            BytesIO(pdf_bytes),
            as_attachment=True,
            filename=f"Invoice_{invoice.invoice_id}.pdf",
            content_type="application/pdf",
        )

    @extend_schema(
        summary="Get dashboard statistics",
        description="Get aggregated statistics for the authenticated user's invoices.",
    )
    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request: Request, version: Optional[str] = None) -> Response:
        from invoices.services.reports_service import DateRange
        workspace = request.user.profile.current_workspace
        date_range = DateRange.from_preset('this_month')
        stats = ReportsService.get_reports_home_data(workspace, date_range)
        return APIResponse.success(
            data=stats.get('kpis', {}),
            message="Dashboard statistics loaded.",
        )


# ------------------------------
# InvoiceTemplate ViewSet
# ------------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List invoice templates",
        description="Retrieve all invoice templates for the authenticated user.",
    ),
    retrieve=extend_schema(
        summary="Get template details",
        description="Retrieve a specific invoice template.",
        parameters=[TEMPLATE_ID_PARAM],
    ),
    create=extend_schema(
        summary="Create template",
        description="Create a new invoice template.",
    ),
    update=extend_schema(
        summary="Update template",
        description="Update an existing invoice template.",
        parameters=[TEMPLATE_ID_PARAM],
    ),
    partial_update=extend_schema(
        summary="Partial update template",
        description="Partially update an invoice template.",
        parameters=[TEMPLATE_ID_PARAM],
    ),
    destroy=extend_schema(
        summary="Delete template",
        description="Delete an invoice template.",
        parameters=[TEMPLATE_ID_PARAM],
    ),
)
# from .views import InvoiceViewSet, InvoiceTemplateViewSet
class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.none() # Placeholder to stop import error
    serializer_class = InvoiceDetailSerializer # Placeholder
