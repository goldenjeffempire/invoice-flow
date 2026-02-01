from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Estimate, Workspace
from ..services.estimate_service import EstimateService

@login_required
def estimate_list(request):
    workspace = request.user.profile.current_workspace
    estimates = Estimate.objects.filter(workspace=workspace)
    return render(request, 'pages/estimates/list.html', {'estimates': estimates})

@login_required
def estimate_builder(request, estimate_id=None):
    workspace = request.user.profile.current_workspace
    estimate = None
    if estimate_id:
        estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)
    
    if request.method == 'POST':
        # Logic to handle create/update
        pass
        
    return render(request, 'pages/estimates/builder.html', {'estimate': estimate})

def public_estimate_view(request, token):
    estimate = get_object_or_404(Estimate, public_token=token)
    return render(request, 'pages/estimates/public_view.html', {'estimate': estimate})

@login_required
def convert_estimate(request, estimate_id):
    workspace = request.user.profile.current_workspace
    estimate = get_object_or_404(Estimate, id=estimate_id, workspace=workspace)
    try:
        invoice = EstimateService.convert_to_invoice(estimate, request.user)
        messages.success(request, "Estimate converted to invoice successfully")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)
    except Exception as e:
        messages.error(request, str(e))
        return redirect('invoices:estimate_detail', estimate_id=estimate.id)
