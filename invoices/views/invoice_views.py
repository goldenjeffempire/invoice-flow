import json
import logging
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse

from ..models import Invoice, LineItem, InvoiceActivity, InvoiceAttachment, InvoicePayment, Client
from ..services.invoice_service import InvoiceService, InvoiceValidationError, InvoiceStateError
from ..services.pdf_service import PDFService

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def invoice_list(request):
    workspace = request.user.profile.current_workspace
    if not workspace:
        messages.warning(request, "Please set up your workspace first.")
        return redirect('invoices:onboarding_router')

    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    ordering = request.GET.get('ordering', '-created_at')
    page = request.GET.get('page', 1)

    invoices = InvoiceService.search_invoices(
        workspace=workspace,
        query=search_query if search_query else None,
        status=status_filter if status_filter else None,
        ordering=ordering,
    )

    if date_from:
        try:
            from datetime import datetime
            invoices = invoices.filter(issue_date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            invoices = invoices.filter(issue_date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    paginator = Paginator(invoices, 20)
    invoices_page = paginator.get_page(page)

    stats = InvoiceService.get_invoice_stats(workspace)

    status_tabs = [
        {'key': '', 'label': 'All', 'count': stats['total_count']},
        {'key': 'draft', 'label': 'Draft', 'count': stats['draft_count']},
        {'key': 'sent', 'label': 'Sent', 'count': stats['sent_count']},
        {'key': 'viewed', 'label': 'Viewed', 'count': stats['viewed_count']},
        {'key': 'part_paid', 'label': 'Part Paid', 'count': stats['part_paid_count']},
        {'key': 'paid', 'label': 'Paid', 'count': stats['paid_count']},
        {'key': 'overdue', 'label': 'Overdue', 'count': stats['overdue_count']},
    ]

    context = {
        'invoices': invoices_page,
        'stats': stats,
        'status_tabs': status_tabs,
        'current_status': status_filter,
        'search_query': search_query,
        'ordering': ordering,
        'page_title': 'Invoices',
    }

    return render(request, "pages/invoices/list.html", context)


@login_required
def invoice_create(request):
    workspace = request.user.profile.current_workspace
    if not workspace:
        messages.warning(request, "Please set up your workspace first.")
        return redirect('invoices:onboarding_router')

    clients = Client.objects.filter(workspace=workspace).order_by('name')
    profile = request.user.profile

    if request.method == 'POST':
        try:
            data = {
                'client_id': request.POST.get('client_id'),
                'issue_date': request.POST.get('issue_date') or timezone.now().date(),
                'due_date': request.POST.get('due_date'),
                'currency': request.POST.get('currency', profile.default_currency or 'NGN'),
                'tax_mode': request.POST.get('tax_mode', 'exclusive'),
                'default_tax_rate': request.POST.get('default_tax_rate', 0),
                'discount_type': request.POST.get('discount_type', 'flat'),
                'global_discount_value': request.POST.get('global_discount_value', 0),
                'client_memo': request.POST.get('client_memo', ''),
                'internal_notes': request.POST.get('internal_notes', ''),
                'terms_conditions': request.POST.get('terms_conditions', ''),
                'payment_instructions': request.POST.get('payment_instructions', ''),
            }

            if isinstance(data['issue_date'], str):
                from datetime import datetime
                data['issue_date'] = datetime.strptime(data['issue_date'], '%Y-%m-%d').date()
            if isinstance(data['due_date'], str):
                from datetime import datetime
                data['due_date'] = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

            items_json = request.POST.get('items', '[]')
            items = json.loads(items_json)

            invoice = InvoiceService.create_invoice(workspace, request.user, data, items)
            messages.success(request, f"Invoice {invoice.invoice_number} created successfully!")

            action = request.POST.get('action', 'save')
            if action == 'save_and_send':
                return redirect('invoices:invoice_send', invoice_id=invoice.id)
            elif action == 'save_and_preview':
                return redirect('invoices:invoice_preview', invoice_id=invoice.id)
            else:
                return redirect('invoices:invoice_detail', invoice_id=invoice.id)

        except InvoiceValidationError as e:
            context = {
                'clients': clients,
                'profile': profile,
                'errors': e.errors,
                'form_data': request.POST,
                'currencies': Invoice.CURRENCY_CHOICES,
                'page_title': 'Create Invoice',
            }
            return render(request, "pages/invoices/builder.html", context)
        except Exception as e:
            logger.exception(f"Error creating invoice: {e}")
            messages.error(request, "An error occurred while creating the invoice.")

    default_due_date = timezone.now().date() + timedelta(days=30)

    context = {
        'clients': clients,
        'profile': profile,
        'currencies': Invoice.CURRENCY_CHOICES,
        'default_due_date': default_due_date.isoformat(),
        'default_issue_date': timezone.now().date().isoformat(),
        'is_edit': False,
        'page_title': 'Create Invoice',
    }

    return render(request, "pages/invoices/builder.html", context)


@login_required
def invoice_edit(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    if not invoice.can_edit:
        messages.error(request, "This invoice can no longer be edited.")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)

    clients = Client.objects.filter(workspace=workspace).order_by('name')
    profile = request.user.profile

    if request.method == 'POST':
        try:
            data = {
                'client_id': request.POST.get('client_id'),
                'issue_date': request.POST.get('issue_date'),
                'due_date': request.POST.get('due_date'),
                'currency': request.POST.get('currency', invoice.currency),
                'tax_mode': request.POST.get('tax_mode', invoice.tax_mode),
                'default_tax_rate': request.POST.get('default_tax_rate', invoice.default_tax_rate),
                'discount_type': request.POST.get('discount_type', invoice.discount_type),
                'global_discount_value': request.POST.get('global_discount_value', invoice.global_discount_value),
                'client_memo': request.POST.get('client_memo', ''),
                'internal_notes': request.POST.get('internal_notes', ''),
                'terms_conditions': request.POST.get('terms_conditions', ''),
                'payment_instructions': request.POST.get('payment_instructions', ''),
            }

            if isinstance(data['issue_date'], str):
                from datetime import datetime
                data['issue_date'] = datetime.strptime(data['issue_date'], '%Y-%m-%d').date()
            if isinstance(data['due_date'], str):
                from datetime import datetime
                data['due_date'] = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

            items_json = request.POST.get('items', '[]')
            items = json.loads(items_json)

            invoice = InvoiceService.update_invoice(invoice, request.user, data, items)
            messages.success(request, f"Invoice {invoice.invoice_number} updated successfully!")
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)

        except InvoiceValidationError as e:
            context = {
                'invoice': invoice,
                'clients': clients,
                'profile': profile,
                'errors': e.errors,
                'form_data': request.POST,
                'currencies': Invoice.CURRENCY_CHOICES,
                'is_edit': True,
                'page_title': f'Edit Invoice {invoice.invoice_number}',
            }
            return render(request, "pages/invoices/builder.html", context)
        except InvoiceStateError as e:
            messages.error(request, str(e))
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)

    items_data = []
    for item in invoice.items.all():
        items_data.append({
            'id': item.id,
            'item_type': item.item_type,
            'description': item.description,
            'long_description': item.long_description,
            'unit': item.unit,
            'quantity': str(item.quantity),
            'unit_price': str(item.unit_price),
            'tax_rate': str(item.tax_rate),
            'discount_type': item.discount_type,
            'discount_value': str(item.discount_value),
        })

    context = {
        'invoice': invoice,
        'clients': clients,
        'profile': profile,
        'currencies': Invoice.CURRENCY_CHOICES,
        'items_json': json.dumps(items_data),
        'is_edit': True,
        'page_title': f'Edit Invoice {invoice.invoice_number}',
    }

    return render(request, "pages/invoices/builder.html", context)


