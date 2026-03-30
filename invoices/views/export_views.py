from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from ..models import Client, Transaction, Payment, Invoice, Estimate
import csv
import datetime

@login_required
def export_clients_csv(request):
    workspace = request.user.profile.current_workspace
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="clients_{workspace.slug}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone', 'Currency', 'Tax ID', 'Billing Address'])

    clients = Client.objects.filter(workspace=workspace)
    for client in clients:
        writer.writerow([
            client.name,
            client.email,
            client.phone,
            client.currency,
            client.tax_id,
            client.billing_address
        ])

    return response

@login_required
def export_transactions_csv(request):
    workspace = request.user.profile.current_workspace
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{workspace.slug}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Amount', 'Currency', 'Description', 'Reference'])

    transactions = Transaction.objects.filter(workspace=workspace).order_by('-created_at')
    for tx in transactions:
        writer.writerow([
            tx.created_at.strftime('%Y-%m-%d %H:%M'),
            tx.get_transaction_type_display(),
            tx.amount,
            tx.currency,
            tx.description,
            tx.provider_transaction_id
        ])

    return response


@login_required
def export_payments_csv(request):
    workspace = request.user.profile.current_workspace
    response = HttpResponse(content_type='text/csv')
    fname = f"payments_{workspace.slug}_{datetime.date.today().isoformat()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'

    writer = csv.writer(response)
    writer.writerow([
        'Payment Date', 'Invoice #', 'Client', 'Amount', 'Currency',
        'Method', 'Status', 'Fee', 'Net Amount', 'Transaction ID', 'Notes'
    ])

    payments = Payment.objects.filter(workspace=workspace).select_related('invoice', 'invoice__client').order_by('-payment_date')
    for p in payments:
        writer.writerow([
            p.payment_date.strftime('%Y-%m-%d'),
            p.invoice.invoice_number,
            p.invoice.client.name if p.invoice.client else '',
            p.amount,
            p.currency,
            p.get_payment_method_display(),
            p.get_status_display(),
            p.fee_amount,
            p.net_amount,
            p.transaction_id,
            p.notes,
        ])

    return response


@login_required
def export_estimates_csv(request):
    workspace = request.user.profile.current_workspace
    response = HttpResponse(content_type='text/csv')
    fname = f"estimates_{workspace.slug}_{datetime.date.today().isoformat()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'

    writer = csv.writer(response)
    writer.writerow([
        'Estimate #', 'Client', 'Issue Date', 'Expiry Date',
        'Subtotal', 'Tax', 'Total', 'Currency', 'Status', 'Notes'
    ])

    estimates = Estimate.objects.filter(workspace=workspace).select_related('client').order_by('-created_at')
    for est in estimates:
        writer.writerow([
            est.estimate_number,
            est.client.name if est.client else '',
            est.issue_date.strftime('%Y-%m-%d') if est.issue_date else '',
            est.expiry_date.strftime('%Y-%m-%d') if est.expiry_date else '',
            est.subtotal_amount,
            est.tax_amount,
            est.total_amount,
            est.currency,
            est.get_status_display(),
            est.notes,
        ])

    return response


@login_required
def export_invoices_csv(request):
    workspace = request.user.profile.current_workspace
    response = HttpResponse(content_type='text/csv')
    fname = f"invoices_{workspace.slug}_{datetime.date.today().isoformat()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice #', 'Client', 'Issue Date', 'Due Date',
        'Subtotal', 'Tax', 'Total', 'Amount Paid', 'Balance Due',
        'Currency', 'Status', 'Notes'
    ])

    invoices = Invoice.objects.filter(workspace=workspace).select_related('client').order_by('-issue_date')
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client.name if inv.client else '',
            inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
            inv.due_date.strftime('%Y-%m-%d') if inv.due_date else '',
            inv.subtotal_amount,
            inv.tax_amount,
            inv.total_amount,
            inv.amount_paid,
            inv.balance_due,
            inv.currency,
            inv.get_status_display(),
            inv.notes,
        ])

    return response
