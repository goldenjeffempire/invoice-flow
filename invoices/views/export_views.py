from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from ..models import Client, Transaction
import csv

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
