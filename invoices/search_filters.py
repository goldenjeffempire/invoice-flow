import csv
import io
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class InvoiceExport:
    """Export utilities for invoices."""

    @staticmethod
    def export_to_csv(invoices) -> str:
        """Export invoices to CSV format string.

        Uses Invoice model fields: invoice_id, client_name, total (property),
        currency, status, invoice_date, due_date, business_name.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Invoice ID",
                "Client",
                "Amount",
                "Currency",
                "Status",
                "Invoice Date",
                "Due Date",
                "Business Name",
            ]
        )

        for invoice in invoices:
            try:
                writer.writerow(
                    [
                        invoice.invoice_id,
                        invoice.client_name,
                        str(invoice.total),
                        invoice.currency,
                        invoice.status,
                        invoice.invoice_date.strftime("%Y-%m-%d"),
                        invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "",
                        invoice.business_name or "",
                    ]
                )
            except AttributeError as e:
                logger.warning(f"Skipping invoice due to missing field: {e}")
                continue

        return output.getvalue()

    @staticmethod
    def bulk_export_pdfs(invoices) -> List[Tuple[str, bytes]]:
        """Generate bulk PDF export for invoices.

        Returns list of tuples: (invoice_id, pdf_bytes)
        Logs errors for failed PDF generation instead of silently skipping.
        """
        from invoices.services import PDFService

        results: List[Tuple[str, bytes]] = []
        for invoice in invoices:
            try:
                pdf_bytes: Optional[bytes] = PDFService.generate_pdf_bytes(invoice)
                if pdf_bytes:
                    results.append((f"Invoice_{invoice.invoice_id}", pdf_bytes))
                else:
                    logger.warning(f"PDF generation returned None for invoice {invoice.invoice_id}")
            except Exception as e:
                logger.error(f"Failed to generate PDF for invoice {invoice.invoice_id}: {e}")
                continue
        return results