@login_required
def invoice_detail(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'created_by', 'workspace').prefetch_related('items', 'activities', 'payments', 'attachments'),
        id=invoice_id,
        workspace=workspace
    )

    activities = invoice.activities.all()[:20]
    payments = invoice.payments.filter(status=InvoicePayment.PaymentStatus.COMPLETED)
    attachments = invoice.attachments.all()

    context = {
        'invoice': invoice,
        'activities': activities,
        'payments': payments,
        'attachments': attachments,
        'can_edit': invoice.can_edit,
        'can_send': invoice.can_send,
        'can_void': invoice.can_void,
        'can_record_payment': invoice.can_record_payment,
        'payment_methods': InvoicePayment.PaymentMethod.choices,
        'today': timezone.now().date(),
        'page_title': f'Invoice {invoice.invoice_number}',
    }

    return render(request, "pages/invoices/detail.html", context)


@login_required
def invoice_preview(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'workspace').prefetch_related('items'),
        id=invoice_id,
        workspace=workspace
    )

    context = {
        'invoice': invoice,
        'profile': request.user.profile,
        'is_preview': True,
        'page_title': f'Preview - Invoice {invoice.invoice_number}',
    }

    return render(request, "pages/invoices/preview.html", context)


@login_required
def invoice_pdf(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    try:
        pdf_bytes = PDFService.generate_pdf_bytes(invoice)

        InvoiceService.log_activity(
            invoice, request.user, InvoiceActivity.ActionType.DOWNLOADED,
            "PDF downloaded"
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
        return response

    except Exception as e:
        logger.exception(f"Error generating PDF: {e}")
        messages.error(request, "Unable to generate PDF. Please try again.")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)


@login_required
@require_POST
def invoice_send(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    email = request.POST.get('email', invoice.client.email)
    subject = request.POST.get('subject')
    message = request.POST.get('message')

    try:
        # Mark as sent if it was draft
        if invoice.status == Invoice.Status.DRAFT:
            invoice.status = Invoice.Status.SENT
            invoice.sent_at = timezone.now()
            invoice.save()

        from ..services.email_service import EmailService
        try:
            EmailService.send_invoice(invoice, email)
            
            InvoiceService.log_activity(
                invoice, request.user, InvoiceActivity.ActionType.SENT,
                f"Invoice sent to {email}"
            )
            
            messages.success(request, f"Invoice sent to {email}")
        except Exception as e:
            logger.exception(f"Error sending email: {e}")
            messages.warning(request, "Invoice marked as sent, but email delivery failed. You can share the link manually.")

    except Exception as e:
        logger.exception(f"Error in invoice_send: {e}")
        messages.error(request, str(e))

    return redirect('invoices:invoice_detail', invoice_id=invoice.id)


@login_required
def invoice_share_link(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    public_url = request.build_absolute_uri(
        reverse('invoices:public_invoice', kwargs={'token': invoice.public_token})
    )

    InvoiceService.log_activity(
        invoice, request.user, InvoiceActivity.ActionType.SHARED,
        "Share link generated"
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'url': public_url, 'token': invoice.public_token})

    context = {
        'invoice': invoice,
        'public_url': public_url,
        'page_title': f'Share Invoice {invoice.invoice_number}',
    }

    return render(request, "pages/invoices/share.html", context)


@login_required
@require_POST
def invoice_record_payment(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    try:
        amount = Decimal(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        reference = request.POST.get('reference', '')
        payment_date_str = request.POST.get('payment_date')
        notes = request.POST.get('notes', '')

        payment_date = None
        if payment_date_str:
            from datetime import datetime
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        else:
            payment_date = timezone.now().date()

        invoice, payment = InvoiceService.record_payment(
            invoice, request.user, amount,
            payment_method=payment_method,
            reference=reference if reference else None,
            payment_date=payment_date,
            notes=notes,
        )

        messages.success(request, f"Payment of {invoice.currency_symbol}{amount} recorded successfully!")

    except (InvoiceStateError, Exception) as e:
        logger.exception(f"Error recording payment: {e}")
        messages.error(request, str(e))

    return redirect('invoices:invoice_detail', invoice_id=invoice.id)


@login_required
@require_POST
def invoice_void(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    reason = request.POST.get('reason', '')

    try:
        invoice = InvoiceService.void_invoice(invoice, request.user, reason)
        messages.success(request, f"Invoice {invoice.invoice_number} has been voided.")
    except (InvoiceStateError, Exception) as e:
        messages.error(request, str(e))

    return redirect('invoices:invoice_detail', invoice_id=invoice.id)


@login_required
@require_POST
def invoice_duplicate(request, invoice_id):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    try:
        new_invoice = InvoiceService.duplicate_invoice(invoice, request.user)
        messages.success(request, f"Invoice duplicated as {new_invoice.invoice_number}")
        return redirect('invoices:invoice_edit', invoice_id=new_invoice.id)
    except Exception as e:
        logger.exception(f"Error duplicating invoice: {e}")
        messages.error(request, "Unable to duplicate invoice. Please try again.")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)


def public_invoice_view(request, token):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'workspace').prefetch_related('items'),
        public_token=token
    )

    if invoice.status == Invoice.Status.VOID:
        raise Http404("This invoice is no longer available.")

    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    invoice = InvoiceService.record_view(invoice, ip_address=ip_address, user_agent=user_agent)

    profile = invoice.workspace.members.first().user.profile if invoice.workspace.members.exists() else None

    context = {
        'invoice': invoice,
        'profile': profile,
        'is_public': True,
        'page_title': f'Invoice {invoice.invoice_number}',
    }

    return render(request, "payments/public_invoice.html", context)


@require_POST
def public_initiate_payment(request, token):
    invoice = get_object_or_404(Invoice, public_token=token)
    email = request.POST.get('email', invoice.client.email)
    
    # In a real app, you would integrate with Paystack/Stripe here
    # For now, we'll simulate initiating a payment and redirecting to a success page
    # or to the Paystack checkout if keys are configured.
    
    from ..services.payment_service import PaymentService
    try:
        # Mocking payment initiation for now as we don't have real keys
        # In production, PaymentService would return a redirect URL
        messages.info(request, "Redirecting to secure payment gateway...")
        # For simulation, we'll just record a partial payment if it's a test environment
        # or redirect to a mock success
        return redirect('invoices:public_invoice', token=token)
    except Exception as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect('invoices:public_invoice', token=token)


def public_invoice_pdf(request, token):
    invoice = get_object_or_404(Invoice, public_token=token)

    if invoice.status == Invoice.Status.VOID:
        raise Http404("This invoice is no longer available.")

    try:
        pdf_bytes = PDFService.generate_pdf_bytes(invoice)

        InvoiceActivity.objects.create(
            invoice=invoice,
            action=InvoiceActivity.ActionType.DOWNLOADED,
            description="PDF downloaded via public link",
            ip_address=get_client_ip(request),
            is_system=True,
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.invoice_number}.pdf"'
        return response

    except Exception as e:
        logger.exception(f"Error generating PDF: {e}")
        raise Http404("Unable to generate PDF.")


@login_required
def invoice_export_csv(request):
    import csv
    from django.http import HttpResponse

    workspace = request.user.profile.current_workspace
    invoices = Invoice.objects.filter(workspace=workspace).select_related('client')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="invoices_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice Number', 'Client', 'Status', 'Issue Date', 'Due Date',
        'Currency', 'Subtotal', 'Tax', 'Discount', 'Total', 'Amount Paid', 'Amount Due',
        'Created At'
    ])

    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client.name,
            inv.get_status_display(),
            inv.issue_date.isoformat(),
            inv.due_date.isoformat(),
            inv.currency,
            inv.subtotal,
            inv.tax_total,
            inv.discount_total,
            inv.total_amount,
            inv.amount_paid,
            inv.amount_due,
            inv.created_at.isoformat(),
        ])

    return response


