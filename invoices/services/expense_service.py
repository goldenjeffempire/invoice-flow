import os
import uuid
import logging
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict, Any, Tuple
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from invoices.models import (
    Expense, ExpenseCategory, Vendor, ExpenseAttachment, ExpenseAuditLog,
    Invoice, LineItem, Workspace, Client
)

logger = logging.getLogger(__name__)

ALLOWED_FILE_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'application/pdf': '.pdf',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ExpenseService:
    
    @staticmethod
    def get_expense_for_user(expense_id: int, user, workspace: Workspace) -> Optional[Expense]:
        try:
            return Expense.objects.select_related(
                'category', 'vendor', 'client', 'invoice', 'created_by', 'approved_by'
            ).prefetch_related('attachments', 'audit_logs').get(
                id=expense_id,
                workspace=workspace
            )
        except Expense.DoesNotExist:
            return None

    @staticmethod
    def get_expenses_queryset(workspace: Workspace, filters: Dict[str, Any] = None):
        queryset = Expense.objects.filter(workspace=workspace).select_related(
            'category', 'vendor', 'client', 'created_by'
        ).prefetch_related('attachments')
        
        if not filters:
            return queryset
        
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        if filters.get('category_id'):
            queryset = queryset.filter(category_id=filters['category_id'])
        if filters.get('vendor_id'):
            queryset = queryset.filter(vendor_id=filters['vendor_id'])
        if filters.get('client_id'):
            queryset = queryset.filter(client_id=filters['client_id'])
        if filters.get('is_billable') is not None:
            queryset = queryset.filter(is_billable=filters['is_billable'])
        if filters.get('is_billed') is not None:
            queryset = queryset.filter(is_billed=filters['is_billed'])
        if filters.get('date_from'):
            queryset = queryset.filter(expense_date__gte=filters['date_from'])
        if filters.get('date_to'):
            queryset = queryset.filter(expense_date__lte=filters['date_to'])
        if filters.get('min_amount'):
            queryset = queryset.filter(total_amount__gte=filters['min_amount'])
        if filters.get('max_amount'):
            queryset = queryset.filter(total_amount__lte=filters['max_amount'])
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(description__icontains=search_term) |
                Q(expense_number__icontains=search_term) |
                Q(vendor__name__icontains=search_term) |
                Q(reference_number__icontains=search_term)
            )
        if filters.get('tags'):
            for tag in filters['tags']:
                queryset = queryset.filter(tags__contains=[tag])
        
        return queryset

    @staticmethod
    @transaction.atomic
    def create_expense(
        workspace: Workspace,
        user,
        data: Dict[str, Any],
        request=None
    ) -> Expense:
        category = None
        if data.get('category_id'):
            category = ExpenseCategory.objects.filter(
                id=data['category_id'],
                workspace=workspace,
                is_active=True
            ).first()
        
        vendor = None
        if data.get('vendor_id'):
            vendor = Vendor.objects.filter(
                id=data['vendor_id'],
                workspace=workspace,
                is_active=True
            ).first()
        
        client = None
        if data.get('client_id'):
            client = Client.objects.filter(
                id=data['client_id'],
                workspace=workspace
            ).first()
        
        expense = Expense(
            workspace=workspace,
            description=data['description'],
            notes=data.get('notes', ''),
            category=category,
            vendor=vendor,
            expense_date=data['expense_date'],
            amount=Decimal(str(data['amount'])),
            tax_rate=Decimal(str(data.get('tax_rate', 0))),
            currency=data.get('currency', 'USD'),
            exchange_rate=Decimal(str(data.get('exchange_rate', 1))),
            payment_method=data.get('payment_method', 'other'),
            reference_number=data.get('reference_number', ''),
            is_billable=data.get('is_billable', False),
            markup_percent=Decimal(str(data.get('markup_percent', 0))),
            client=client,
            project_name=data.get('project_name', ''),
            tags=data.get('tags', []),
            is_recurring=data.get('is_recurring', False),
            created_by=user,
            metadata=data.get('metadata', {}),
        )
        expense.save()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.CREATED,
            description=f"Expense created: {expense.description}",
            new_values=ExpenseService._expense_to_dict(expense),
            request=request
        )
        
        logger.info(f"Created expense {expense.expense_number} for workspace {workspace.id}")
        return expense

    @staticmethod
    @transaction.atomic
    def update_expense(
        expense: Expense,
        user,
        data: Dict[str, Any],
        request=None
    ) -> Expense:
        if expense.status in [Expense.Status.BILLED, Expense.Status.REIMBURSED]:
            raise ValidationError("Cannot edit expenses that are billed or reimbursed")
        
        old_values = ExpenseService._expense_to_dict(expense)
        
        if 'description' in data:
            expense.description = data['description']
        if 'notes' in data:
            expense.notes = data['notes']
        if 'expense_date' in data:
            expense.expense_date = data['expense_date']
        if 'amount' in data:
            expense.amount = Decimal(str(data['amount']))
        if 'tax_rate' in data:
            expense.tax_rate = Decimal(str(data['tax_rate']))
        if 'currency' in data:
            expense.currency = data['currency']
        if 'exchange_rate' in data:
            expense.exchange_rate = Decimal(str(data['exchange_rate']))
        if 'payment_method' in data:
            expense.payment_method = data['payment_method']
        if 'reference_number' in data:
            expense.reference_number = data['reference_number']
        if 'is_billable' in data:
            expense.is_billable = data['is_billable']
        if 'markup_percent' in data:
            expense.markup_percent = Decimal(str(data['markup_percent']))
        if 'project_name' in data:
            expense.project_name = data['project_name']
        if 'tags' in data:
            expense.tags = data['tags']
        if 'is_recurring' in data:
            expense.is_recurring = data['is_recurring']
        
        if 'category_id' in data:
            if data['category_id']:
                expense.category = ExpenseCategory.objects.filter(
                    id=data['category_id'],
                    workspace=expense.workspace,
                    is_active=True
                ).first()
            else:
                expense.category = None
        
        if 'vendor_id' in data:
            if data['vendor_id']:
                expense.vendor = Vendor.objects.filter(
                    id=data['vendor_id'],
                    workspace=expense.workspace,
                    is_active=True
                ).first()
            else:
                expense.vendor = None
        
        if 'client_id' in data:
            if data['client_id']:
                expense.client = Client.objects.filter(
                    id=data['client_id'],
                    workspace=expense.workspace
                ).first()
            else:
                expense.client = None
        
        expense.save()
        
        new_values = ExpenseService._expense_to_dict(expense)
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.UPDATED,
            description="Expense updated",
            old_values=old_values,
            new_values=new_values,
            request=request
        )
        
        return expense

    @staticmethod
    @transaction.atomic
    def submit_expense(expense: Expense, user, request=None) -> Expense:
        if expense.status != Expense.Status.DRAFT:
            raise ValidationError("Only draft expenses can be submitted")
        
        expense.status = Expense.Status.PENDING
        expense.submitted_by = user
        expense.submitted_at = timezone.now()
        expense.save()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.SUBMITTED,
            description="Expense submitted for approval",
            new_values={'status': expense.status},
            request=request
        )
        
        return expense

    @staticmethod
    @transaction.atomic
    def approve_expense(expense: Expense, user, request=None) -> Expense:
        if expense.status != Expense.Status.PENDING:
            raise ValidationError("Only pending expenses can be approved")
        
        expense.status = Expense.Status.APPROVED
        expense.approved_by = user
        expense.approved_at = timezone.now()
        expense.save()
        
        if expense.vendor:
            expense.vendor.update_totals()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.APPROVED,
            description=f"Expense approved by {user.email}",
            new_values={'status': expense.status, 'approved_by': user.id},
            request=request
        )
        
        return expense

    @staticmethod
    @transaction.atomic
    def reject_expense(expense: Expense, user, reason: str, request=None) -> Expense:
        if expense.status != Expense.Status.PENDING:
            raise ValidationError("Only pending expenses can be rejected")
        
        expense.status = Expense.Status.REJECTED
        expense.rejected_reason = reason
        expense.save()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.REJECTED,
            description=f"Expense rejected: {reason}",
            new_values={'status': expense.status, 'rejected_reason': reason},
            request=request
        )
        
        return expense

    @staticmethod
    @transaction.atomic
    def mark_reimbursed(expense: Expense, user, reference: str = '', request=None) -> Expense:
        if expense.status != Expense.Status.APPROVED:
            raise ValidationError("Only approved expenses can be marked as reimbursed")
        
        expense.status = Expense.Status.REIMBURSED
        expense.reimbursed_at = timezone.now()
        expense.reimbursement_reference = reference
        expense.save()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.REIMBURSED,
            description=f"Expense reimbursed. Reference: {reference}",
            new_values={'status': expense.status, 'reimbursement_reference': reference},
            request=request
        )
        
        return expense

    @staticmethod
    @transaction.atomic
    def add_expenses_to_invoice(
        expenses: List[Expense],
        invoice: Invoice,
        user,
        request=None
    ) -> Invoice:
        for expense in expenses:
            if not expense.is_billable:
                raise ValidationError(f"Expense {expense.expense_number} is not marked as billable")
            if expense.is_billed:
                raise ValidationError(f"Expense {expense.expense_number} has already been billed")
            if expense.status not in [Expense.Status.APPROVED, Expense.Status.PENDING]:
                raise ValidationError(f"Expense {expense.expense_number} must be approved or pending to be billed")
            if expense.workspace_id != invoice.workspace_id:
                raise ValidationError("Expenses must belong to the same workspace as the invoice")
        
        for expense in expenses:
            description = f"Expense: {expense.description}"
            if expense.vendor:
                description += f" (Vendor: {expense.vendor.name})"
            if expense.expense_date:
                description += f" - {expense.expense_date.strftime('%Y-%m-%d')}"
            
            LineItem.objects.create(
                invoice=invoice,
                description=description,
                quantity=1,
                unit_price=expense.billable_amount,
                tax_rate=Decimal('0.00'),
                sort_order=invoice.line_items.count() + 1
            )
            
            expense.is_billed = True
            expense.invoice = invoice
            expense.billed_at = timezone.now()
            expense.status = Expense.Status.BILLED
            expense.save()
            
            ExpenseService._create_audit_log(
                expense=expense,
                user=user,
                action=ExpenseAuditLog.Action.BILLED,
                description=f"Expense added to Invoice {invoice.invoice_number}",
                new_values={'invoice_id': invoice.id, 'is_billed': True},
                related_invoice=invoice,
                request=request
            )
        
        invoice.calculate_totals()
        invoice.save()
        
        logger.info(f"Added {len(expenses)} expenses to invoice {invoice.invoice_number}")
        return invoice

    @staticmethod
    def get_unbilled_billable_expenses(workspace: Workspace, client_id: Optional[int] = None):
        queryset = Expense.objects.filter(
            workspace=workspace,
            is_billable=True,
            is_billed=False,
            status__in=[Expense.Status.APPROVED, Expense.Status.PENDING]
        ).select_related('category', 'vendor', 'client')
        
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        return queryset

    @staticmethod
    def validate_file_upload(file) -> Tuple[bool, str]:
        if file.size > MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed ({MAX_FILE_SIZE // 1024 // 1024}MB)"
        
        if file.content_type not in ALLOWED_FILE_TYPES:
            return False, f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES.keys())}"
        
        return True, ""

    @staticmethod
    @transaction.atomic
    def add_attachment(
        expense: Expense,
        file,
        user,
        file_type: str = 'receipt',
        description: str = '',
        request=None
    ) -> ExpenseAttachment:
        is_valid, error_msg = ExpenseService.validate_file_upload(file)
        if not is_valid:
            raise ValidationError(error_msg)
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'expenses', str(expense.workspace_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        ext = ALLOWED_FILE_TYPES.get(file.content_type, '.bin')
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        relative_path = os.path.join('expenses', str(expense.workspace_id), safe_filename)
        
        is_first = not expense.attachments.exists()
        
        attachment = ExpenseAttachment.objects.create(
            expense=expense,
            file_name=safe_filename,
            original_file_name=file.name,
            file_path=relative_path,
            file_type=file_type,
            mime_type=file.content_type,
            file_size=file.size,
            uploaded_by=user,
            description=description,
            is_primary=is_first
        )
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.ATTACHMENT_ADDED,
            description=f"Attachment added: {file.name}",
            new_values={'attachment_id': attachment.id, 'file_name': file.name},
            request=request
        )
        
        return attachment

    @staticmethod
    @transaction.atomic
    def remove_attachment(attachment: ExpenseAttachment, user, request=None) -> bool:
        expense = attachment.expense
        file_path = os.path.join(settings.MEDIA_ROOT, attachment.file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        file_name = attachment.original_file_name
        attachment_id = attachment.id
        attachment.delete()
        
        ExpenseService._create_audit_log(
            expense=expense,
            user=user,
            action=ExpenseAuditLog.Action.ATTACHMENT_REMOVED,
            description=f"Attachment removed: {file_name}",
            old_values={'attachment_id': attachment_id, 'file_name': file_name},
            request=request
        )
        
        return True

    @staticmethod
    def get_expense_summary(workspace: Workspace, date_from: date = None, date_to: date = None) -> Dict[str, Any]:
        queryset = Expense.objects.filter(workspace=workspace)
        
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        
        summary = queryset.aggregate(
            total_expenses=Sum('total_amount'),
            total_tax=Sum('tax_amount'),
            expense_count=Count('id'),
            approved_total=Sum('total_amount', filter=Q(status=Expense.Status.APPROVED)),
            pending_total=Sum('total_amount', filter=Q(status=Expense.Status.PENDING)),
            billable_total=Sum('billable_amount', filter=Q(is_billable=True, is_billed=False)),
            billed_total=Sum('billable_amount', filter=Q(is_billed=True)),
        )
        
        for key in summary:
            if summary[key] is None:
                summary[key] = Decimal('0.00') if 'total' in key else 0
        
        by_category = queryset.values('category__name', 'category__color').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        by_vendor = queryset.values('vendor__name').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        summary['by_category'] = list(by_category)
        summary['by_vendor'] = list(by_vendor)
        
        return summary

    @staticmethod
    def get_pl_data(workspace: Workspace, date_from: date, date_to: date) -> Dict[str, Any]:
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_from,
            expense_date__lte=date_to,
            status__in=[Expense.Status.APPROVED, Expense.Status.REIMBURSED, Expense.Status.BILLED]
        )
        
        invoices = Invoice.objects.filter(
            workspace=workspace,
            issue_date__gte=date_from,
            issue_date__lte=date_to,
            status__in=['sent', 'viewed', 'part_paid', 'paid']
        )
        
        total_revenue = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_expenses = expenses.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        gross_profit = total_revenue - total_expenses
        
        expense_by_category = expenses.values('category__name').annotate(
            total=Sum('total_amount')
        ).order_by('-total')
        
        revenue_by_month = invoices.extra(
            select={'month': "TO_CHAR(issue_date, 'YYYY-MM')"}
        ).values('month').annotate(
            total=Sum('total')
        ).order_by('month')
        
        expense_by_month = expenses.extra(
            select={'month': "TO_CHAR(expense_date, 'YYYY-MM')"}
        ).values('month').annotate(
            total=Sum('total_amount')
        ).order_by('month')
        
        return {
            'period': {'from': date_from, 'to': date_to},
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'gross_profit': gross_profit,
            'profit_margin': (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00'),
            'expense_by_category': list(expense_by_category),
            'revenue_by_month': list(revenue_by_month),
            'expense_by_month': list(expense_by_month),
        }

    @staticmethod
    def _expense_to_dict(expense: Expense) -> Dict[str, Any]:
        return {
            'description': expense.description,
            'amount': str(expense.amount),
            'tax_rate': str(expense.tax_rate),
            'total_amount': str(expense.total_amount),
            'currency': expense.currency,
            'status': expense.status,
            'category_id': expense.category_id,
            'vendor_id': expense.vendor_id,
            'client_id': expense.client_id,
            'is_billable': expense.is_billable,
            'is_billed': expense.is_billed,
            'expense_date': str(expense.expense_date) if expense.expense_date else None,
        }

    @staticmethod
    def _create_audit_log(
        expense: Expense,
        user,
        action: str,
        description: str = '',
        old_values: Dict = None,
        new_values: Dict = None,
        related_invoice: Invoice = None,
        request=None
    ):
        ExpenseAuditLog.objects.create(
            expense=expense,
            user=user,
            action=action,
            description=description,
            old_values=old_values or {},
            new_values=new_values or {},
            related_invoice=related_invoice,
            ip_address=ExpenseService._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        )

    @staticmethod
    def _get_client_ip(request):
        if not request:
            return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class ExpenseCategoryService:
    
    @staticmethod
    def get_categories(workspace: Workspace, include_inactive: bool = False):
        queryset = ExpenseCategory.objects.filter(workspace=workspace)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('parent')

    @staticmethod
    @transaction.atomic
    def create_category(workspace: Workspace, data: Dict[str, Any]) -> ExpenseCategory:
        parent = None
        if data.get('parent_id'):
            parent = ExpenseCategory.objects.filter(
                id=data['parent_id'],
                workspace=workspace
            ).first()
        
        category = ExpenseCategory.objects.create(
            workspace=workspace,
            name=data['name'],
            description=data.get('description', ''),
            color=data.get('color', '#6366f1'),
            icon=data.get('icon', ''),
            is_active=data.get('is_active', True),
            is_tax_deductible=data.get('is_tax_deductible', False),
            gl_account_code=data.get('gl_account_code', ''),
            parent=parent,
            sort_order=data.get('sort_order', 0),
        )
        return category

    @staticmethod
    @transaction.atomic
    def update_category(category: ExpenseCategory, data: Dict[str, Any]) -> ExpenseCategory:
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'color' in data:
            category.color = data['color']
        if 'icon' in data:
            category.icon = data['icon']
        if 'is_active' in data:
            category.is_active = data['is_active']
        if 'is_tax_deductible' in data:
            category.is_tax_deductible = data['is_tax_deductible']
        if 'gl_account_code' in data:
            category.gl_account_code = data['gl_account_code']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        
        if 'parent_id' in data:
            if data['parent_id']:
                category.parent = ExpenseCategory.objects.filter(
                    id=data['parent_id'],
                    workspace=category.workspace
                ).first()
            else:
                category.parent = None
        
        category.save()
        return category

    @staticmethod
    def create_default_categories(workspace: Workspace):
        defaults = [
            {'name': 'Travel', 'color': '#3b82f6', 'icon': 'plane', 'is_tax_deductible': True},
            {'name': 'Meals & Entertainment', 'color': '#ef4444', 'icon': 'utensils', 'is_tax_deductible': True},
            {'name': 'Office Supplies', 'color': '#10b981', 'icon': 'paperclip', 'is_tax_deductible': True},
            {'name': 'Software & Subscriptions', 'color': '#8b5cf6', 'icon': 'laptop', 'is_tax_deductible': True},
            {'name': 'Professional Services', 'color': '#f59e0b', 'icon': 'briefcase', 'is_tax_deductible': True},
            {'name': 'Marketing & Advertising', 'color': '#ec4899', 'icon': 'megaphone', 'is_tax_deductible': True},
            {'name': 'Equipment', 'color': '#6366f1', 'icon': 'tools', 'is_tax_deductible': True},
            {'name': 'Utilities', 'color': '#14b8a6', 'icon': 'bolt', 'is_tax_deductible': True},
            {'name': 'Insurance', 'color': '#64748b', 'icon': 'shield', 'is_tax_deductible': True},
            {'name': 'Other', 'color': '#9ca3af', 'icon': 'ellipsis', 'is_tax_deductible': False},
        ]
        
        for i, cat_data in enumerate(defaults):
            ExpenseCategory.objects.get_or_create(
                workspace=workspace,
                name=cat_data['name'],
                defaults={
                    'color': cat_data['color'],
                    'icon': cat_data['icon'],
                    'is_tax_deductible': cat_data['is_tax_deductible'],
                    'sort_order': i,
                }
            )


class VendorService:
    
    @staticmethod
    def get_vendors(workspace: Workspace, include_inactive: bool = False):
        queryset = Vendor.objects.filter(workspace=workspace)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('default_category')

    @staticmethod
    def get_vendor(vendor_id: int, workspace: Workspace) -> Optional[Vendor]:
        try:
            return Vendor.objects.select_related('default_category').get(
                id=vendor_id,
                workspace=workspace
            )
        except Vendor.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_vendor(workspace: Workspace, data: Dict[str, Any]) -> Vendor:
        default_category = None
        if data.get('default_category_id'):
            default_category = ExpenseCategory.objects.filter(
                id=data['default_category_id'],
                workspace=workspace
            ).first()
        
        vendor = Vendor.objects.create(
            workspace=workspace,
            name=data['name'],
            contact_name=data.get('contact_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            website=data.get('website', ''),
            address_line1=data.get('address_line1', ''),
            address_line2=data.get('address_line2', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            postal_code=data.get('postal_code', ''),
            country=data.get('country', ''),
            tax_id=data.get('tax_id', ''),
            payment_terms=data.get('payment_terms', ''),
            default_category=default_category,
            notes=data.get('notes', ''),
            is_active=data.get('is_active', True),
        )
        return vendor

    @staticmethod
    @transaction.atomic
    def update_vendor(vendor: Vendor, data: Dict[str, Any]) -> Vendor:
        for field in ['name', 'contact_name', 'email', 'phone', 'website',
                      'address_line1', 'address_line2', 'city', 'state',
                      'postal_code', 'country', 'tax_id', 'payment_terms',
                      'notes', 'is_active']:
            if field in data:
                setattr(vendor, field, data[field])
        
        if 'default_category_id' in data:
            if data['default_category_id']:
                vendor.default_category = ExpenseCategory.objects.filter(
                    id=data['default_category_id'],
                    workspace=vendor.workspace
                ).first()
            else:
                vendor.default_category = None
        
        vendor.save()
        return vendor
