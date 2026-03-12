import logging
from django.db.models import Q

logger = logging.getLogger(__name__)


def workspace_context(request):
    context = {
        'workspace': None,
        'current_workspace': None,
        'user_workspaces': [],
        'notifications': [],
        'unread_notifications_count': 0,
        'dark_mode_preference': False,
        'invoices_count': 0,
        'clients_count': 0,
        'overdue_count': 0,
        'drafts_count': 0,
    }

    if not request.user.is_authenticated:
        return context

    try:
        context['dark_mode_preference'] = request.session.get('dark_mode', False)

        if hasattr(request.user, 'notifications'):
            context['notifications'] = request.user.notifications.filter(
                is_read=False
            ).order_by('-created_at')[:15]
            context['unread_notifications_count'] = request.user.notifications.filter(
                is_read=False
            ).count()

        if hasattr(request.user, 'workspace_memberships'):
            context['user_workspaces'] = [
                m.workspace for m in request.user.workspace_memberships.select_related('workspace').all()
            ]

        workspace = None
        if hasattr(request, 'workspace') and request.workspace:
            workspace = request.workspace
        else:
            workspace_id = request.session.get('current_workspace_id')
            if workspace_id:
                from .models import Workspace
                try:
                    workspace = Workspace.objects.get(id=workspace_id)
                except Workspace.DoesNotExist:
                    pass
            if not workspace and hasattr(request.user, 'profile'):
                try:
                    workspace = request.user.profile.current_workspace
                except Exception:
                    pass

        if workspace:
            context['workspace'] = workspace
            context['current_workspace'] = workspace

            try:
                from .models import Invoice, Client
                inv_qs = Invoice.objects.filter(workspace=workspace)
                context['invoices_count'] = inv_qs.count()
                context['clients_count'] = Client.objects.filter(workspace=workspace).count()
                context['overdue_count'] = inv_qs.filter(status='overdue').count()
                context['drafts_count'] = inv_qs.filter(status='draft').count()
            except Exception as e:
                logger.debug("Context processor counts error: %s", e)

    except Exception as e:
        logger.debug("Workspace context processor error: %s", e)

    return context
