/**
 * Invoice Creator V3 - Enhanced Invoice Creation Interface
 */

(function() {
    'use strict';

    const InvoiceCreatorV3 = {
        init: function() {
            this.cacheElements();
            this.bindEvents();
            this.initializeFormState();
        },

        cacheElements: function() {
            this.form = document.querySelector('form[data-invoice-form]');
            this.itemsList = document.querySelector('[data-items-list]');
            this.addItemBtn = document.querySelector('[data-add-item]');
            this.preview = document.querySelector('[data-invoice-preview]');
            this.submitBtn = document.querySelector('[data-submit-btn]');
        },

        bindEvents: function() {
            if (this.addItemBtn) {
                this.addItemBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.addInvoiceItem();
                });
            }

            if (this.form) {
                this.form.addEventListener('input', (e) => {
                    if (e.target.closest('[data-item-row]')) {
                        this.updatePreview();
                    }
                });

                this.form.addEventListener('change', (e) => {
                    this.updatePreview();
                });
            }

            document.addEventListener('click', (e) => {
                if (e.target.closest('[data-remove-item]')) {
                    const row = e.target.closest('[data-item-row]');
                    if (row) {
                        row.remove();
                        this.updatePreview();
                    }
                }
            });
        },

        initializeFormState: function() {
            if (this.form) {
                this.updatePreview();
            }
        },

        addInvoiceItem: function() {
            if (!this.itemsList) return;

            const itemRow = document.createElement('div');
            itemRow.className = 'item-row';
            itemRow.setAttribute('data-item-row', '');
            itemRow.innerHTML = `
                <input type="text" class="item-description" placeholder="Item description" />
                <input type="number" class="item-quantity" placeholder="Qty" min="1" value="1" />
                <input type="number" class="item-rate" placeholder="Rate" min="0" step="0.01" />
                <input type="number" class="item-amount" placeholder="Amount" readonly />
                <button type="button" class="remove-item-btn" data-remove-item="true">Remove</button>
            `;

            const quantityInput = itemRow.querySelector('.item-quantity');
            const rateInput = itemRow.querySelector('.item-rate');
            const amountInput = itemRow.querySelector('.item-amount');

            const updateAmount = () => {
                const qty = parseFloat(quantityInput.value) || 0;
                const rate = parseFloat(rateInput.value) || 0;
                const amount = qty * rate;
                amountInput.value = amount.toFixed(2);
                this.updatePreview();
            };

            quantityInput.addEventListener('input', updateAmount);
            rateInput.addEventListener('input', updateAmount);

            this.itemsList.appendChild(itemRow);
            itemRow.querySelector('.item-description').focus();
        },

        getFormData: function() {
            if (!this.form) return null;

            const data = new FormData(this.form);
            const items = [];

            const itemRows = this.form.querySelectorAll('[data-item-row]');
            itemRows.forEach((row) => {
                const description = row.querySelector('.item-description')?.value || '';
                const quantity = parseFloat(row.querySelector('.item-quantity')?.value) || 0;
                const rate = parseFloat(row.querySelector('.item-rate')?.value) || 0;
                const amount = parseFloat(row.querySelector('.item-amount')?.value) || 0;

                if (description || quantity || rate) {
                    items.push({
                        description,
                        quantity,
                        rate,
                        amount: quantity * rate
                    });
                }
            });

            return {
                clientName: data.get('client_name') || 'Client Name',
                clientEmail: data.get('client_email') || 'client@example.com',
                invoiceNumber: data.get('invoice_number') || 'INV-2024-001',
                invoiceDate: data.get('invoice_date') || new Date().toISOString().split('T')[0],
                dueDate: data.get('due_date') || '',
                items: items
            };
        },

        calculateTotals: function(items) {
            let subtotal = 0;
            items.forEach((item) => {
                subtotal += item.amount;
            });

            const tax = subtotal * 0.1;
            const total = subtotal + tax;

            return { subtotal, tax, total };
        },

        updatePreview: function() {
            if (!this.preview) return;

            const formData = this.getFormData();
            if (!formData) return;

            const { items } = formData;
            const { subtotal, tax, total } = this.calculateTotals(items);

            let itemsHtml = '';
            items.forEach((item) => {
                itemsHtml += `
                    <tr>
                        <td>${this.escapeHtml(item.description)}</td>
                        <td class="text-right">${item.quantity}</td>
                        <td class="text-right">₦${item.rate.toFixed(2)}</td>
                        <td class="text-right">₦${item.amount.toFixed(2)}</td>
                    </tr>
                `;
            });

            this.preview.innerHTML = `
                <div class="invoice-header">
                    <div class="invoice-logo">InvoiceFlow</div>
                </div>
                <div class="invoice-details">
                    <div class="detail-block">
                        <h4>Bill To</h4>
                        <p><strong>${this.escapeHtml(formData.clientName)}</strong></p>
                        <p>${this.escapeHtml(formData.clientEmail)}</p>
                    </div>
                    <div class="detail-block text-right">
                        <h4>Invoice #</h4>
                        <p><strong>${this.escapeHtml(formData.invoiceNumber)}</strong></p>
                        <p>Date: ${formData.invoiceDate}</p>
                    </div>
                </div>
                ${items.length > 0 ? `
                    <table class="items-table">
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th class="text-right">Qty</th>
                                <th class="text-right">Rate</th>
                                <th class="text-right">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${itemsHtml}
                        </tbody>
                    </table>
                    <div class="invoice-summary">
                        <div class="summary-items">
                            <div class="summary-row">
                                <span>Subtotal</span>
                                <span>₦${subtotal.toFixed(2)}</span>
                            </div>
                            <div class="summary-row">
                                <span>Tax (10%)</span>
                                <span>₦${tax.toFixed(2)}</span>
                            </div>
                            <div class="summary-row total">
                                <span>Total</span>
                                <span>₦${total.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                ` : '<p class="text-muted">Add items to generate preview</p>'}
            `;
        },

        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            InvoiceCreatorV3.init();
        });
    } else {
        InvoiceCreatorV3.init();
    }

    // Export for external use if needed
    window.InvoiceCreatorV3 = InvoiceCreatorV3;
})();
