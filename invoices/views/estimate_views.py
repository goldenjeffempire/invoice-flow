from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import Http404
from ..models import Estimate, Client, Invoice
from ..services.estimate_service import EstimateService


def _get_workspace(request):
    profile = getattr(request.user, 'profile', None)
    return profile.current_workspace if profile else None


def _parse_items(post):
    items = []
    count_str = post.get('item_count', '0')
    try:
        count = int(count_str)
    except (ValueError, TypeError):
        count = 0
    for i in range(count):
        desc = post.get(f'items[{i}][description]', '').strip()
        if not desc:
            continue
        try:
            qty = Decimal(post.get(f'items[{i}][quantity]', '1') or '1')
            price = Decimal(post.get(f'items[{i}][unit_price]', '0') or '0')
            tax = Decimal(post.get(f'items[{i}][tax_rate]', '0') or '0')
        except InvalidOperation:
            continue
        items.append({
            'id': post.get(f'items[{i}][id]') or None,
            'description': desc,
            'quantity': qty,
            'unit_price': price,
            'tax_rate': tax,
        })
    return items


@login_required
def estimate_list(request):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    ordering = request.GET.get('ordering', '-created_at')

    estimates = Estimate.objects.filter(workspace=workspace).select_related('client')

    if query:
        estimates = estimates.filter(
            Q(estimate_number__icontains=query) |
            Q(client__name__icontains=query) |
            Q(client__email__icontains=query)
        )

    if status_filter != 'all':
        estimates = estimates.filter(status=status_filter)

    estimates = estimates.order_by(ordering)

    all_estimates = Estimate.objects.filter(workspace=workspace)
    stats = {
        'total_count': all_estimates.count(),
        'accepted_value': all_estimates.filter(status=Estimate.Status.APPROVED).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'pending_value': all_estimates.filter(status__in=[Estimate.Status.SENT, Estimate.Status.VIEWED, Estimate.Status.DRAFT]).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }

    total_non_draft = all_estimates.exclude(status=Estimate.Status.DRAFT).count()
    accepted_count = all_estimates.filter(status=Estimate.Status.APPROVED).count()
    stats['conversion_rate'] = (accepted_count / total_non_draft * 100) if total_non_draft > 0 else 0

    status_tabs = [
        {'key': 'all', 'label': 'All', 'count': all_estimates.count()},
        {'key': 'draft', 'label': 'Draft', 'count': all_estimates.filter(status=Estimate.Status.DRAFT).count()},
        {'key': 'sent', 'label': 'Sent', 'count': all_estimates.filter(status=Estimate.Status.SENT).count()},
        {'key': 'approved', 'label': 'Accepted', 'count': all_estimates.filter(status=Estimate.Status.APPROVED).count()},
        {'key': 'declined', 'label': 'Declined', 'count': all_estimates.filter(status=Estimate.Status.DECLINED).count()},
        {'key': 'expired', 'label': 'Expired', 'count': all_estimates.filter(status=Estimate.Status.EXPIRED).count()},
    ]

    return render(request, 'pages/estimates/list.html', {
        'estimates': estimates,
        'stats': stats,
        'status_tabs': status_tabs,
        'current_status': status_filter,
        'search_query': query,
        'ordering': ordering,
    })


@login_required
def estimate_builder(request, estimate_id=None):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = None
    if estimate_id:
        estimate = get_object_or_404(
            Estimate.objects.prefetch_related('items'),
            id=estimate_id, workspace=workspace
        )
        if estimate.status not in (Estimate.Status.DRAFT,):
            messages.error(request, "Only draft estimates can be edited.")
            return redirect('invoices:estimate_detail', estimate_id=estimate.id)

    clients = Client.objects.filter(workspace=workspace).order_by('name')
    today = timezone.now().date().isoformat()
    expiry_default = (timezone.now().date() + timezone.timedelta(days=30)).isoformat()
    currencies = Invoice.CURRENCY_CHOICES

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        client_id = request.POST.get('client_id', '').strip()

        if not client_id:
            messages.error(request, "Please select a client.")
            return render(request, 'pages/estimates/builder.html', {
                'estimate': estimate, 'clients': clients,
                'today': today, 'expiry_default': expiry_default,
                'currencies': currencies,
            })

        client = get_object_or_404(Client, id=client_id, workspace=workspace)
        items = _parse_items(request.POST)

        if not items:
            messages.error(request, "Please add at least one line item.")
            return render(request, 'pages/estimates/builder.html', {
                'estimate': estimate, 'clients': clients,
                'today': today, 'expiry_default': expiry_default,
                'currencies': currencies,
            })

        expiry_date = request.POST.get('expiry_date', '').strip()
        if not expiry_date:
            expiry_date = (timezone.now().date() + timezone.timedelta(days=30)).isoformat()

        data = {
            'estimate_number': request.POST.get('estimate_number', '').strip(),
            'issue_date': request.POST.get('issue_date') or timezone.now().date(),
            'expiry_date': expiry_date,
            'currency': request.POST.get('currency', 'NGN'),
            'client_notes': request.POST.get('client_notes', ''),
            'internal_notes': request.POST.get('internal_notes', ''),
            'terms_conditions': request.POST.get('terms_conditions', ''),
            'items': items,
            'as_draft': action == 'draft',
        }

        try:
            if estimate:
                estimate = EstimateService.update_estimate(estimate, request.user, data)
                messages.success(request, "Estimate updated successfully.")
            else:
                estimate = EstimateService.create_estimate(workspace, client, request.user, data)
                messages.success(request, "Estimate created successfully.")
            return redirect('invoices:estimate_detail', estimate_id=estimate.id)
        except Exception as e:
            messages.error(request, f"Error saving estimate: {e}")

    return render(request, 'pages/estimates/builder.html', {
        'estimate': estimate,
        'clients': clients,
        'today': today,
        'expiry_default': expiry_default,
        'currencies': currencies,
    })


