/**
 * InvoiceFlow - Modern Invoice Creator v2.0
 * Advanced functionality with auto-save, drag-drop, and responsive design
 */

(function() {
    'use strict';

    const CURRENCY_SYMBOLS = {
        USD: '$', EUR: '€', GBP: '£', NGN: '₦', CAD: 'C$', AUD: 'A$'
    };

    const STORAGE_KEY = 'invoiceflow_draft';
    const AUTOSAVE_DELAY = 1500;

    let items = [];
    let autosaveTimer = null;
    let currentCurrency = 'USD';

    const elements = {
        form: null,
        lineItemsInput: null,
        itemsEmpty: null,
        itemsList: null,
        itemsRows: null,
        itemsAddBar: null,
        itemsBadge: null,
        summarySubtotal: null,
        summaryTax: null,
        summaryTotal: null,
        taxRateDisplay: null,
        taxRateInput: null,
        currencySelect: null,
        draftIndicator: null,
        clearDraftBtn: null,
        previewBtn: null,
        previewModal: null,
        previewClose: null,
        previewBody: null,
        submitBtn: null
    };

    function init() {
        cacheElements();
        bindEvents();
        loadDraft();
        setDefaultDates();
        updateItemsUI();
        updateSummary();
    }

    function cacheElements() {
        elements.form = document.getElementById('invoiceForm');
        elements.lineItemsInput = document.getElementById('lineItemsInput');
        elements.itemsEmpty = document.getElementById('itemsEmpty');
        elements.itemsList = document.getElementById('itemsList');
        elements.itemsRows = document.getElementById('itemsRows');
        elements.itemsAddBar = document.getElementById('itemsAddBar');
        elements.itemsBadge = document.getElementById('itemsBadge');
        elements.summarySubtotal = document.getElementById('summarySubtotal');
        elements.summaryTax = document.getElementById('summaryTax');
        elements.summaryTotal = document.getElementById('summaryTotal');
        elements.taxRateDisplay = document.getElementById('taxRateDisplay');
        elements.taxRateInput = document.getElementById('tax_rate');
        elements.currencySelect = document.getElementById('currency');
        elements.draftIndicator = document.getElementById('draftIndicator');
        elements.clearDraftBtn = document.getElementById('clearDraftBtn');
        elements.previewBtn = document.getElementById('previewBtn');
        elements.previewModal = document.getElementById('previewModal');
        elements.previewClose = document.getElementById('previewClose');
        elements.previewBody = document.getElementById('previewBody');
        elements.submitBtn = document.getElementById('submitBtn');
    }

    function bindEvents() {
        const addFirstBtn = document.getElementById('addFirstItemBtn');
        const addItemBtn = document.getElementById('addItemBtn');

        if (addFirstBtn) addFirstBtn.addEventListener('click', () => addItem());
        if (addItemBtn) addItemBtn.addEventListener('click', () => addItem());

        if (elements.taxRateInput) {
            elements.taxRateInput.addEventListener('input', () => {
                updateSummary();
                scheduleSave();
            });
        }

        if (elements.currencySelect) {
            elements.currencySelect.addEventListener('change', (e) => {
                currentCurrency = e.target.value;
                updateAllCurrencySymbols();
                updateSummary();
                scheduleSave();
            });
        }

        if (elements.clearDraftBtn) {
            elements.clearDraftBtn.addEventListener('click', clearDraft);
        }

        if (elements.previewBtn) {
            elements.previewBtn.addEventListener('click', showPreview);
        }

        if (elements.previewClose) {
            elements.previewClose.addEventListener('click', hidePreview);
        }

        if (elements.previewModal) {
            elements.previewModal.querySelector('.preview-overlay')?.addEventListener('click', hidePreview);
        }

        if (elements.form) {
            elements.form.addEventListener('submit', handleSubmit);
        }

        document.querySelectorAll('.card-toggle').forEach(btn => {
            btn.addEventListener('click', function() {
                const section = this.closest('.form-card');
                const body = section.querySelector('.card-body');
                const expanded = this.getAttribute('aria-expanded') === 'true';
                
                this.setAttribute('aria-expanded', !expanded);
                if (expanded) {
                    body.classList.add('collapsed');
                } else {
                    body.classList.remove('collapsed');
                }
            });
        });

        document.querySelectorAll('input, textarea, select').forEach(input => {
            if (input.id !== 'lineItemsInput') {
                input.addEventListener('input', scheduleSave);
                input.addEventListener('change', scheduleSave);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.previewModal?.style.display !== 'none') {
                hidePreview();
            }
        });
    }

    function setDefaultDates() {
        const invoiceDateInput = document.getElementById('invoice_date');
        const dueDateInput = document.getElementById('due_date');
        
        if (invoiceDateInput && !invoiceDateInput.value) {
            invoiceDateInput.value = formatDate(new Date());
        }
        
        if (dueDateInput && !dueDateInput.value) {
            const dueDate = new Date();
            dueDate.setDate(dueDate.getDate() + 30);
            dueDateInput.value = formatDate(dueDate);
        }
    }

    function formatDate(date) {
        return date.toISOString().split('T')[0];
    }

    function addItem(data = null) {
        const item = data || {
            id: generateId(),
            description: '',
            quantity: 1,
            rate: 0
        };

        items.push(item);
        renderItem(item);
        updateItemsUI();
        updateSummary();
        scheduleSave();

        if (!data) {
            setTimeout(() => {
                const isMobile = window.innerWidth <= 768;
                const selector = isMobile 
                    ? `.mobile-item-card[data-id="${item.id}"] .mobile-item-description`
                    : `.item-row[data-id="${item.id}"] .item-description`;
                const input = document.querySelector(selector);
                if (input) input.focus();
            }, 50);
        }
    }

    function renderItem(item) {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            renderMobileItem(item);
        } else {
            renderDesktopItem(item);
        }
    }

    function renderDesktopItem(item) {
        const template = document.getElementById('itemRowTemplate');
        if (!template || !elements.itemsRows) return;

        const clone = template.content.cloneNode(true);
        const row = clone.querySelector('.item-row');
        
        row.setAttribute('data-id', item.id);
        
        const descInput = row.querySelector('.item-description');
        const qtyInput = row.querySelector('.item-qty');
        const rateInput = row.querySelector('.item-rate');
        const amountSpan = row.querySelector('.item-amount');
        const currencyPrefix = row.querySelector('.currency-prefix');

        descInput.value = item.description;
        qtyInput.value = item.quantity;
        rateInput.value = item.rate || '';
        amountSpan.textContent = formatCurrency(calculateItemAmount(item));
        
        if (currencyPrefix) {
            currencyPrefix.textContent = getCurrencySymbol();
        }

        descInput.addEventListener('input', (e) => {
            item.description = e.target.value;
            scheduleSave();
        });

        qtyInput.addEventListener('input', (e) => {
            item.quantity = parseFloat(e.target.value) || 0;
            updateItemAmount(row, item);
            updateSummary();
            scheduleSave();
        });

        rateInput.addEventListener('input', (e) => {
            item.rate = parseFloat(e.target.value) || 0;
            updateItemAmount(row, item);
            updateSummary();
            scheduleSave();
        });

        rateInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addItem();
            }
        });

        const duplicateBtn = row.querySelector('.item-action-btn.duplicate');
        const deleteBtn = row.querySelector('.item-action-btn.delete');

        duplicateBtn?.addEventListener('click', () => duplicateItem(item.id));
        deleteBtn?.addEventListener('click', () => removeItem(item.id));

        setupDragDrop(row, item.id);

        elements.itemsRows.appendChild(row);
    }

    function renderMobileItem(item) {
        const template = document.getElementById('mobileItemTemplate');
        if (!template || !elements.itemsRows) return;

        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.mobile-item-card');
        
        card.setAttribute('data-id', item.id);

        const itemNumber = card.querySelector('.mobile-item-number');
        const descInput = card.querySelector('.mobile-item-description');
        const qtyInput = card.querySelector('.mobile-item-qty');
        const rateInput = card.querySelector('.mobile-item-rate');
        const amountSpan = card.querySelector('.mobile-item-amount');

        itemNumber.textContent = `Item ${items.indexOf(item) + 1}`;
        descInput.value = item.description;
        qtyInput.value = item.quantity;
        rateInput.value = item.rate || '';
        amountSpan.textContent = formatCurrency(calculateItemAmount(item));

        descInput.addEventListener('input', (e) => {
            item.description = e.target.value;
            scheduleSave();
        });

        qtyInput.addEventListener('input', (e) => {
            item.quantity = parseFloat(e.target.value) || 0;
            updateMobileItemAmount(card, item);
            updateSummary();
            scheduleSave();
        });

        rateInput.addEventListener('input', (e) => {
            item.rate = parseFloat(e.target.value) || 0;
            updateMobileItemAmount(card, item);
            updateSummary();
            scheduleSave();
        });

        const duplicateBtn = card.querySelector('.mobile-action-btn.duplicate');
        const deleteBtn = card.querySelector('.mobile-action-btn.delete');

        duplicateBtn?.addEventListener('click', () => duplicateItem(item.id));
        deleteBtn?.addEventListener('click', () => removeItem(item.id));

        elements.itemsRows.appendChild(card);
    }

    function updateItemAmount(row, item) {
        const amountSpan = row.querySelector('.item-amount');
        if (amountSpan) {
            amountSpan.textContent = formatCurrency(calculateItemAmount(item));
        }
    }

    function updateMobileItemAmount(card, item) {
        const amountSpan = card.querySelector('.mobile-item-amount');
        if (amountSpan) {
            amountSpan.textContent = formatCurrency(calculateItemAmount(item));
        }
    }

    function calculateItemAmount(item) {
        return (item.quantity || 0) * (item.rate || 0);
    }

    function duplicateItem(id) {
        const original = items.find(i => i.id === id);
        if (!original) return;

        const newItem = {
            id: generateId(),
            description: original.description,
            quantity: original.quantity,
            rate: original.rate
        };

        const index = items.findIndex(i => i.id === id);
        items.splice(index + 1, 0, newItem);
        
        rebuildItemsList();
        updateSummary();
        scheduleSave();
    }

    function removeItem(id) {
        items = items.filter(i => i.id !== id);
        
        const element = document.querySelector(`[data-id="${id}"]`);
        if (element) {
            element.style.transition = 'opacity 0.2s, transform 0.2s';
            element.style.opacity = '0';
            element.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                element.remove();
                updateItemsUI();
                updateMobileItemNumbers();
            }, 200);
        }
        
        updateSummary();
        scheduleSave();
    }

    function updateMobileItemNumbers() {
        document.querySelectorAll('.mobile-item-card').forEach((card, index) => {
            const numberEl = card.querySelector('.mobile-item-number');
            if (numberEl) {
                numberEl.textContent = `Item ${index + 1}`;
            }
        });
    }

    function rebuildItemsList() {
        if (elements.itemsRows) {
            elements.itemsRows.innerHTML = '';
        }
        items.forEach(item => renderItem(item));
        updateItemsUI();
    }

    function updateItemsUI() {
        const hasItems = items.length > 0;
        
        if (elements.itemsEmpty) {
            elements.itemsEmpty.style.display = hasItems ? 'none' : 'flex';
        }
        if (elements.itemsList) {
            elements.itemsList.style.display = hasItems ? 'block' : 'none';
        }
        if (elements.itemsAddBar) {
            elements.itemsAddBar.style.display = hasItems ? 'flex' : 'none';
        }
        if (elements.itemsBadge) {
            elements.itemsBadge.textContent = `${items.length} item${items.length !== 1 ? 's' : ''}`;
        }
    }

    function updateSummary() {
        const subtotal = items.reduce((sum, item) => sum + calculateItemAmount(item), 0);
        const taxRate = parseFloat(elements.taxRateInput?.value) || 0;
        const tax = subtotal * (taxRate / 100);
        const total = subtotal + tax;

        if (elements.summarySubtotal) {
            elements.summarySubtotal.textContent = formatCurrency(subtotal);
        }
        if (elements.summaryTax) {
            elements.summaryTax.textContent = formatCurrency(tax);
        }
        if (elements.summaryTotal) {
            elements.summaryTotal.textContent = formatCurrency(total);
        }
        if (elements.taxRateDisplay) {
            elements.taxRateDisplay.textContent = taxRate;
        }

        if (elements.lineItemsInput) {
            elements.lineItemsInput.value = JSON.stringify(items.map(item => ({
                description: item.description,
                quantity: item.quantity,
                unit_price: item.rate
            })));
        }
    }

    function getCurrencySymbol() {
        return CURRENCY_SYMBOLS[currentCurrency] || '$';
    }

    function formatCurrency(amount) {
        const symbol = getCurrencySymbol();
        return symbol + amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    function updateAllCurrencySymbols() {
        document.querySelectorAll('.currency-prefix').forEach(el => {
            el.textContent = getCurrencySymbol();
        });

        items.forEach(item => {
            const row = document.querySelector(`.item-row[data-id="${item.id}"]`);
            if (row) {
                const amountSpan = row.querySelector('.item-amount');
                if (amountSpan) {
                    amountSpan.textContent = formatCurrency(calculateItemAmount(item));
                }
            }
            
            const mobileCard = document.querySelector(`.mobile-item-card[data-id="${item.id}"]`);
            if (mobileCard) {
                const amountSpan = mobileCard.querySelector('.mobile-item-amount');
                if (amountSpan) {
                    amountSpan.textContent = formatCurrency(calculateItemAmount(item));
                }
            }
        });
    }

    function setupDragDrop(element, itemId) {
        element.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', itemId);
            element.classList.add('dragging');
        });

        element.addEventListener('dragend', () => {
            element.classList.remove('dragging');
            document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
        });

        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            element.classList.add('drag-over');
        });

        element.addEventListener('dragleave', () => {
            element.classList.remove('drag-over');
        });

        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('drag-over');
            
            const draggedId = e.dataTransfer.getData('text/plain');
            const targetId = itemId;
            
            if (draggedId !== targetId) {
                reorderItems(draggedId, targetId);
            }
        });
    }

    function reorderItems(draggedId, targetId) {
        const draggedIndex = items.findIndex(i => i.id === draggedId);
        const targetIndex = items.findIndex(i => i.id === targetId);
        
        if (draggedIndex === -1 || targetIndex === -1) return;
        
        const [draggedItem] = items.splice(draggedIndex, 1);
        items.splice(targetIndex, 0, draggedItem);
        
        rebuildItemsList();
        scheduleSave();
    }

    function generateId() {
        return 'item_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function scheduleSave() {
        if (autosaveTimer) {
            clearTimeout(autosaveTimer);
        }
        
        showSaving();
        
        autosaveTimer = setTimeout(() => {
            saveDraft();
            showSaved();
        }, AUTOSAVE_DELAY);
    }

    function saveDraft() {
        const formData = {
            business_name: document.getElementById('business_name')?.value || '',
            business_email: document.getElementById('business_email')?.value || '',
            business_phone: document.getElementById('business_phone')?.value || '',
            business_address: document.getElementById('business_address')?.value || '',
            client_name: document.getElementById('client_name')?.value || '',
            client_email: document.getElementById('client_email')?.value || '',
            client_phone: document.getElementById('client_phone')?.value || '',
            client_address: document.getElementById('client_address')?.value || '',
            invoice_date: document.getElementById('invoice_date')?.value || '',
            due_date: document.getElementById('due_date')?.value || '',
            currency: document.getElementById('currency')?.value || 'USD',
            tax_rate: document.getElementById('tax_rate')?.value || '0',
            notes: document.getElementById('notes')?.value || '',
            items: items
        };

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(formData));
        } catch (e) {
            console.warn('Could not save draft:', e);
        }
    }

    function loadDraft() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return;

            const data = JSON.parse(saved);

            const fields = [
                'business_name', 'business_email', 'business_phone', 'business_address',
                'client_name', 'client_email', 'client_phone', 'client_address',
                'invoice_date', 'due_date', 'currency', 'tax_rate', 'notes'
            ];

            fields.forEach(field => {
                const el = document.getElementById(field);
                if (el && data[field] !== undefined) {
                    if (!el.value) {
                        el.value = data[field];
                    }
                }
            });

            if (data.currency) {
                currentCurrency = data.currency;
            }

            if (data.items && Array.isArray(data.items) && data.items.length > 0) {
                data.items.forEach(item => {
                    addItem({
                        id: item.id || generateId(),
                        description: item.description || '',
                        quantity: item.quantity || 1,
                        rate: item.rate || item.unit_price || 0
                    });
                });
            }

            if (elements.clearDraftBtn) {
                elements.clearDraftBtn.style.display = 'flex';
            }

        } catch (e) {
            console.warn('Could not load draft:', e);
        }
    }

    function clearDraft() {
        if (!confirm('Clear all entered data and start fresh?')) return;

        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {}

        items = [];
        
        const fields = document.querySelectorAll('#invoiceForm input, #invoiceForm textarea, #invoiceForm select');
        fields.forEach(field => {
            if (field.type === 'hidden') return;
            if (field.tagName === 'SELECT') {
                field.selectedIndex = 0;
            } else {
                field.value = '';
            }
        });

        currentCurrency = 'USD';
        
        if (elements.itemsRows) {
            elements.itemsRows.innerHTML = '';
        }
        
        setDefaultDates();
        updateItemsUI();
        updateSummary();
        
        if (elements.clearDraftBtn) {
            elements.clearDraftBtn.style.display = 'none';
        }
    }

    function showSaving() {
        if (elements.draftIndicator) {
            elements.draftIndicator.querySelector('.draft-text').textContent = 'Saving...';
            elements.draftIndicator.querySelector('.pulse-dot').style.background = '#f59e0b';
        }
    }

    function showSaved() {
        if (elements.draftIndicator) {
            elements.draftIndicator.querySelector('.draft-text').textContent = 'Draft auto-saved';
            elements.draftIndicator.querySelector('.pulse-dot').style.background = '#10b981';
        }

        if (elements.clearDraftBtn) {
            elements.clearDraftBtn.style.display = 'flex';
        }
    }

    function showPreview() {
        if (!elements.previewModal || !elements.previewBody) return;

        const data = {
            business_name: document.getElementById('business_name')?.value || 'Your Business',
            client_name: document.getElementById('client_name')?.value || 'Client Name',
            invoice_date: document.getElementById('invoice_date')?.value || '',
            due_date: document.getElementById('due_date')?.value || '',
            items: items,
            subtotal: items.reduce((sum, item) => sum + calculateItemAmount(item), 0),
            tax_rate: parseFloat(elements.taxRateInput?.value) || 0
        };

        data.tax = data.subtotal * (data.tax_rate / 100);
        data.total = data.subtotal + data.tax;

        elements.previewBody.innerHTML = generatePreviewHTML(data);
        elements.previewModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function hidePreview() {
        if (elements.previewModal) {
            elements.previewModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    function generatePreviewHTML(data) {
        const itemsHTML = data.items.map(item => `
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">${escapeHtml(item.description) || 'No description'}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">${item.quantity}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">${formatCurrency(item.rate)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: 500;">${formatCurrency(calculateItemAmount(item))}</td>
            </tr>
        `).join('');

        return `
            <div style="font-family: system-ui, sans-serif;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 32px;">
                    <div>
                        <h2 style="font-size: 1.5rem; font-weight: 700; color: #0f172a; margin: 0 0 4px;">${escapeHtml(data.business_name)}</h2>
                        <p style="color: #64748b; margin: 0;">Invoice Preview</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.875rem; color: #64748b;">Issue Date: ${data.invoice_date || 'Not set'}</div>
                        <div style="font-size: 0.875rem; color: #64748b;">Due Date: ${data.due_date || 'Not set'}</div>
                    </div>
                </div>
                
                <div style="background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; margin-bottom: 4px;">Bill To</div>
                    <div style="font-weight: 600; color: #0f172a;">${escapeHtml(data.client_name)}</div>
                </div>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                    <thead>
                        <tr style="background: #f1f5f9;">
                            <th style="padding: 12px; text-align: left; font-size: 0.75rem; text-transform: uppercase; color: #64748b;">Description</th>
                            <th style="padding: 12px; text-align: center; font-size: 0.75rem; text-transform: uppercase; color: #64748b;">Qty</th>
                            <th style="padding: 12px; text-align: right; font-size: 0.75rem; text-transform: uppercase; color: #64748b;">Rate</th>
                            <th style="padding: 12px; text-align: right; font-size: 0.75rem; text-transform: uppercase; color: #64748b;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${itemsHTML || '<tr><td colspan="4" style="padding: 24px; text-align: center; color: #94a3b8;">No items added</td></tr>'}
                    </tbody>
                </table>
                
                <div style="display: flex; justify-content: flex-end;">
                    <div style="width: 250px;">
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; color: #64748b;">
                            <span>Subtotal</span>
                            <span>${formatCurrency(data.subtotal)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; color: #64748b;">
                            <span>Tax (${data.tax_rate}%)</span>
                            <span>${formatCurrency(data.tax)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px 0; border-top: 2px solid #e2e8f0; font-weight: 700; font-size: 1.125rem; color: #0f172a;">
                            <span>Total</span>
                            <span style="color: #6366f1;">${formatCurrency(data.total)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function handleSubmit(e) {
        const requiredFields = [
            { id: 'business_name', label: 'Business Name' },
            { id: 'client_name', label: 'Client Name' },
            { id: 'invoice_date', label: 'Invoice Date' },
            { id: 'due_date', label: 'Due Date' }
        ];

        let hasErrors = false;
        const errors = [];

        requiredFields.forEach(field => {
            const el = document.getElementById(field.id);
            const errorEl = document.getElementById(field.id + '_error');
            
            if (!el?.value?.trim()) {
                hasErrors = true;
                errors.push(field.label + ' is required');
                el?.classList.add('error');
                if (errorEl) errorEl.textContent = 'Required';
            } else {
                el?.classList.remove('error');
                if (errorEl) errorEl.textContent = '';
            }
        });

        if (items.length === 0) {
            hasErrors = true;
            errors.push('Please add at least one line item');
        }

        if (hasErrors) {
            e.preventDefault();
            
            const firstError = document.querySelector('.error');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }

            return false;
        }

        updateSummary();

        if (elements.submitBtn) {
            elements.submitBtn.disabled = true;
            elements.submitBtn.innerHTML = `
                <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
                    <path d="M21 12a9 9 0 11-6.219-8.56"/>
                </svg>
                Creating...
            `;
        }

        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {}

        return true;
    }

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            rebuildItemsList();
        }, 250);
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();