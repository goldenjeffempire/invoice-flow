from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Sum, Q
from ..models import Estimate, Client

from ..services.estimate_service import EstimateService

@login_required
def estimate_list(request):
    workspace = request.user.profile.current_workspace
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    ordering = request.GET.get('ordering', '-created_at')

    estimates = Estimate.objects.filter(workspace=workspace)

    if query:
        estimates = estimates.filter(
            Q(estimate_number__icontains=query) |
            Q(client__name__icontains=query) |
            Q(client__email__icontains=query)
        )

    if status_filter != 'all':
        estimates = estimates.filter(status=status_filter)

    estimates = estimates.order_by(ordering)

    # Stats
    all_estimates = Estimate.objects.filter(workspace=workspace)
    stats = {
        'total_count': all_estimates.count(),
        'accepted_value': all_estimates.filter(status=Estimate.Status.APPROVED).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'pending_value': all_estimates.filter(status__in=[Estimate.Status.SENT, Estimate.Status.VIEWED, Estimate.Status.DRAFT]).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }

    # Conversion Rate
    total_non_draft = all_estimates.exclude(status=Estimate.Status.DRAFT).count()
    accepted_count = all_estimates.filter(status=Estimate.Status.APPROVED).count()
    stats['conversion_rate'] = (accepted_count / total_non_draft * 100) if total_non_draft > 0 else 0

    # Status Tabs
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
    workspace = request.user.profile.current_workspace
    estimate = None
    if estimate_id:
        estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)

    clients = Client.objects.filter(workspace=workspace).order_by('name')

    return render(request, 'pages/estimates/builder.html', {
        'estimate': estimate,
        'clients': clients,
    })

@login_required
def estimate_detail(request, estimate_id):
    workspace = request.user.profile.current_workspace
    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)
    activities = estimate.activities.all().order_by('-created_at')

    return render(request, 'pages/estimates/detail.html', {
        'estimate': estimate,
        'activities': activities,
    })

@login_required
def convert_estimate(request, estimate_id):
    workspace = request.user.profile.current_workspace
    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)
    try:
        invoice = EstimateService.convert_to_invoice(estimate, request.user)
        messages.success(request, "Estimate converted to invoice successfully")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)
    except Exception as e:
        messages.error(request, str(e))
        return redirect('invoices:estimate_detail', estimate_id=estimate.id)


from django.http import Http404
from django.utils import timezone


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
