def workspace_context(request):
    if not request.user.is_authenticated:
        return {}
    
    notifications = request.user.notifications.all()[:10]
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_count,
        'dark_mode_preference': request.session.get('dark_mode', False),
    }
    
    if hasattr(request, 'workspace'):
        context.update({
            'current_workspace': request.workspace,
            'workspace_member': getattr(request, 'workspace_member', None),
            'workspaces': [m.workspace for m in request.user.workspace_memberships.all()]
        })
    return context
