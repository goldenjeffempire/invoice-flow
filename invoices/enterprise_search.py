"""Advanced search and filtering for enterprise queries."""

from typing import List, Dict, Any, Optional
from django.db.models import Q, QuerySet
from decimal import Decimal


class AdvancedSearch:
    """Advanced search capabilities for invoices and payments."""
    
    @staticmethod
    def search_invoices(queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Apply advanced filters to invoice queryset."""
        
        # Text search
        if filters.get('search'):
            search_term = filters['search'].strip()
            queryset = queryset.filter(
                Q(invoice_id__icontains=search_term) |
                Q(client_name__icontains=search_term) |
                Q(client_email__icontains=search_term) |
                Q(notes__icontains=search_term)
            )
        
        # Status filter
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # Date range
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        # Amount range
        if filters.get('amount_min'):
            queryset = queryset.filter(total__gte=Decimal(filters['amount_min']))
        if filters.get('amount_max'):
            queryset = queryset.filter(total__lte=Decimal(filters['amount_max']))
        
        # Currency filter
        if filters.get('currency'):
            queryset = queryset.filter(currency=filters['currency'])
        
        # Due date filtering
        if filters.get('overdue_only'):
            from django.utils import timezone
            queryset = queryset.filter(due_date__lt=timezone.now(), status='unpaid')
        
        return queryset
    
    @staticmethod
    def search_payments(queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Apply advanced filters to payment queryset."""
        
        # Text search
        if filters.get('search'):
            search_term = filters['search'].strip()
            queryset = queryset.filter(
                Q(reference__icontains=search_term) |
                Q(invoice__invoice_id__icontains=search_term)
            )
        
        # Status filter
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # Payment method filter
        if filters.get('method'):
            queryset = queryset.filter(payment_method=filters['method'])
        
        # Date range
        if filters.get('date_from'):
            queryset = queryset.filter(payment_date__gte=filters['date_from'])
        if filters.get('date_to'):
            queryset = queryset.filter(payment_date__lte=filters['date_to'])
        
        # Amount range
        if filters.get('amount_min'):
            queryset = queryset.filter(amount__gte=Decimal(filters['amount_min']))
        if filters.get('amount_max'):
            queryset = queryset.filter(amount__lte=Decimal(filters['amount_max']))
        
        return queryset


class FilterBuilder:
    """Build filters from query parameters."""
    
    @staticmethod
    def build_invoice_filters(query_params: Dict[str, str]) -> Dict[str, Any]:
        """Convert query parameters to filter dictionary."""
        filters = {}
        
        if 'search' in query_params:
            filters['search'] = query_params.get('search')
        
        if 'status' in query_params:
            filters['status'] = query_params.get('status')
        
        if 'date_from' in query_params:
            from dateutil.parser import parse
            try:
                filters['date_from'] = parse(query_params['date_from'])
            except (ValueError, TypeError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Invalid date_from: {e}")
        
        if 'date_to' in query_params:
            from dateutil.parser import parse
            try:
                filters['date_to'] = parse(query_params['date_to'])
            except (ValueError, TypeError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Invalid date_to: {e}")
        
        if 'amount_min' in query_params:
            try:
                filters['amount_min'] = query_params['amount_min']
            except (ValueError, TypeError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Invalid amount_min: {e}")
        
        if 'amount_max' in query_params:
            try:
                filters['amount_max'] = query_params['amount_max']
            except (ValueError, TypeError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Invalid amount_max: {e}")
        
        if 'currency' in query_params:
            filters['currency'] = query_params.get('currency')
        
        if 'overdue' in query_params:
            filters['overdue_only'] = query_params.get('overdue').lower() == 'true'
        
        return filters