@login_required
@require_POST
def api_client_create(request):
    workspace = request.user.profile.current_workspace
    try:
        data = json.loads(request.body)
        name = data.get('name')
        email = data.get('email')
        
        if not name or not email:
            return JsonResponse({'success': False, 'error': 'Name and email are required.'}, status=400)
            
        client = Client.objects.create(
            workspace=workspace,
            name=name,
            email=email
        )
        
        return JsonResponse({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'email': client.email
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_invoice_calculate(request):
    try:
        items_json = request.GET.get('items', '[]')
        items = json.loads(items_json)
        tax_mode = request.GET.get('tax_mode', 'exclusive')
        discount_type = request.GET.get('discount_type', 'flat')
        global_discount_value = Decimal(request.GET.get('global_discount_value', '0'))

        totals = InvoiceService.calculate_invoice_totals(
            items, tax_mode, discount_type, global_discount_value
        )

        return JsonResponse({
            'success': True,
            'subtotal': str(totals['subtotal']),
            'tax_total': str(totals['tax_total']),
            'discount_total': str(totals['discount_total']),
            'total_amount': str(totals['total_amount']),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_clients_search(request):
    workspace = request.user.profile.current_workspace
    query = request.GET.get('q', '')

    clients = Client.objects.filter(workspace=workspace)
    if query:
        clients = clients.filter(Q(name__icontains=query) | Q(email__icontains=query))

    clients = clients[:10]

    data = [{'id': c.id, 'name': c.name, 'email': c.email} for c in clients]
    return JsonResponse({'clients': data})
