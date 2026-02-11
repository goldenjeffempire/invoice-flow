def workspace_context(request):
    """Adds workspace context to all templates."""
    context = {
        'current_workspace': None,
        'user_workspaces': [],
        'notifications': [],
        'unread_notifications_count': 0,
        'dark_mode_preference': False,
    }
    
    if request.user.is_authenticated:
        # Notifications
        if hasattr(request.user, 'notifications'):
            context['notifications'] = request.user.notifications.all()[:10]
            context['unread_notifications_count'] = request.user.notifications.filter(is_read=False).count()
        
        context['dark_mode_preference'] = request.session.get('dark_mode', False)

        # Workspaces
        if hasattr(request.user, 'workspace_memberships'):
            context['user_workspaces'] = [m.workspace for m in request.user.workspace_memberships.all()]
        
        # Current Workspace
        if hasattr(request, 'workspace'):
            context['current_workspace'] = request.workspace
        else:
            workspace_id = request.session.get('current_workspace_id')
            if workspace_id:
                from .models import Workspace
                try:
                    context['current_workspace'] = Workspace.objects.get(id=workspace_id)
                except Workspace.DoesNotExist:
                    pass
            
            if not context['current_workspace'] and hasattr(request.user, 'profile'):
                context['current_workspace'] = request.user.profile.current_workspace
            
    return context
