/**
 * Client-side validation for invoice forms
 * Provides real-time validation feedback and error handling
 */

class InvoiceValidator {
    /**
     * Validate email format
     */
    static isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate phone number format
     */
    static isValidPhone(phone) {
        if (!phone) return true; // Optional field
        const phoneRegex = /^[\d\s\-\(\)\+]+$/;
        const digitsOnly = phone.replace(/\D/g, '');
        return phoneRegex.test(phone) && digitsOnly.length >= 10;
    }

    /**
     * Validate positive decimal number
     */
    static isValidPositiveDecimal(value) {
        const num = parseFloat(value);
        return !isNaN(num) && num > 0;
    }

    /**
     * Validate tax rate (0-100)
     */
    static isValidTaxRate(value) {
        const num = parseFloat(value);
        return !isNaN(num) && num >= 0 && num <= 100;
    }

    /**
     * Validate required field
     */
    static isNotEmpty(value) {
        return value && value.trim().length > 0;
    }

    /**
     * Validate invoice date
     */
    static isValidInvoiceDate(date) {
        if (!date) return false;
        const invoiceDate = new Date(date);
        const today = new Date();
        const maxFutureDate = new Date();
        maxFutureDate.setFullYear(maxFutureDate.getFullYear() + 1);
        return invoiceDate <= maxFutureDate;
    }

    /**
     * Show field error
     */
    static showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        field.classList.add('field-error');
        const errorEl = field.parentElement.querySelector('.field-error-message');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }

    /**
     * Clear field error
     */
    static clearFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        field.classList.remove('field-error');
        const errorEl = field.parentElement.querySelector('.field-error-message');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    /**
     * Validate invoice form before submission
     */
    static validateInvoiceForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        let isValid = true;

        // Validate client email
        const clientEmail = form.querySelector('[name="client_email"]');
        if (clientEmail && !this.isValidEmail(clientEmail.value)) {
            this.showFieldError(clientEmail.id, 'Invalid email address');
            isValid = false;
        } else if (clientEmail) {
            this.clearFieldError(clientEmail.id);
        }

        // Validate client phone
        const clientPhone = form.querySelector('[name="client_phone"]');
        if (clientPhone && clientPhone.value && !this.isValidPhone(clientPhone.value)) {
            this.showFieldError(clientPhone.id, 'Invalid phone number');
            isValid = false;
        } else if (clientPhone) {
            this.clearFieldError(clientPhone.id);
        }

        // Validate tax rate
        const taxRate = form.querySelector('[name="tax_rate"]');
        if (taxRate && taxRate.value && !this.isValidTaxRate(taxRate.value)) {
            this.showFieldError(taxRate.id, 'Tax rate must be between 0 and 100');
            isValid = false;
        } else if (taxRate) {
            this.clearFieldError(taxRate.id);
        }

        // Validate line items
        const lineItems = form.querySelectorAll('[name="description[]"]');
        if (lineItems.length === 0) {
            alert('Add at least one line item');
            isValid = false;
        }

        return isValid;
    }
}

// Auto-validate on form input
document.addEventListener('DOMContentLoaded', function() {
    // Email validation
    document.querySelectorAll('input[type="email"]').forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value && !InvoiceValidator.isValidEmail(this.value)) {
                InvoiceValidator.showFieldError(this.id, 'Invalid email address');
            } else {
                InvoiceValidator.clearFieldError(this.id);
            }
        });
    });

    // Phone validation
    document.querySelectorAll('input[type="tel"]').forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value && !InvoiceValidator.isValidPhone(this.value)) {
                InvoiceValidator.showFieldError(this.id, 'Invalid phone number');
            } else {
                InvoiceValidator.clearFieldError(this.id);
            }
        });
    });

    // Decimal validation
    document.querySelectorAll('input[type="number"]').forEach(field => {
        field.addEventListener('blur', function() {
            const isDecimal = this.getAttribute('step')?.includes('.');
            if (this.value && !InvoiceValidator.isValidPositiveDecimal(this.value)) {
                const message = this.value < 0 ? 'Amount cannot be negative' : 'Invalid number';
                InvoiceValidator.showFieldError(this.id, message);
            } else {
                InvoiceValidator.clearFieldError(this.id);
            }
        });
    });

    // Form submission
    document.querySelectorAll('form[data-validate="invoice"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!InvoiceValidator.validateInvoiceForm(this.id)) {
                e.preventDefault();
            }
        });
    });
});
