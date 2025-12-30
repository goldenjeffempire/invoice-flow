"""
Production utilities for the invoices app.
Provides helpers for PDF generation, data validation, and reporting.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from datetime import date, timedelta

if TYPE_CHECKING:
    from invoices.models import Invoice

logger = logging.getLogger(__name__)


class PDFGenerationService:
    """Service for generating professional invoice PDFs."""

    @staticmethod
    def generate_invoice_pdf(invoice: 'Invoice') -> Optional[bytes]:
        """
        Generate PDF from invoice instance.

        Args:
            invoice: Invoice model instance

        Returns:
            bytes: PDF file content or None if generation fails
        """
        try:
            import pdfkit
            from django.template.loader import render_to_string

            html_content = render_to_string(
                'invoices/invoice_pdf.html',
                {'invoice': invoice}
            )

            # Generate PDF with wkhtmltopdf
            pdf_bytes = pdfkit.from_string(html_content, False)
            logger.info(f"PDF generated for invoice {invoice.invoice_id}")
            return pdf_bytes

        except ImportError:
            logger.warning("pdfkit not installed. Using fallback PDF generation.")
            return None
        except Exception as e:
            logger.exception(f"PDF generation failed for {invoice.invoice_id}: {str(e)}")
            return None


class FinancialAnalyticsService:
    """Service for financial analytics and reporting."""

    @staticmethod
    def calculate_invoice_metrics(invoices: List['Invoice']) -> Dict:
        """
        Calculate key financial metrics from invoices.

        Args:
            invoices: List of Invoice instances

        Returns:
            dict: Metrics including totals, averages, and statistics
        """
        if not invoices:
            return {
                'total_amount': Decimal('0.00'),
                'paid_amount': Decimal('0.00'),
                'overdue_amount': Decimal('0.00'),
                'average_invoice': Decimal('0.00'),
                'invoice_count': 0,
                'paid_count': 0,
                'overdue_count': 0,
                'days_to_payment_avg': 0,
            }

        total_amount = Decimal('0.00')
        paid_amount = Decimal('0.00')
        overdue_amount = Decimal('0.00')
        paid_count = 0
        overdue_count = 0
        days_to_payment_list = []

        today = date.today()

        for invoice in invoices:
            total_amount += invoice.total

            if invoice.is_paid:
                paid_amount += invoice.total
                paid_count += 1

                # Calculate days to payment
                if invoice.paid_date:
                    days = (invoice.paid_date - invoice.invoice_date).days
                    days_to_payment_list.append(days)

            elif invoice.is_overdue:
                overdue_amount += invoice.total
                overdue_count += 1

        average_invoice = total_amount / len(invoices) if invoices else Decimal('0.00')
        avg_days_to_payment = (
            sum(days_to_payment_list) / len(days_to_payment_list)
            if days_to_payment_list
            else 0
        )

        return {
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'overdue_amount': overdue_amount,
            'pending_amount': total_amount - paid_amount - overdue_amount,
            'average_invoice': average_invoice,
            'invoice_count': len(invoices),
            'paid_count': paid_count,
            'unpaid_count': len(invoices) - paid_count,
            'overdue_count': overdue_count,
            'days_to_payment_avg': int(avg_days_to_payment),
            'payment_rate': (paid_count / len(invoices) * 100) if invoices else 0,
        }

    @staticmethod
    def get_invoice_forecast(invoices: List['Invoice'], days_ahead: int = 30) -> Dict:
        """
        Get revenue forecast based on pending invoices.

        Args:
            invoices: List of Invoice instances
            days_ahead: Number of days to forecast

        Returns:
            dict: Forecast data including expected revenue
        """
        today = date.today()
        forecast_date = today + timedelta(days=days_ahead)

        expected_revenue = Decimal('0.00')
        invoices_due_soon = []

        for invoice in invoices:
            if not invoice.is_paid and invoice.due_date <= forecast_date:
                expected_revenue += invoice.total
                invoices_due_soon.append({
                    'invoice_id': invoice.invoice_id,
                    'amount': invoice.total,
                    'due_date': invoice.due_date,
                    'days_until_due': (invoice.due_date - today).days,
                })

        invoices_due_soon.sort(key=lambda x: x['due_date'])

        return {
            'forecast_date': forecast_date,
            'expected_revenue': expected_revenue,
            'invoices_due_soon': invoices_due_soon,
            'invoice_count': len(invoices_due_soon),
        }


class ValidationService:
    """Service for complex invoice validations."""

    @staticmethod
    def validate_line_items(line_items: List[Dict]) -> Tuple[bool, Optional[str]]:
        """
        Validate line items data structure and values.

        Args:
            line_items: List of line item dictionaries

        Returns:
            tuple: (is_valid, error_message)
        """
        if not line_items:
            return False, "At least one line item is required"

        for idx, item in enumerate(line_items, 1):
            # Check required fields
            if not item.get('description'):
                return False, f"Item {idx}: Description is required"

            # Validate quantity
            try:
                qty = Decimal(str(item.get('quantity', 0)))
                if qty <= 0:
                    return False, f"Item {idx}: Quantity must be greater than zero"
            except:
                return False, f"Item {idx}: Invalid quantity"

            # Validate unit price
            try:
                price = Decimal(str(item.get('unit_price', 0)))
                if price < 0:
                    return False, f"Item {idx}: Unit price cannot be negative"
            except:
                return False, f"Item {idx}: Invalid unit price"

        return True, None

    @staticmethod
    def validate_invoice_dates(
        invoice_date: date,
        due_date: date
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate invoice and due dates.

        Args:
            invoice_date: Invoice creation date
            due_date: Payment due date

        Returns:
            tuple: (is_valid, error_message)
        """
        today = date.today()

        if invoice_date > today + timedelta(days=365):
            return False, "Invoice date cannot be more than 1 year in the future"

        if due_date < invoice_date:
            return False, "Due date cannot be before invoice date"

        return True, None


class DataExportService:
    """Service for exporting invoice data in various formats."""

    @staticmethod
    def export_to_csv(invoices: List['Invoice']) -> str:
        """
        Export invoices to CSV format.

        Args:
            invoices: List of Invoice instances

        Returns:
            str: CSV formatted data
        """
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'Invoice ID', 'Client', 'Amount', 'Status', 'Invoice Date', 'Due Date', 'Created'
        ])

        # Data rows
        for invoice in invoices:
            writer.writerow([
                invoice.invoice_id,
                invoice.client_name,
                invoice.total,
                invoice.get_status_display(),
                invoice.invoice_date.strftime('%Y-%m-%d'),
                invoice.due_date.strftime('%Y-%m-%d'),
                invoice.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return output.getvalue()

    @staticmethod
    def export_to_json(invoices: List['Invoice']) -> str:
        """
        Export invoices to JSON format.

        Args:
            invoices: List of Invoice instances

        Returns:
            str: JSON formatted data
        """
        import json

        data = []
        for invoice in invoices:
            data.append({
                'id': invoice.id,
                'invoice_id': invoice.invoice_id,
                'client_name': invoice.client_name,
                'client_email': invoice.client_email,
                'total': float(invoice.total),
                'status': invoice.get_status_display(),
                'invoice_date': invoice.invoice_date.isoformat(),
                'due_date': invoice.due_date.isoformat(),
                'created_at': invoice.created_at.isoformat(),
            })

        return json.dumps(data, indent=2)
