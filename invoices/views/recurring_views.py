from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from invoices.models import Client, RecurringSchedule, Workspace

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_workspace(user):
    membership = user.workspace_memberships.select_related('workspace').first()
    return membership.workspace if membership else None


@login_required
def schedule_list(request):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "No workspace found.")
        return redirect('invoices:dashboard')

    status_filter = request.GET.get('status', '')
    schedules = RecurringBillingService.get_schedules_for_workspace(
        workspace, status=status_filter if status_filter else None
    )

    status_counts = {
        'all': RecurringSchedule.objects.filter(workspace=workspace).count(),
        'active': RecurringSchedule.objects.filter(workspace=workspace, status='active').count(),
        'paused': RecurringSchedule.objects.filter(workspace=workspace, status='paused').count(),
        'cancelled': RecurringSchedule.objects.filter(workspace=workspace, status='cancelled').count(),
        'failed': RecurringSchedule.objects.filter(workspace=workspace, status='failed').count(),
    }

    context = {
        'schedules': schedules,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'interval_choices': RecurringSchedule.IntervalType.choices,
    }
    return render(request, 'pages/recurring/schedule_list.html', context)


@login_required
def schedule_create(request):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "No workspace found.")
        return redirect('invoices:dashboard')

    clients = Client.objects.filter(workspace=workspace).order_by('name')

    if request.method == 'POST':
        try:
            client_id = request.POST.get('client_id')
            client = get_object_or_404(Client, id=client_id, workspace=workspace)

            description = request.POST.get('description', '').strip()
            if not description:
                messages.error(request, "Description is required.")
                return redirect('invoices:schedule_create')

            interval_type = request.POST.get('interval_type', 'monthly')
            custom_interval_days = None
            if interval_type == 'custom':
                try:
                    custom_interval_days = int(request.POST.get('custom_interval_days', 30))
                except ValueError:
                    custom_interval_days = 30

            start_date_str = request.POST.get('start_date')
            try:
                start_date = date.fromisoformat(start_date_str)
            except (ValueError, TypeError):
                start_date = timezone.now().date()

            end_date_str = request.POST.get('end_date', '').strip()
            end_date = None
            if end_date_str:
                try:
                    end_date = date.fromisoformat(end_date_str)
                except ValueError:
                    pass

            try:
                base_amount = Decimal(request.POST.get('base_amount', '0'))
            except InvalidOperation:
                messages.error(request, "Invalid amount.")
                return redirect('invoices:schedule_create')

            currency = request.POST.get('currency', 'USD')

            try:
                tax_rate = Decimal(request.POST.get('tax_rate', '0'))
            except InvalidOperation:
                tax_rate = Decimal('0')

            try:
                payment_terms_days = int(request.POST.get('payment_terms_days', 30))
            except ValueError:
                payment_terms_days = 30

            proration_enabled = request.POST.get('proration_enabled') == 'on'
            auto_send = request.POST.get('auto_send') == 'on'
            retry_enabled = request.POST.get('retry_enabled') == 'on'

            anchor_day = None
            if request.POST.get('anchor_day'):
                try:
                    anchor_day = int(request.POST.get('anchor_day'))
                    if anchor_day < 1 or anchor_day > 31:
                        anchor_day = None
                except ValueError:
                    pass

            try:
                max_retry_attempts = int(request.POST.get('max_retry_attempts', 3))
            except ValueError:
                max_retry_attempts = 3

            try:
                retry_interval_hours = int(request.POST.get('retry_interval_hours', 24))
            except ValueError:
                retry_interval_hours = 24

            invoice_terms = request.POST.get('invoice_terms', '').strip()
            invoice_notes = request.POST.get('invoice_notes', '').strip()

            line_items_template = []
            item_descriptions = request.POST.getlist('item_description[]')
            item_quantities = request.POST.getlist('item_quantity[]')
            item_prices = request.POST.getlist('item_price[]')

            for i in range(len(item_descriptions)):
                if item_descriptions[i].strip():
                    try:
                        qty = Decimal(item_quantities[i]) if i < len(item_quantities) else Decimal('1')
                        price = Decimal(item_prices[i]) if i < len(item_prices) else base_amount
                        line_items_template.append({
                            'description': item_descriptions[i].strip(),
                            'quantity': str(qty),
                            'unit_price': str(price),
                        })
                    except (InvalidOperation, IndexError):
                        pass

            success, message, schedule = RecurringBillingService.create_schedule(
                workspace=workspace,
                client=client,
                user=request.user,
                description=description,
                interval_type=interval_type,
                start_date=start_date,
                base_amount=base_amount,
                currency=currency,
                end_date=end_date,
                custom_interval_days=custom_interval_days,
                proration_enabled=proration_enabled,
                anchor_day=anchor_day,
                tax_rate=tax_rate,
                line_items_template=line_items_template if line_items_template else None,
                invoice_terms=invoice_terms,
                invoice_notes=invoice_notes,
                payment_terms_days=payment_terms_days,
                auto_send=auto_send,
                retry_enabled=retry_enabled,
                max_retry_attempts=max_retry_attempts,
                retry_interval_hours=retry_interval_hours,
                ip_address=get_client_ip(request),
            )

            if success:
                messages.success(request, message)
                return redirect('invoices:schedule_detail', schedule_id=schedule.id)
            else:
                messages.error(request, message)

        except Exception as e:
            logger.exception("Error creating schedule")
            messages.error(request, f"Error creating schedule: {str(e)}")

    context = {
        'clients': clients,
        'interval_choices': RecurringSchedule.IntervalType.choices,
        'currency_choices': [
            ('USD', '$ - US Dollar'),
            ('EUR', '€ - Euro'),
            ('GBP', '£ - British Pound'),
            ('NGN', '₦ - Nigerian Naira'),
        ],
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'pages/recurring/schedule_create.html', context)


