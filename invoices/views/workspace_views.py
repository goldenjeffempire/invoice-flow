from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from ..models import Workspace, WorkspaceMember, WorkspaceInvitation, ActivityLog, Invoice, Payment, Client
from django.http import JsonResponse
import csv
import io

@login_required
def switch_workspace(request, workspace_slug):
    try:
        member = WorkspaceMember.objects.get(user=request.user, workspace__slug=workspace_slug)
        request.user.profile.current_workspace = member.workspace
        request.user.profile.save()
        messages.success(request, f"Switched to workspace: {member.workspace.name}")
    except WorkspaceMember.DoesNotExist:
        messages.error(request, "You do not have access to this workspace.")
    return redirect(request.META.get('HTTP_REFERER', reverse('invoices:dashboard')))

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
            
            messages.success(request, "Workspace configuration updated.")
            return redirect('invoices:workspace_settings')
                
    return render(request, 'pages/workspace/settings.html', {
        'workspace': workspace,
        'members': members,
        'invitations': invitations
    })

@login_required
def revoke_invitation(request, invite_id):
    invitation = get_object_or_404(WorkspaceInvitation, id=invite_id, inviter=request.user)
    invitation.is_revoked = True
    invitation.save()
    messages.success(request, "Invitation revoked.")
    return redirect('invoices:workspace_settings')

@login_required
def remove_member(request, member_id):
    workspace = request.user.profile.current_workspace
    member = get_object_or_404(WorkspaceMember, id=member_id, workspace=workspace)
    
    if member.user == request.user:
        messages.error(request, "You cannot remove yourself.")
    else:
        member.delete()
        messages.success(request, f"Member {member.user.email} removed.")
        
    return redirect('invoices:workspace_settings')
