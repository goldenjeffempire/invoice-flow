import csv
import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET

from invoices.models import (
    Expense, ExpenseCategory, Vendor, ExpenseAttachment, ExpenseAuditLog,
    Invoice, Client, Workspace
)
from invoices.services.expense_service import (
    ExpenseService, ExpenseCategoryService, VendorService
)

logger = logging.getLogger(__name__)


def get_user_workspace(user):
    from invoices.models import WorkspaceMember
    membership = WorkspaceMember.objects.filter(user=user).select_related('workspace').first()
    return membership.workspace if membership else None


@login_required
def expense_list(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    filters = {}
    if request.GET.get('status'):
        filters['status'] = request.GET['status']
    if request.GET.get('category'):
        filters['category_id'] = request.GET['category']
    if request.GET.get('vendor'):
        filters['vendor_id'] = request.GET['vendor']
    if request.GET.get('client'):
        filters['client_id'] = request.GET['client']
    if request.GET.get('is_billable'):
        filters['is_billable'] = request.GET['is_billable'] == 'true'
    if request.GET.get('date_from'):
        try:
            filters['date_from'] = date.fromisoformat(request.GET['date_from'])
        except ValueError:
            pass
    if request.GET.get('date_to'):
        try:
            filters['date_to'] = date.fromisoformat(request.GET['date_to'])
        except ValueError:
            pass
    if request.GET.get('search'):
        filters['search'] = request.GET['search']
    
    expenses = ExpenseService.get_expenses_queryset(workspace, filters)
    
    sort_by = request.GET.get('sort', '-expense_date')
    if sort_by in ['expense_date', '-expense_date', 'total_amount', '-total_amount', 
                   'description', '-description', 'status', '-status']:
        expenses = expenses.order_by(sort_by)
    
    paginator = Paginator(expenses, 25)
    page = request.GET.get('page', 1)
    expenses_page = paginator.get_page(page)
    
    summary = ExpenseService.get_expense_summary(
        workspace,
        date_from=filters.get('date_from'),
        date_to=filters.get('date_to')
    )
    
    categories = ExpenseCategoryService.get_categories(workspace)
    vendors = VendorService.get_vendors(workspace)
    clients = Client.objects.filter(workspace=workspace)
    
    context = {
        'expenses': expenses_page,
        'summary': summary,
        'categories': categories,
        'vendors': vendors,
        'clients': clients,
        'filters': filters,
        'status_choices': Expense.Status.choices,
        'current_sort': sort_by,
    }
    return render(request, 'pages/expenses/expense_list.html', context)


@login_required
def expense_create(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    if request.method == 'POST':
        try:
            data = {
                'description': request.POST.get('description', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'expense_date': date.fromisoformat(request.POST.get('expense_date')),
                'amount': request.POST.get('amount'),
                'tax_rate': request.POST.get('tax_rate', 0),
                'currency': request.POST.get('currency', 'USD'),
                'payment_method': request.POST.get('payment_method', 'other'),
                'reference_number': request.POST.get('reference_number', '').strip(),
                'is_billable': request.POST.get('is_billable') == 'on',
                'markup_percent': request.POST.get('markup_percent', 0),
                'project_name': request.POST.get('project_name', '').strip(),
                'category_id': request.POST.get('category') or None,
                'vendor_id': request.POST.get('vendor') or None,
                'client_id': request.POST.get('client') or None,
                'tags': [t.strip() for t in request.POST.get('tags', '').split(',') if t.strip()],
            }
            
            if not data['description']:
                raise ValidationError("Description is required")
            if not data['amount']:
                raise ValidationError("Amount is required")
            
            expense = ExpenseService.create_expense(
                workspace=workspace,
                user=request.user,
                data=data,
                request=request
            )
            
            if request.FILES.get('receipt'):
                try:
                    ExpenseService.add_attachment(
                        expense=expense,
                        file=request.FILES['receipt'],
                        user=request.user,
                        file_type='receipt',
                        request=request
                    )
                except ValidationError as e:
                    messages.warning(request, f"Expense created but receipt upload failed: {str(e)}")
            
            messages.success(request, f"Expense {expense.expense_number} created successfully.")
            return redirect('invoices:expense_detail', expense_id=expense.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Invalid data provided: {str(e)}")
        except Exception as e:
            logger.exception(f"Error creating expense: {e}")
            messages.error(request, "An error occurred while creating the expense.")
    
    categories = ExpenseCategoryService.get_categories(workspace)
    vendors = VendorService.get_vendors(workspace)
    clients = Client.objects.filter(workspace=workspace)
    
    context = {
        'categories': categories,
        'vendors': vendors,
        'clients': clients,
        'payment_methods': Expense.PaymentMethod.choices,
        'currencies': Invoice.CURRENCY_CHOICES,
        'today': date.today().isoformat(),
    }
    return render(request, 'pages/expenses/expense_form.html', context)


@login_required
def expense_detail(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        raise Http404("Workspace not found")
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        raise Http404("Expense not found")
    
    audit_logs = expense.audit_logs.select_related('user', 'related_invoice').order_by('-timestamp')[:20]
    
    context = {
        'expense': expense,
        'attachments': expense.attachments.all(),
        'audit_logs': audit_logs,
        'can_edit': expense.status not in [Expense.Status.BILLED, Expense.Status.REIMBURSED],
        'can_approve': expense.status == Expense.Status.PENDING,
        'can_submit': expense.status == Expense.Status.DRAFT,
        'can_reimburse': expense.status == Expense.Status.APPROVED,
        'can_add_to_invoice': expense.is_billable and not expense.is_billed and expense.status in [Expense.Status.APPROVED, Expense.Status.PENDING],
    }
    return render(request, 'pages/expenses/expense_detail.html', context)


@login_required
def expense_edit(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        raise Http404("Workspace not found")
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        raise Http404("Expense not found")
    
    if expense.status in [Expense.Status.BILLED, Expense.Status.REIMBURSED]:
        messages.error(request, "This expense cannot be edited.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    
    if request.method == 'POST':
        try:
            data = {
                'description': request.POST.get('description', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'expense_date': date.fromisoformat(request.POST.get('expense_date')),
                'amount': request.POST.get('amount'),
                'tax_rate': request.POST.get('tax_rate', 0),
                'currency': request.POST.get('currency', 'USD'),
                'payment_method': request.POST.get('payment_method', 'other'),
                'reference_number': request.POST.get('reference_number', '').strip(),
                'is_billable': request.POST.get('is_billable') == 'on',
                'markup_percent': request.POST.get('markup_percent', 0),
                'project_name': request.POST.get('project_name', '').strip(),
                'category_id': request.POST.get('category') or None,
                'vendor_id': request.POST.get('vendor') or None,
                'client_id': request.POST.get('client') or None,
                'tags': [t.strip() for t in request.POST.get('tags', '').split(',') if t.strip()],
            }
            
            if not data['description']:
                raise ValidationError("Description is required")
            if not data['amount']:
                raise ValidationError("Amount is required")
            
            ExpenseService.update_expense(
                expense=expense,
                user=request.user,
                data=data,
                request=request
            )
            
            messages.success(request, "Expense updated successfully.")
            return redirect('invoices:expense_detail', expense_id=expense.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception(f"Error updating expense: {e}")
            messages.error(request, "An error occurred while updating the expense.")
    
    categories = ExpenseCategoryService.get_categories(workspace)
    vendors = VendorService.get_vendors(workspace)
    clients = Client.objects.filter(workspace=workspace)
    
    context = {
        'expense': expense,
        'categories': categories,
        'vendors': vendors,
        'clients': clients,
        'payment_methods': Expense.PaymentMethod.choices,
        'currencies': Invoice.CURRENCY_CHOICES,
        'editing': True,
    }
    return render(request, 'pages/expenses/expense_form.html', context)


@login_required
@require_POST
def expense_submit(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    try:
        ExpenseService.submit_expense(expense, request.user, request)
        messages.success(request, "Expense submitted for approval.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
@require_POST
def expense_approve(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    try:
        ExpenseService.approve_expense(expense, request.user, request)
        messages.success(request, "Expense approved.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
@require_POST
def expense_reject(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, "Please provide a rejection reason.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    
    try:
        ExpenseService.reject_expense(expense, request.user, reason, request)
        messages.success(request, "Expense rejected.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
@require_POST
def expense_reimburse(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    reference = request.POST.get('reference', '').strip()
    
    try:
        ExpenseService.mark_reimbursed(expense, request.user, reference, request)
        messages.success(request, "Expense marked as reimbursed.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
@require_POST
def expense_upload_receipt(request, expense_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    if not request.FILES.get('receipt'):
        messages.error(request, "No file uploaded.")
        return redirect('invoices:expense_detail', expense_id=expense.id)
    
    try:
        file_type = request.POST.get('file_type', 'receipt')
        description = request.POST.get('description', '').strip()
        
        attachment = ExpenseService.add_attachment(
            expense=expense,
            file=request.FILES['receipt'],
            user=request.user,
            file_type=file_type,
            description=description,
            request=request
        )
        messages.success(request, "Receipt uploaded successfully.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.exception(f"Error uploading receipt: {e}")
        messages.error(request, "An error occurred while uploading the receipt.")
    
    return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
@require_POST
def expense_delete_attachment(request, expense_id, attachment_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    expense = ExpenseService.get_expense_for_user(expense_id, request.user, workspace)
    if not expense:
        return JsonResponse({'error': 'Expense not found'}, status=404)
    
    try:
        attachment = ExpenseAttachment.objects.get(id=attachment_id, expense=expense)
        ExpenseService.remove_attachment(attachment, request.user, request)
        messages.success(request, "Attachment removed.")
    except ExpenseAttachment.DoesNotExist:
        messages.error(request, "Attachment not found.")
    except Exception as e:
        logger.exception(f"Error removing attachment: {e}")
        messages.error(request, "An error occurred while removing the attachment.")
    
    return redirect('invoices:expense_detail', expense_id=expense.id)


@login_required
def category_list(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            try:
                data = {
                    'name': request.POST.get('name', '').strip(),
                    'description': request.POST.get('description', '').strip(),
                    'color': request.POST.get('color', '#6366f1'),
                    'is_tax_deductible': request.POST.get('is_tax_deductible') == 'on',
                    'gl_account_code': request.POST.get('gl_account_code', '').strip(),
                }
                if not data['name']:
                    raise ValidationError("Category name is required")
                
                ExpenseCategoryService.create_category(workspace, data)
                messages.success(request, "Category created successfully.")
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.exception(f"Error creating category: {e}")
                messages.error(request, "An error occurred.")
        
        elif action == 'create_defaults':
            ExpenseCategoryService.create_default_categories(workspace)
            messages.success(request, "Default categories created.")
        
        return redirect('invoices:category_list')
    
    categories = ExpenseCategoryService.get_categories(workspace, include_inactive=True)
    
    context = {
        'categories': categories,
    }
    return render(request, 'pages/expenses/category_list.html', context)


@login_required
@require_POST
def category_edit(request, category_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return JsonResponse({'error': 'Workspace not found'}, status=404)
    
    try:
        category = ExpenseCategory.objects.get(id=category_id, workspace=workspace)
    except ExpenseCategory.DoesNotExist:
        messages.error(request, "Category not found.")
        return redirect('invoices:category_list')
    
    try:
        data = {
            'name': request.POST.get('name', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'color': request.POST.get('color', '#6366f1'),
            'is_tax_deductible': request.POST.get('is_tax_deductible') == 'on',
            'is_active': request.POST.get('is_active') == 'on',
            'gl_account_code': request.POST.get('gl_account_code', '').strip(),
        }
        
        ExpenseCategoryService.update_category(category, data)
        messages.success(request, "Category updated successfully.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.exception(f"Error updating category: {e}")
        messages.error(request, "An error occurred.")
    
    return redirect('invoices:category_list')


@login_required
def vendor_list(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    vendors = VendorService.get_vendors(workspace, include_inactive=True)
    
    search = request.GET.get('search', '').strip()
    if search:
        vendors = vendors.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(contact_name__icontains=search)
        )
    
    paginator = Paginator(vendors, 25)
    page = request.GET.get('page', 1)
    vendors_page = paginator.get_page(page)
    
    categories = ExpenseCategoryService.get_categories(workspace)
    
    context = {
        'vendors': vendors_page,
        'categories': categories,
        'search': search,
    }
    return render(request, 'pages/expenses/vendor_list.html', context)


@login_required
def vendor_create(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    if request.method == 'POST':
        try:
            data = {
                'name': request.POST.get('name', '').strip(),
                'contact_name': request.POST.get('contact_name', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'website': request.POST.get('website', '').strip(),
                'address_line1': request.POST.get('address_line1', '').strip(),
                'address_line2': request.POST.get('address_line2', '').strip(),
                'city': request.POST.get('city', '').strip(),
                'state': request.POST.get('state', '').strip(),
                'postal_code': request.POST.get('postal_code', '').strip(),
                'country': request.POST.get('country', '').strip(),
                'tax_id': request.POST.get('tax_id', '').strip(),
                'payment_terms': request.POST.get('payment_terms', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'default_category_id': request.POST.get('default_category') or None,
            }
            
            if not data['name']:
                raise ValidationError("Vendor name is required")
            
            vendor = VendorService.create_vendor(workspace, data)
            messages.success(request, f"Vendor '{vendor.name}' created successfully.")
            return redirect('invoices:vendor_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception(f"Error creating vendor: {e}")
            messages.error(request, "An error occurred while creating the vendor.")
    
    categories = ExpenseCategoryService.get_categories(workspace)
    
    context = {
        'categories': categories,
    }
    return render(request, 'pages/expenses/vendor_form.html', context)


@login_required
def vendor_edit(request, vendor_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        raise Http404("Workspace not found")
    
    vendor = VendorService.get_vendor(vendor_id, workspace)
    if not vendor:
        raise Http404("Vendor not found")
    
    if request.method == 'POST':
        try:
            data = {
                'name': request.POST.get('name', '').strip(),
                'contact_name': request.POST.get('contact_name', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'website': request.POST.get('website', '').strip(),
                'address_line1': request.POST.get('address_line1', '').strip(),
                'address_line2': request.POST.get('address_line2', '').strip(),
                'city': request.POST.get('city', '').strip(),
                'state': request.POST.get('state', '').strip(),
                'postal_code': request.POST.get('postal_code', '').strip(),
                'country': request.POST.get('country', '').strip(),
                'tax_id': request.POST.get('tax_id', '').strip(),
                'payment_terms': request.POST.get('payment_terms', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'is_active': request.POST.get('is_active') == 'on',
                'default_category_id': request.POST.get('default_category') or None,
            }
            
            if not data['name']:
                raise ValidationError("Vendor name is required")
            
            VendorService.update_vendor(vendor, data)
            messages.success(request, "Vendor updated successfully.")
            return redirect('invoices:vendor_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception(f"Error updating vendor: {e}")
            messages.error(request, "An error occurred while updating the vendor.")
    
    categories = ExpenseCategoryService.get_categories(workspace)
    
    context = {
        'vendor': vendor,
        'categories': categories,
        'editing': True,
    }
    return render(request, 'pages/expenses/vendor_form.html', context)


@login_required
def vendor_detail(request, vendor_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        raise Http404("Workspace not found")
    
    vendor = VendorService.get_vendor(vendor_id, workspace)
    if not vendor:
        raise Http404("Vendor not found")
    
    expenses = Expense.objects.filter(
        workspace=workspace,
        vendor=vendor
    ).select_related('category').order_by('-expense_date')[:20]
    
    context = {
        'vendor': vendor,
        'expenses': expenses,
    }
    return render(request, 'pages/expenses/vendor_detail.html', context)


@login_required
def expense_pl_report(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        messages.error(request, "Please complete your workspace setup first.")
        return redirect('invoices:onboarding_router')
    
    today = date.today()
    default_from = date(today.year, today.month, 1)
    default_to = today
    
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    
    try:
        date_from = date.fromisoformat(date_from_str) if date_from_str else default_from
    except ValueError:
        date_from = default_from
    
    try:
        date_to = date.fromisoformat(date_to_str) if date_to_str else default_to
    except ValueError:
        date_to = default_to
    
    pl_data = ExpenseService.get_pl_data(workspace, date_from, date_to)
    
    context = {
        'pl_data': pl_data,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'pages/expenses/pl_report.html', context)


@login_required
def expense_export_csv(request):
    workspace = get_user_workspace(request.user)
    if not workspace:
        return HttpResponse("Workspace not found", status=404)
    
    filters = {}
    if request.GET.get('status'):
        filters['status'] = request.GET['status']
    if request.GET.get('date_from'):
        try:
            filters['date_from'] = date.fromisoformat(request.GET['date_from'])
        except ValueError:
            pass
    if request.GET.get('date_to'):
        try:
            filters['date_to'] = date.fromisoformat(request.GET['date_to'])
        except ValueError:
            pass
    
    expenses = ExpenseService.get_expenses_queryset(workspace, filters)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expenses_{date.today().isoformat()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Expense Number', 'Date', 'Description', 'Category', 'Vendor',
        'Amount', 'Tax', 'Total', 'Currency', 'Payment Method',
        'Status', 'Billable', 'Billed', 'Client', 'Project',
        'Reference', 'Tags', 'Created By', 'Created At'
    ])
    
    for expense in expenses:
        writer.writerow([
            expense.expense_number,
            expense.expense_date.isoformat() if expense.expense_date else '',
            expense.description,
            expense.category.name if expense.category else '',
            expense.vendor.name if expense.vendor else '',
            str(expense.amount),
            str(expense.tax_amount),
            str(expense.total_amount),
            expense.currency,
            expense.get_payment_method_display(),
            expense.get_status_display(),
            'Yes' if expense.is_billable else 'No',
            'Yes' if expense.is_billed else 'No',
            expense.client.name if expense.client else '',
            expense.project_name,
            expense.reference_number,
            ', '.join(expense.tags) if expense.tags else '',
            expense.created_by.email if expense.created_by else '',
            expense.created_at.isoformat() if expense.created_at else '',
        ])
    
    return response


@login_required
def billable_expenses_select(request, invoice_id):
    workspace = get_user_workspace(request.user)
    if not workspace:
        raise Http404("Workspace not found")
    
    try:
        invoice = Invoice.objects.get(id=invoice_id, workspace=workspace)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")
    
    if invoice.status not in ['draft']:
        messages.error(request, "Expenses can only be added to draft invoices.")
        return redirect('invoices:invoice_detail', invoice_id=invoice.id)
    
    client_id = invoice.client_id if invoice.client else None
    unbilled_expenses = ExpenseService.get_unbilled_billable_expenses(workspace, client_id)
    
    if request.method == 'POST':
        expense_ids = request.POST.getlist('expenses')
        if not expense_ids:
            messages.warning(request, "No expenses selected.")
            return redirect('invoices:billable_expenses_select', invoice_id=invoice.id)
        
        try:
            expenses = Expense.objects.filter(
                id__in=expense_ids,
                workspace=workspace,
                is_billable=True,
                is_billed=False
            )
            
            ExpenseService.add_expenses_to_invoice(
                list(expenses),
                invoice,
                request.user,
                request
            )
            
            messages.success(request, f"Added {expenses.count()} expense(s) to invoice.")
            return redirect('invoices:invoice_edit', invoice_id=invoice.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception(f"Error adding expenses to invoice: {e}")
            messages.error(request, "An error occurred.")
    
    context = {
        'invoice': invoice,
        'unbilled_expenses': unbilled_expenses,
    }
    return render(request, 'pages/expenses/billable_expenses_select.html', context)