@login_required
def estimate_detail(request, estimate_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = get_object_or_404(
        Estimate.objects.select_related('client', 'workspace', 'converted_invoice').prefetch_related('items', 'activities__user'),
        id=estimate_id, workspace=workspace
    )
    activities = estimate.activities.all().order_by('-created_at')

    return render(request, 'pages/estimates/detail.html', {
        'estimate': estimate,
        'activities': activities,
    })


@login_required
@require_POST
def estimate_send(request, estimate_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)

    if estimate.status not in (Estimate.Status.DRAFT, Estimate.Status.SENT):
        messages.error(request, "This estimate cannot be sent in its current state.")
        return redirect('invoices:estimate_detail', estimate_id=estimate_id)

    message_text = request.POST.get('message', '').strip()

    try:
        EstimateService.send_estimate(estimate, request.user, message_text)
        messages.success(request, f"Estimate sent to {estimate.client.email}.")
    except Exception as e:
        messages.error(request, f"Failed to send estimate: {e}")

    return redirect('invoices:estimate_detail', estimate_id=estimate_id)


@login_required
@require_POST
def estimate_void(request, estimate_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)

    if estimate.status == Estimate.Status.VOID:
        messages.error(request, "Estimate is already void.")
        return redirect('invoices:estimate_detail', estimate_id=estimate_id)

    reason = request.POST.get('reason', '').strip()

    try:
        EstimateService.void_estimate(estimate, request.user, reason)
        messages.success(request, "Estimate voided successfully.")
    except Exception as e:
        messages.error(request, f"Failed to void estimate: {e}")

    return redirect('invoices:estimate_detail', estimate_id=estimate_id)


@login_required
@require_POST
def estimate_duplicate(request, estimate_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)

    try:
        new_estimate = EstimateService.duplicate_estimate(estimate, request.user)
        messages.success(request, f"Estimate duplicated as {new_estimate.estimate_number}.")
        return redirect('invoices:estimate_detail', estimate_id=new_estimate.id)
    except Exception as e:
        messages.error(request, f"Failed to duplicate estimate: {e}")
        return redirect('invoices:estimate_detail', estimate_id=estimate_id)


@login_required
def convert_estimate(request, estimate_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)
    if request.method != 'POST':
        return redirect('invoices:estimate_detail', estimate_id=estimate_id)
    try:
        invoice = EstimateService.convert_to_invoice(estimate, request.user)
        messages.success(request, "Estimate converted to invoice successfully.")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)
    except Exception as e:
        messages.error(request, str(e))
        return redirect('invoices:estimate_detail', estimate_id=estimate.id)


def public_estimate_view(request, token):
    estimate = get_object_or_404(
        Estimate.objects.select_related('client', 'workspace').prefetch_related('items'),
        public_token=token,
    )

    if estimate.status == Estimate.Status.VOID:
        raise Http404('This estimate is no longer available.')

    updates = []
    if estimate.status == Estimate.Status.SENT:
        estimate.status = Estimate.Status.VIEWED
        updates.append('status')
    if not estimate.viewed_at:
        estimate.viewed_at = timezone.now()
        updates.append('viewed_at')
    if updates:
        estimate.save(update_fields=updates)

    return render(request, 'pages/estimates/public_view.html', {'estimate': estimate})


@require_POST
def public_estimate_action(request, token, action):
    estimate = get_object_or_404(Estimate, public_token=token)

    if action == 'accept':
        estimate.status = Estimate.Status.APPROVED
        estimate.accepted_at = timezone.now()
        estimate.save(update_fields=['status', 'accepted_at'])
        messages.success(request, 'Estimate accepted successfully.')
    elif action == 'decline':
        estimate.status = Estimate.Status.DECLINED
        estimate.declined_at = timezone.now()
        estimate.save(update_fields=['status', 'declined_at'])
        messages.info(request, 'Estimate declined.')
    else:
        raise Http404('Unsupported estimate action.')

    return redirect('invoices:public_estimate', token=token)
