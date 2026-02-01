def workspace_context(request):
    if hasattr(request, 'workspace'):
        return {
            'current_workspace': request.workspace,
            'workspace_member': getattr(request, 'workspace_member', None),
            'workspaces': [m.workspace for m in request.user.workspace_memberships.all()] if request.user.is_authenticated else []
        }
    return {}
