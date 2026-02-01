from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from ..models import Workspace, WorkspaceMember, ImportJob
from django.http import JsonResponse
import csv
import io

@login_required
def switch_workspace(request, workspace_slug):
    try:
        member = WorkspaceMember.objects.get(user=request.user, workspace__slug=workspace_slug)
        request.session['current_workspace_id'] = member.workspace.id
        messages.success(request, f"Switched to workspace: {member.workspace.name}")
    except WorkspaceMember.DoesNotExist:
        messages.error(request, "You do not have access to this workspace.")
    return redirect(request.META.get('HTTP_REFERER', reverse('invoices:dashboard')))

@login_required
def onboarding_step(request):
    member = request.workspace_member
    if not member:
        return redirect('invoices:dashboard')
    
    if request.method == 'POST':
        step = int(request.POST.get('step', 1))
        data = request.POST.dict()
        member.onboarding_data.update(data)
        member.onboarding_step = step + 1
        if step >= 5: # Assuming 5 steps
            member.onboarding_completed = True
        member.save()
        return JsonResponse({'status': 'success', 'next_step': member.onboarding_step})
    
    return render(request, 'invoices/onboarding/wizard.html', {'member': member})

@login_required
def import_csv(request):
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file']
        resource_type = request.POST.get('resource_type', 'customers')
        
        job = ImportJob.objects.create(
            workspace=request.workspace,
            user=request.user,
            resource_type=resource_type,
            file=csv_file
        )
        
        # Simple validation & background processing mock
        job.status = 'processing'
        job.save()
        
        # In a real app, this would be a Celery task
        return JsonResponse({'status': 'success', 'job_id': job.id})
    
    return render(request, 'invoices/import/upload.html')
