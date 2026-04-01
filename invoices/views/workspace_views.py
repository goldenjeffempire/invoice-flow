import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from ..models import Workspace, WorkspaceInvitation, WorkspaceMember

logger = logging.getLogger(__name__)


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required
def switch_workspace(request, workspace_identifier):
    try:
        workspace_filter = (
            {'workspace__id': int(workspace_identifier)}
            if str(workspace_identifier).isdigit()
            else {'workspace__slug': workspace_identifier}
        )
        member = WorkspaceMember.objects.select_related('workspace').get(
            user=request.user, **workspace_filter
        )
        request.user.profile.current_workspace = member.workspace
        request.user.profile.save(update_fields=['current_workspace'])
        messages.success(request, f"Switched to workspace: {member.workspace.name}")
    except (WorkspaceMember.DoesNotExist, ValueError):
        messages.error(request, "You do not have access to this workspace.")
    return redirect(request.META.get('HTTP_REFERER', reverse('invoices:invoice_list')))


@login_required
def workspace_create(request):
    profile = request.user.profile
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'Workspace name is required.')
            return redirect('invoices:workspace_create')

        base_slug = slugify(name) or f'workspace-{request.user.pk}'
        slug = base_slug
        counter = 2
        while Workspace.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        workspace = Workspace.objects.create(
            name=name,
            slug=slug,
            owner=request.user,
            currency=request.POST.get('currency') or getattr(profile, 'default_currency', 'NGN') or 'NGN',
        )
        WorkspaceMember.objects.get_or_create(
            user=request.user, workspace=workspace, defaults={'role': 'owner'}
        )
        profile.current_workspace = workspace
        profile.save(update_fields=['current_workspace'])
        messages.success(request, 'Workspace created successfully.')
        return redirect('invoices:workspace_settings')

    return render(request, 'pages/workspace/create.html')


@login_required
def workspace_settings(request):
    workspace = request.user.profile.current_workspace
    if not workspace:
        messages.warning(request, "You need to create or join a workspace first.")
        return redirect('invoices:workspace_create')

    members = workspace.members.all().select_related('user')
    invitations = WorkspaceInvitation.objects.filter(
        inviter=request.user, accepted_at__isnull=True, is_revoked=False
    )
    profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'invite':
            email = request.POST.get('email', '').strip().lower()
            role = request.POST.get('role', 'member')
            try:
                validate_email(email)
            except ValidationError:
                if _is_ajax(request):
                    return JsonResponse({'success': False, 'message': 'Please enter a valid email address.'}, status=400)
                messages.error(request, 'Please enter a valid email address.')
                return redirect('invoices:workspace_settings')

            if WorkspaceMember.objects.filter(workspace=workspace, user__email__iexact=email).exists():
                if _is_ajax(request):
                    return JsonResponse({'success': False, 'message': 'This person is already a member.'}, status=400)
                messages.error(request, 'This person is already a member.')
                return redirect('invoices:workspace_settings')

            WorkspaceInvitation.create_invitation(request.user, email, role)
            if _is_ajax(request):
                return JsonResponse({'success': True, 'message': f'Invitation sent to {email}.'})
            messages.success(request, f"Invitation sent to {email}")
            return redirect('invoices:workspace_settings')

        elif action == 'update_general':
            name = (request.POST.get('name') or '').strip()
            currency = (request.POST.get('currency') or '').strip()
            if not name:
                if _is_ajax(request):
                    return JsonResponse({'success': False, 'message': 'Workspace name is required.'}, status=400)
                messages.error(request, 'Workspace name is required.')
                return redirect('invoices:workspace_settings')

            workspace.name = name[:100]
            if currency:
                workspace.currency = currency
            workspace.save(update_fields=['name', 'currency'])

            raw_prefix = (request.POST.get('invoice_prefix') or '').strip()[:10]
            raw_start = request.POST.get('invoice_start_number', '').strip()
            default_terms = request.POST.get('default_terms', '').strip()
            if raw_prefix:
                profile.invoice_prefix = raw_prefix
            if raw_start.isdigit():
                profile.invoice_start_number = int(raw_start)
            profile.payment_instructions = default_terms
            profile.save(update_fields=['invoice_prefix', 'invoice_start_number', 'payment_instructions'])

            if _is_ajax(request):
                return JsonResponse({'success': True, 'message': 'Workspace configuration updated.'})
            messages.success(request, 'Workspace configuration updated.')
            return redirect('invoices:workspace_settings')

    return render(request, 'pages/workspace/settings.html', {
        'workspace': workspace,
        'members': members,
        'invitations': invitations,
        'profile': profile,
        'active_tab': request.GET.get('tab', 'general'),
    })


@login_required
@require_POST
@csrf_protect
def workspace_bank_details_update(request):
    """AJAX: Save bank account details for payment on invoices."""
    profile = request.user.profile
    try:
        profile.bank_name           = request.POST.get('bank_name', '').strip()[:100]
        profile.bank_account_name   = request.POST.get('bank_account_name', '').strip()[:255]
        profile.bank_account_number = request.POST.get('bank_account_number', '').strip()[:50]
        profile.bank_swift_code     = request.POST.get('bank_swift_code', '').strip()[:20]
        profile.save(update_fields=[
            'bank_name', 'bank_account_name', 'bank_account_number', 'bank_swift_code',
        ])
        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Bank details saved successfully.'})
        messages.success(request, 'Bank details saved.')
    except Exception as exc:
        logger.error("Bank details update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Failed to save bank details.'}, status=500)
        messages.error(request, 'Failed to save bank details.')
    return redirect('invoices:workspace_settings')


@login_required
def revoke_invitation(request, invite_id):
    invitation = get_object_or_404(WorkspaceInvitation, id=invite_id, inviter=request.user)
    invitation.is_revoked = True
    invitation.save(update_fields=['is_revoked'])
    if _is_ajax(request):
        return JsonResponse({'success': True, 'message': 'Invitation revoked.'})
    messages.success(request, 'Invitation revoked.')
    return redirect('invoices:workspace_settings')


@login_required
def remove_member(request, member_id):
    workspace = request.user.profile.current_workspace
    member = get_object_or_404(WorkspaceMember, id=member_id, workspace=workspace)

    if member.user == request.user:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'You cannot remove yourself.'}, status=400)
        messages.error(request, 'You cannot remove yourself.')
    else:
        member.delete()
        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': f'Member removed.'})
        messages.success(request, f'Member {member.user.email} removed.')

    return redirect('invoices:workspace_settings')
