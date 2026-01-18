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

from invoices.models import Invoice, InvoiceTemplate
from invoices.services import AnalyticsService, PDFService

from .response import APIResponse
from .serializers import (
    InvoiceCreateSerializer,
    InvoiceDetailSerializer,
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
        queryset = Invoice.objects.filter(user=self.request.user).prefetch_related("line_items")
        status_filter = self.request.query_params.get("status")
        if status_filter in ["paid", "unpaid"]:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        AnalyticsService.invalidate_user_cache(self.request.user.id)
        return instance

    def perform_destroy(self, instance):
        user_id = self.request.user.id
        instance.delete()
        AnalyticsService.invalidate_user_cache(user_id)

    @extend_schema(
        summary="Update invoice status",
        description="Update the payment status of an invoice (paid/unpaid).",
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
        invoice.status = validated_data["status"]
        invoice.save()
        AnalyticsService.invalidate_user_cache(request.user.id)
        return APIResponse.success(
            data=InvoiceDetailSerializer(invoice).data,
            message="Invoice status updated.",
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
        stats = AnalyticsService.get_user_dashboard_stats(request.user)
        return APIResponse.success(
            data=stats,
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
class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    queryset = InvoiceTemplate.objects.all()
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return InvoiceTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
