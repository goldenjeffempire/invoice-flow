from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from .models import WorkspaceMember

class WorkspaceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            request.workspace = None
            return

        # Try to get workspace from session
        workspace_id = request.session.get('current_workspace_id')
        
        if workspace_id:
            try:
                member = WorkspaceMember.objects.select_related('workspace').get(
                    user=request.user, 
                    workspace_id=workspace_id
                )
                request.workspace = member.workspace
                request.workspace_member = member
            except WorkspaceMember.DoesNotExist:
                workspace_id = None

        if not workspace_id:
            # Fallback to default or first workspace
            member = WorkspaceMember.objects.select_related('workspace').filter(user=request.user).first()
            if member:
                request.workspace = member.workspace
                request.workspace_member = member
                request.session['current_workspace_id'] = member.workspace.id
            else:
                request.workspace = None
                request.workspace_member = None

        # Gating logic: Redirect to onboarding if not completed and not on onboarding pages
        if request.workspace and not request.workspace_member.onboarding_completed:
            allowed_paths = [
                reverse('invoices:onboarding'),
                reverse('invoices:logout'),
                '/static/',
                '/media/',
            ]
            if not any(request.path.startswith(path) for path in allowed_paths):
                # Only gate core invoice creation
                if request.path.startswith(reverse('invoices:invoice_create')):
                    return redirect('invoices:onboarding_wizard')
        return None
