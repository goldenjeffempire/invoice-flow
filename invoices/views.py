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
def invoice_create(request):
    if request.method == "POST":
        # Basic form handling
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    user=request.user,
                    client_name=request.POST.get('client_name'),
                    client_email=request.POST.get('client_email'),
                    due_date=request.POST.get('due_date'),
                    currency=request.POST.get('currency'),
                    tax_rate=Decimal(request.POST.get('tax_rate', '0')),
                    business_name=request.user.profile.company_name or request.user.get_full_name(),
                    business_email=request.user.email
                )
                
                descriptions = request.POST.getlist('item_description[]')
                quantities = request.POST.getlist('item_quantity[]')
                prices = request.POST.getlist('item_price[]')
                
                for desc, qty, price in zip(descriptions, quantities, prices):
                    LineItem.objects.create(
                        invoice=invoice,
                        description=desc,
                        quantity=Decimal(qty),
                        unit_price=Decimal(price)
                    )
                
                messages.success(request, "Invoice created successfully!")
                return redirect('invoices_list')
        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
            
    return render(request, "pages/invoice_create.html", {"active": "invoices"})

def logout_view(request):
    logout(request)
    return redirect("home")

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)
