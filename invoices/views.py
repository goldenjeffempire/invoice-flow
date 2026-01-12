from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Invoice, UserProfile, LineItem
from django.db.models import Sum, Count, Q

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

@login_required
def dashboard(request):
    user_invoices = Invoice.objects.filter(user=request.user)
    
    total_revenue = Decimal('0.00')
    total_outstanding = Decimal('0.00')
    total_overdue = Decimal('0.00')
    
    for inv in user_invoices:
        if inv.status == 'paid':
            total_revenue += inv.total
        elif inv.status == 'unpaid':
            total_outstanding += inv.total
        elif inv.status == 'overdue':
            total_overdue += inv.total

    formatted_stats = {
        'total_count': user_invoices.count(),
        'revenue': '{:,.2f}'.format(total_revenue),
        'outstanding': '{:,.2f}'.format(total_outstanding),
        'overdue': '{:,.2f}'.format(total_overdue),
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
    return render(request, "pages/invoices_list.html", {
        "invoices": invoices,
        "active": "invoices"
    })

@login_required
def invoice_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                
                invoice = Invoice.objects.create(
                    user=request.user,
                    client_name=request.POST.get('client_name'),
                    client_email=request.POST.get('client_email'),
                    due_date=request.POST.get('due_date'),
                    currency=request.POST.get('currency', 'USD'),
                    tax_rate=Decimal(request.POST.get('tax_rate', '0')),
                    business_name=profile.company_name or request.user.get_full_name() or request.user.username,
                    business_email=profile.business_email or request.user.email
                )
                
                descriptions = request.POST.getlist('item_description[]')
                quantities = request.POST.getlist('item_quantity[]')
                prices = request.POST.getlist('item_price[]')
                
                for desc, qty, price in zip(descriptions, quantities, prices):
                    if desc and qty and price:
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

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        new_status = request.POST.get('status')
        if new_status in dict(Invoice.Status.choices):
            invoice.status = new_status
            invoice.save()
            messages.success(request, f"Invoice {invoice_id} status updated to {invoice.get_status_display()}.")
            return redirect('invoice_detail', invoice_id=invoice_id)
            
    return render(request, "pages/invoice_detail.html", {
        "invoice": invoice,
        "active": "invoices"
    })

def logout_view(request):
    logout(request)
    return redirect("home")

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)
