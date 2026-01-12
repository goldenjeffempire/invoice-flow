from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request, "pages/home-light.html")

def login_view(request):
    # Minimal stub for clean baseline
    return render(request, "pages/home-light.html")

def signup(request):
    # Minimal stub for clean baseline
    return render(request, "pages/home-light.html")

from .models import Invoice, UserProfile
from django.db.models import Sum, Count, Q

@login_required
def dashboard(request):
    # Fetch real user invoices
    user_invoices = Invoice.objects.filter(user=request.user)
    
    # KPIs calculation
    stats = user_invoices.aggregate(
        total_count=Count('id'),
        paid_revenue=Sum('total', filter=Q(status='paid')),
        outstanding=Sum('total', filter=Q(status='unpaid')),
        overdue=Sum('total', filter=Q(status='overdue'))
    )
    
    # Format numbers for template
    formatted_stats = {
        'total_count': stats['total_count'] or 0,
        'revenue': '{:,.2f}'.format(stats['paid_revenue'] or 0),
        'outstanding': '{:,.2f}'.format(stats['outstanding'] or 0),
        'overdue': '{:,.2f}'.format(stats['overdue'] or 0),
    }

    recent_invoices = user_invoices.order_by('-created_at')[:5]
    
    return render(request, "pages/dashboard.html", {
        "stats": formatted_stats, 
        "recent_invoices": recent_invoices,
        "active": "dashboard"
    })

@login_required
def invoices_list(request):
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "pages/invoices_list.html", {"invoices": invoices, "active": "invoices"})

def logout_view(request):
    logout(request)
    return redirect("home")

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)
