"""
PDF Service - Business logic for PDF generation.

Responsibilities:
- Invoice PDF generation
- PDF rendering pipeline
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.template.loader import render_to_string

if TYPE_CHECKING:
    from invoices.models import Invoice

logger = logging.getLogger(__name__)


class PDFService:
    """Handles PDF generation with a unified rendering pipeline."""

    @staticmethod
    def is_available() -> bool:
        """Check if PDF generation is available."""
        try:
            from weasyprint import HTML
            return True
        except (ImportError, OSError, Exception):
            return False

    @staticmethod
    def generate_pdf_bytes(invoice: "Invoice") -> bytes:
        """
        Generate PDF bytes for invoice using a standardized template.
        
        Args:
            invoice: The invoice to generate PDF for
            
        Returns:
            PDF file content as bytes
            
        Raises:
            ValueError: If PDF generation is unavailable or fails
        """
        try:
            from weasyprint import HTML
            from weasyprint.text.fonts import FontConfiguration
        except (ImportError, OSError, Exception):
            raise ValueError(
                "PDF generation is currently unavailable due to missing system dependencies."
            )

        context = {
            "invoice": invoice,
            "base_url": getattr(settings, "SITE_URL", ""),
            "branding_color": "#4f46e5",
        }

        html_string = render_to_string("invoices/invoice_pdf.html", context)
        font_config = FontConfiguration()
        html = HTML(
            string=html_string,
            base_url=getattr(settings, "SITE_URL", ""),
        )

        try:
            pdf_bytes = html.write_pdf(font_config=font_config)
            logger.info(f"Generated PDF for invoice {invoice.invoice_id}")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed for invoice {invoice.invoice_id}: {e}")
            raise ValueError("PDF generation failed. Please contact support.")

    @staticmethod
    def get_invoice_filename(invoice: "Invoice") -> str:
        """
        Generate a filename for the invoice PDF.
        
        Args:
            invoice: The invoice
            
        Returns:
            Filename string
        """
        return f"Invoice-{invoice.invoice_id}.pdf"