@login_required
def schedule_detail(request, schedule_id):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "No workspace found.")
        return redirect('invoices:dashboard')

    schedule = RecurringBillingService.get_schedule_by_id(schedule_id, workspace)
    if not schedule:
        messages.error(request, "Schedule not found.")
        return redirect('invoices:schedule_list')

    executions = RecurringBillingService.get_schedule_executions(schedule, limit=20)
    audit_logs = RecurringBillingService.get_schedule_audit_logs(schedule, limit=30)
    retry_plan = RecurringBillingService.get_retry_plan(schedule)

    context = {
        'schedule': schedule,
        'executions': executions,
        'audit_logs': audit_logs,
        'retry_plan': retry_plan,
    }
    return render(request, 'pages/recurring/schedule_detail.html', context)


@login_required
def schedule_edit(request, schedule_id):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "No workspace found.")
        return redirect('invoices:dashboard')

    schedule = RecurringBillingService.get_schedule_by_id(schedule_id, workspace)
    if not schedule:
        messages.error(request, "Schedule not found.")
        return redirect('invoices:schedule_list')

    clients = Client.objects.filter(workspace=workspace).order_by('name')

    if request.method == 'POST':
        try:
            data = {}

            description = request.POST.get('description', '').strip()
            if description:
                data['description'] = description

            interval_type = request.POST.get('interval_type')
            if interval_type:
                data['interval_type'] = interval_type

            if interval_type == 'custom':
                try:
                    data['custom_interval_days'] = int(request.POST.get('custom_interval_days', 30))
                except ValueError:
                    pass

            end_date_str = request.POST.get('end_date', '').strip()
            if end_date_str:
                try:
                    data['end_date'] = date.fromisoformat(end_date_str)
                except ValueError:
                    pass
            elif 'end_date' in request.POST:
                data['end_date'] = None

            if request.POST.get('base_amount'):
                try:
                    data['base_amount'] = Decimal(request.POST.get('base_amount'))
                except InvalidOperation:
                    pass

            if request.POST.get('tax_rate'):
                try:
                    data['tax_rate'] = Decimal(request.POST.get('tax_rate'))
                except InvalidOperation:
                    pass

            if request.POST.get('payment_terms_days'):
                try:
                    data['payment_terms_days'] = int(request.POST.get('payment_terms_days'))
                except ValueError:
                    pass

            data['proration_enabled'] = request.POST.get('proration_enabled') == 'on'
            data['auto_send'] = request.POST.get('auto_send') == 'on'
            data['retry_enabled'] = request.POST.get('retry_enabled') == 'on'

            if request.POST.get('anchor_day'):
                try:
                    anchor = int(request.POST.get('anchor_day'))
                    if 1 <= anchor <= 31:
                        data['anchor_day'] = anchor
                except ValueError:
                    pass

            if request.POST.get('max_retry_attempts'):
                try:
                    data['max_retry_attempts'] = int(request.POST.get('max_retry_attempts'))
                except ValueError:
                    pass

            if request.POST.get('retry_interval_hours'):
                try:
                    data['retry_interval_hours'] = int(request.POST.get('retry_interval_hours'))
                except ValueError:
                    pass

            data['invoice_terms'] = request.POST.get('invoice_terms', '').strip()
            data['invoice_notes'] = request.POST.get('invoice_notes', '').strip()

            success, message = RecurringBillingService.update_schedule(
                schedule=schedule,
                user=request.user,
                data=data,
                ip_address=get_client_ip(request),
            )

            if success:
                messages.success(request, message)
                return redirect('invoices:schedule_detail', schedule_id=schedule.id)
            else:
                messages.error(request, message)

        except Exception as e:
            logger.exception("Error updating schedule")
            messages.error(request, f"Error updating schedule: {str(e)}")

    context = {
        'schedule': schedule,
        'clients': clients,
        'interval_choices': RecurringSchedule.IntervalType.choices,
        'currency_choices': [
            ('USD', '$ - US Dollar'),
            ('EUR', '€ - Euro'),
            ('GBP', '£ - British Pound'),
            ('NGN', '₦ - Nigerian Naira'),
        ],
    }
    return render(request, 'pages/recurring/schedule_edit.html', context)


