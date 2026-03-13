from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from ..models import Workspace, WorkspaceInvitation, WorkspaceMember


@login_required
def switch_workspace(request, workspace_identifier):
    try:
        workspace_filter = {'workspace__id': int(workspace_identifier)} if str(workspace_identifier).isdigit() else {'workspace__slug': workspace_identifier}
        member = WorkspaceMember.objects.select_related('workspace').get(user=request.user, **workspace_filter)
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
        WorkspaceMember.objects.get_or_create(user=request.user, workspace=workspace, defaults={'role': 'owner'})
        profile.current_workspace = workspace
        profile.save(update_fields=['current_workspace'])
        messages.success(request, 'Workspace created successfully.')
        return redirect('invoices:workspace_settings')

    return render(request, 'pages/workspace/create.html')


@login_required
def workspace_settings(request):
    workspace = request.user.profile.current_workspace
    members = workspace.members.all().select_related('user')
    invitations = WorkspaceInvitation.objects.filter(inviter=request.user, accepted_at__isnull=True, is_revoked=False)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'invite':
            email = request.POST.get('email', '').lower()
            role = request.POST.get('role', 'member')
            if email:
                WorkspaceInvitation.create_invitation(request.user, email, role)
                messages.success(request, f"Invitation sent to {email}")
                return redirect('invoices:workspace_settings')
        elif action == 'update_general':
            workspace.name = request.POST.get('name')
            workspace.currency = request.POST.get('currency')
            workspace.save()

            profile = request.user.profile
            profile.invoice_prefix = request.POST.get('invoice_prefix')
            profile.invoice_start_number = request.POST.get('invoice_start_number')
            profile.terms_conditions = request.POST.get('default_terms')
            profile.save()

            messages.success(request, 'Workspace configuration updated.')
            return redirect('invoices:workspace_settings')

    return render(request, 'pages/workspace/settings.html', {
        'workspace': workspace,
        'members': members,
        'invitations': invitations,
    })


@login_required
def revoke_invitation(request, invite_id):
    invitation = get_object_or_404(WorkspaceInvitation, id=invite_id, inviter=request.user)
    invitation.is_revoked = True
    invitation.save(update_fields=['is_revoked'])
    messages.success(request, 'Invitation revoked.')
    return redirect('invoices:workspace_settings')


@login_required
def remove_member(request, member_id):
    workspace = request.user.profile.current_workspace
    member = get_object_or_404(WorkspaceMember, id=member_id, workspace=workspace)

    if member.user == request.user:
        messages.error(request, 'You cannot remove yourself.')
    else:
        member.delete()
        messages.success(request, f'Member {member.user.email} removed.')

    return redirect('invoices:workspace_settings')
