/**
 * Advanced invoice management features
 * Handles invoice operations, real-time calculations, and user interactions
 */

class InvoiceManager {
    constructor() {
        this.lineItems = [];
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Form submission
        const invoiceForm = document.querySelector('form[data-invoice-form]');
        if (invoiceForm) {
            invoiceForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Line item management
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="remove-item"]')) {
                this.removeLineItem(e.target);
            }
        });

        // Real-time calculations
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-field="quantity"], [data-field="unit_price"], [data-field="tax_rate"]')) {
                this.updateCalculations();
            }
        });
    }

    /**
     * Handle form submission with validation
     */
    handleFormSubmit(event) {
        if (!this.validateForm()) {
            event.preventDefault();
            this.showError('Please fix all validation errors before submitting.');
            return false;
        }
        return true;
    }

    /**
     * Validate entire form
     */
    validateForm() {
        const form = event.target;
        let isValid = true;

        // Validate business information
        const businessEmail = form.querySelector('[name="business_email"]');
        if (businessEmail && businessEmail.value && !InvoiceValidator.isValidEmail(businessEmail.value)) {
            InvoiceValidator.showFieldError(businessEmail.id, 'Invalid business email');
            isValid = false;
        }

        // Validate client information
        const clientEmail = form.querySelector('[name="client_email"]');
        if (clientEmail && clientEmail.value && !InvoiceValidator.isValidEmail(clientEmail.value)) {
            InvoiceValidator.showFieldError(clientEmail.id, 'Invalid client email');
            isValid = false;
        }

        const clientPhone = form.querySelector('[name="client_phone"]');
        if (clientPhone && clientPhone.value && !InvoiceValidator.isValidPhone(clientPhone.value)) {
            InvoiceValidator.showFieldError(clientPhone.id, 'Invalid phone number');
            isValid = false;
        }

        // Validate line items
        const items = document.querySelectorAll('[data-line-item]');
        if (items.length === 0) {
            this.showError('Add at least one line item');
            isValid = false;
        }

        items.forEach(item => {
            const quantity = item.querySelector('[data-field="quantity"]');
            const unitPrice = item.querySelector('[data-field="unit_price"]');

            if (quantity && !InvoiceValidator.isValidPositiveDecimal(quantity.value)) {
                InvoiceValidator.showFieldError(quantity.id, 'Quantity must be a positive number');
                isValid = false;
            }

            if (unitPrice && !InvoiceValidator.isValidPositiveDecimal(unitPrice.value)) {
                InvoiceValidator.showFieldError(unitPrice.id, 'Price must be a positive number');
                isValid = false;
            }
        });

        // Validate tax rate
        const taxRate = form.querySelector('[name="tax_rate"]');
        if (taxRate && taxRate.value && !InvoiceValidator.isValidTaxRate(taxRate.value)) {
            InvoiceValidator.showFieldError(taxRate.id, 'Tax rate must be between 0 and 100');
            isValid = false;
        }

        return isValid;
    }

    /**
     * Update calculations for line items and totals
     */
    updateCalculations() {
        let subtotal = 0;

        // Calculate line item totals
        document.querySelectorAll('[data-line-item]').forEach(item => {
            const quantity = parseFloat(item.querySelector('[data-field="quantity"]')?.value || 0);
            const unitPrice = parseFloat(item.querySelector('[data-field="unit_price"]')?.value || 0);
            const itemTotal = quantity * unitPrice;

            const totalDisplay = item.querySelector('[data-field="item-total"]');
            if (totalDisplay) {
                totalDisplay.textContent = itemTotal.toFixed(2);
            }

            subtotal += itemTotal;
        });

        // Update subtotal display
        const subtotalDisplay = document.querySelector('[data-field="subtotal"]');
        if (subtotalDisplay) {
            subtotalDisplay.textContent = subtotal.toFixed(2);
        }

        // Calculate and update tax
        const taxRate = parseFloat(document.querySelector('[name="tax_rate"]')?.value || 0);
        const taxAmount = (subtotal * taxRate) / 100;

        const taxDisplay = document.querySelector('[data-field="tax-amount"]');
        if (taxDisplay) {
            taxDisplay.textContent = taxAmount.toFixed(2);
        }

        // Update total
        const total = subtotal + taxAmount;
        const totalDisplay = document.querySelector('[data-field="total"]');
        if (totalDisplay) {
            totalDisplay.textContent = total.toFixed(2);
        }

        // Store line items as JSON for form submission
        const lineItemsInput = document.querySelector('[name="line_items"]');
        if (lineItemsInput) {
            this.lineItems = this.getLineItemsData();
            lineItemsInput.value = JSON.stringify(this.lineItems);
        }
    }

    /**
     * Get current line items data
     */
    getLineItemsData() {
        const items = [];
        document.querySelectorAll('[data-line-item]').forEach(item => {
            items.push({
                description: item.querySelector('[data-field="description"]')?.value || '',
                quantity: parseFloat(item.querySelector('[data-field="quantity"]')?.value || 0),
                unit_price: parseFloat(item.querySelector('[data-field="unit_price"]')?.value || 0),
            });
        });
        return items;
    }

    /**
     * Add new line item
     */
    addLineItem() {
        const container = document.querySelector('[data-line-items-container]');
        if (!container) return;

        const itemCount = document.querySelectorAll('[data-line-item]').length;
        const newItem = document.createElement('div');
        newItem.setAttribute('data-line-item', itemCount);
        newItem.className = 'line-item-light';
        newItem.innerHTML = `
            <input type="text" data-field="description" placeholder="Item description" required>
            <input type="number" data-field="quantity" placeholder="Qty" min="1" step="1" value="1" required>
            <input type="number" data-field="unit_price" placeholder="0.00" min="0" step="0.01" value="0" required>
            <div data-field="item-total">0.00</div>
            <button type="button" data-action="remove-item" class="remove-item-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        `;
        container.appendChild(newItem);
        this.updateCalculations();
    }

    /**
     * Remove line item
     */
    removeLineItem(button) {
        const items = document.querySelectorAll('[data-line-item]');
        if (items.length <= 1) {
            this.showError('At least one line item is required');
            return;
        }

        button.closest('[data-line-item]').remove();
        this.updateCalculations();
    }

    /**
     * Show error message
     */
    showError(message) {
        const alertEl = document.createElement('div');
        alertEl.className = 'alert alert-error';
        alertEl.textContent = message;
        alertEl.style.cssText = `
            background: #fee2e2;
            color: #991b1b;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            border-left: 4px solid #991b1b;
            animation: slideDown 0.3s ease;
        `;

        const form = document.querySelector('form[data-invoice-form]');
        if (form) {
            form.parentElement.insertBefore(alertEl, form);
            setTimeout(() => alertEl.remove(), 5000);
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        const alertEl = document.createElement('div');
        alertEl.className = 'alert alert-success';
        alertEl.textContent = message;
        alertEl.style.cssText = `
            background: #dcfce7;
            color: #166534;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            border-left: 4px solid #166534;
            animation: slideDown 0.3s ease;
        `;

        const form = document.querySelector('form[data-invoice-form]');
        if (form) {
            form.parentElement.insertBefore(alertEl, form);
            setTimeout(() => alertEl.remove(), 5000);
        }
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', () => {
    window.invoiceManager = new InvoiceManager();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+S or Cmd+S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const form = document.querySelector('form[data-invoice-form]');
        if (form) {
            form.submit();
        }
    }

    // Ctrl+L or Cmd+L to add line item
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        if (window.invoiceManager) {
            window.invoiceManager.addLineItem();
        }
    }
});

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .alert {
        animation: slideDown 0.3s ease;
    }
`;
document.head.appendChild(style);