@login_required
@require_POST
def schedule_pause(request, schedule_id):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'success': False, 'message': 'No workspace found.'}, status=400)

    schedule = RecurringBillingService.get_schedule_by_id(schedule_id, workspace)
    if not schedule:
        return JsonResponse({'success': False, 'message': 'Schedule not found.'}, status=404)

    success, message = RecurringBillingService.pause_schedule(
        schedule=schedule,
        user=request.user,
        ip_address=get_client_ip(request),
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('invoices:schedule_detail', schedule_id=schedule_id)


@login_required
@require_POST
def schedule_resume(request, schedule_id):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'success': False, 'message': 'No workspace found.'}, status=400)

    schedule = RecurringBillingService.get_schedule_by_id(schedule_id, workspace)
    if not schedule:
        return JsonResponse({'success': False, 'message': 'Schedule not found.'}, status=404)

    success, message = RecurringBillingService.resume_schedule(
        schedule=schedule,
        user=request.user,
        ip_address=get_client_ip(request),
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('invoices:schedule_detail', schedule_id=schedule_id)


@login_required
@require_POST
def schedule_cancel(request, schedule_id):
    from invoices.services.recurring_service import RecurringBillingService

    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'success': False, 'message': 'No workspace found.'}, status=400)

    schedule = RecurringBillingService.get_schedule_by_id(schedule_id, workspace)
    if not schedule:
        return JsonResponse({'success': False, 'message': 'Schedule not found.'}, status=404)

    reason = request.POST.get('reason', '').strip()

    success, message = RecurringBillingService.cancel_schedule(
        schedule=schedule,
        user=request.user,
        reason=reason,
        ip_address=get_client_ip(request),
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('invoices:schedule_detail', schedule_id=schedule_id)
