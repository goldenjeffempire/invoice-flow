(function() {
    'use strict';

    const STORAGE_KEY = 'invoiceflow_draft_v3';
    const AUTOSAVE_DELAY = 1000;

    const currencySymbols = {
        USD: '$', EUR: '€', GBP: '£', NGN: '₦', CAD: 'C$', AUD: 'A$'
    };

    let lineItems = [];
    let saveTimeout = null;
    let currentCurrency = 'USD';

    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

    function init() {
        setupDateDefaults();
        loadDraft();
        setupEventListeners();
        updateSummary();
        updateItemsUI();
    }

    function setupDateDefaults() {
        const today = new Date().toISOString().split('T')[0];
        const due = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        
        const invoiceDateEl = $('#invoice_date');
        const dueDateEl = $('#due_date');
        
        if (invoiceDateEl && !invoiceDateEl.value) invoiceDateEl.value = today;
        if (dueDateEl && !dueDateEl.value) dueDateEl.value = due;
    }

    function setupEventListeners() {
        const form = $('#invoiceForm');
        if (form) {
            form.addEventListener('submit', handleSubmit);
            form.addEventListener('input', handleFormInput);
            form.addEventListener('change', handleFormChange);
        }

        const addFirstBtn = $('#addFirstBtn');
        const addItemBtn = $('#addItemBtn');
        if (addFirstBtn) addFirstBtn.addEventListener('click', () => addItem());
        if (addItemBtn) addItemBtn.addEventListener('click', () => addItem());

        const clearBtn = $('#clearBtn');
        if (clearBtn) clearBtn.addEventListener('click', clearForm);

        const previewBtn = $('#previewBtn');
        const previewClose = $('#previewClose');
        const previewOverlay = $('#previewOverlay');
        
        if (previewBtn) previewBtn.addEventListener('click', showPreview);
        if (previewClose) previewClose.addEventListener('click', hidePreview);
        if (previewOverlay) {
            previewOverlay.addEventListener('click', (e) => {
                if (e.target === previewOverlay) hidePreview();
            });
        }

        $$('.section-toggle').forEach(btn => {
            btn.addEventListener('click', toggleSection);
        });

        const currencySelect = $('#currency');
        if (currencySelect) {
            currencySelect.addEventListener('change', handleCurrencyChange);
            currentCurrency = currencySelect.value;
        }

        document.addEventListener('keydown', handleKeyDown);
    }

    function handleFormInput(e) {
        scheduleSave();
        if (e.target.id === 'tax_rate') {
            updateSummary();
        }
    }

    function handleFormChange(e) {
        scheduleSave();
    }

    function handleCurrencyChange(e) {
        currentCurrency = e.target.value;
        updateCurrencySymbols();
        updateSummary();
        scheduleSave();
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !['TEXTAREA'].includes(e.target.tagName)) {
            if (e.target.classList.contains('item-desc') || 
                e.target.classList.contains('item-rate') ||
                e.target.classList.contains('mobile-desc') ||
                e.target.classList.contains('mobile-rate')) {
                e.preventDefault();
                addItem();
            }
        }

        if (e.key === 'Escape') {
            hidePreview();
        }
    }

    function handleSubmit(e) {
        if (!validateForm()) {
            e.preventDefault();
            return;
        }

        const lineItemsInput = $('#lineItemsInput');
        if (lineItemsInput) {
            lineItemsInput.value = JSON.stringify(lineItems);
        }

        clearDraft();
    }

    function validateForm() {
        let valid = true;
        const required = ['business_name', 'client_name', 'invoice_date', 'due_date'];
        
        required.forEach(fieldId => {
            const field = $(`#${fieldId}`);
            const error = field?.parentElement?.querySelector('.field-error');
            
            if (field && !field.value.trim()) {
                valid = false;
                field.classList.add('error');
                if (error) error.textContent = 'This field is required';
            } else if (field) {
                field.classList.remove('error');
                if (error) error.textContent = '';
            }
        });

        if (lineItems.length === 0) {
            valid = false;
            const itemsEmpty = $('#itemsEmpty');
            if (itemsEmpty) {
                itemsEmpty.classList.add('shake');
                setTimeout(() => itemsEmpty.classList.remove('shake'), 500);
            }
        }

        return valid;
    }

    function addItem(data = null) {
        const item = data || {
            description: '',
            quantity: 1,
            unit_price: 0
        };

        lineItems.push(item);
        renderItems();
        updateItemsUI();
        updateSummary();
        scheduleSave();

        setTimeout(() => {
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                const mobileItems = $$('.mobile-item');
                const lastItem = mobileItems[mobileItems.length - 1];
                if (lastItem) {
                    const input = lastItem.querySelector('.mobile-desc');
                    if (input) input.focus();
                }
            } else {
                const rows = $$('.item-row');
                const lastRow = rows[rows.length - 1];
                if (lastRow) {
                    const input = lastRow.querySelector('.item-desc');
                    if (input) input.focus();
                }
            }
        }, 50);
    }

    function removeItem(index) {
        lineItems.splice(index, 1);
        renderItems();
        updateItemsUI();
        updateSummary();
        scheduleSave();
    }

    function duplicateItem(index) {
        const item = { ...lineItems[index] };
        lineItems.splice(index + 1, 0, item);
        renderItems();
        updateItemsUI();
        updateSummary();
        scheduleSave();
    }

    function updateItem(index, field, value) {
        if (lineItems[index]) {
            lineItems[index][field] = value;
            updateSummary();
            scheduleSave();
        }
    }

    function renderItems() {
        const itemsBody = $('#itemsBody');
        const itemRowTemplate = $('#itemRowTemplate');
        const mobileTemplate = $('#mobileItemTemplate');
        
        if (!itemsBody || !itemRowTemplate) return;

        itemsBody.innerHTML = '';
        const symbol = currencySymbols[currentCurrency] || '$';

        lineItems.forEach((item, index) => {
            const clone = itemRowTemplate.content.cloneNode(true);
            const row = clone.querySelector('.item-row');
            
            const descInput = row.querySelector('.item-desc');
            const qtyInput = row.querySelector('.item-qty');
            const rateInput = row.querySelector('.item-rate');
            const amountSpan = row.querySelector('.item-amount');
            const currencySym = row.querySelector('.currency-sym');
            
            descInput.value = item.description || '';
            qtyInput.value = item.quantity || 1;
            rateInput.value = item.unit_price || '';
            
            if (currencySym) currencySym.textContent = symbol;
            
            const amount = (item.quantity || 0) * (item.unit_price || 0);
            amountSpan.textContent = formatCurrency(amount);

            descInput.addEventListener('input', (e) => updateItem(index, 'description', e.target.value));
            qtyInput.addEventListener('input', (e) => {
                updateItem(index, 'quantity', parseFloat(e.target.value) || 0);
                updateRowAmount(row);
            });
            rateInput.addEventListener('input', (e) => {
                updateItem(index, 'unit_price', parseFloat(e.target.value) || 0);
                updateRowAmount(row);
            });

            const dupBtn = row.querySelector('.action-btn.dup');
            const delBtn = row.querySelector('.action-btn.del');
            
            if (dupBtn) dupBtn.addEventListener('click', () => duplicateItem(index));
            if (delBtn) delBtn.addEventListener('click', () => removeItem(index));

            row.addEventListener('dragstart', (e) => handleDragStart(e, index));
            row.addEventListener('dragover', handleDragOver);
            row.addEventListener('drop', (e) => handleDrop(e, index));
            row.addEventListener('dragend', handleDragEnd);

            itemsBody.appendChild(row);

            if (mobileTemplate) {
                const mobileClone = mobileTemplate.content.cloneNode(true);
                const mobileItem = mobileClone.querySelector('.mobile-item');
                
                const mobileNum = mobileItem.querySelector('.mobile-item-num');
                const mobileDesc = mobileItem.querySelector('.mobile-desc');
                const mobileQty = mobileItem.querySelector('.mobile-qty');
                const mobileRate = mobileItem.querySelector('.mobile-rate');
                const mobileAmount = mobileItem.querySelector('.mobile-amount');
                
                if (mobileNum) mobileNum.textContent = `Item ${index + 1}`;
                if (mobileDesc) mobileDesc.value = item.description || '';
                if (mobileQty) mobileQty.value = item.quantity || 1;
                if (mobileRate) mobileRate.value = item.unit_price || '';
                if (mobileAmount) mobileAmount.textContent = formatCurrency(amount);

                if (mobileDesc) {
                    mobileDesc.addEventListener('input', (e) => updateItem(index, 'description', e.target.value));
                }
                if (mobileQty) {
                    mobileQty.addEventListener('input', (e) => {
                        updateItem(index, 'quantity', parseFloat(e.target.value) || 0);
                        mobileAmount.textContent = formatCurrency(
                            (parseFloat(e.target.value) || 0) * (lineItems[index].unit_price || 0)
                        );
                    });
                }
                if (mobileRate) {
                    mobileRate.addEventListener('input', (e) => {
                        updateItem(index, 'unit_price', parseFloat(e.target.value) || 0);
                        mobileAmount.textContent = formatCurrency(
                            (lineItems[index].quantity || 0) * (parseFloat(e.target.value) || 0)
                        );
                    });
                }

                const mobileDup = mobileItem.querySelector('.mobile-btn.dup');
                const mobileDel = mobileItem.querySelector('.mobile-btn.del');
                
                if (mobileDup) mobileDup.addEventListener('click', () => duplicateItem(index));
                if (mobileDel) mobileDel.addEventListener('click', () => removeItem(index));

                itemsBody.appendChild(mobileItem);
            }
        });
    }

    function updateRowAmount(row) {
        const qty = parseFloat(row.querySelector('.item-qty')?.value) || 0;
        const rate = parseFloat(row.querySelector('.item-rate')?.value) || 0;
        const amountSpan = row.querySelector('.item-amount');
        if (amountSpan) {
            amountSpan.textContent = formatCurrency(qty * rate);
        }
    }

    function updateItemsUI() {
        const itemsEmpty = $('#itemsEmpty');
        const itemsTable = $('#itemsTable');
        const itemsFooter = $('#itemsFooter');
        const itemsCount = $('#itemsCount');

        if (lineItems.length === 0) {
            if (itemsEmpty) itemsEmpty.style.display = 'flex';
            if (itemsTable) itemsTable.style.display = 'none';
            if (itemsFooter) itemsFooter.style.display = 'none';
        } else {
            if (itemsEmpty) itemsEmpty.style.display = 'none';
            if (itemsTable) itemsTable.style.display = 'block';
            if (itemsFooter) itemsFooter.style.display = 'flex';
        }

        if (itemsCount) {
            itemsCount.textContent = `${lineItems.length} item${lineItems.length !== 1 ? 's' : ''}`;
        }
    }

    function updateSummary() {
        const subtotal = lineItems.reduce((sum, item) => {
            return sum + ((item.quantity || 0) * (item.unit_price || 0));
        }, 0);

        const taxRate = parseFloat($('#tax_rate')?.value) || 0;
        const tax = subtotal * (taxRate / 100);
        const total = subtotal + tax;

        const subtotalEl = $('#summarySubtotal');
        const taxEl = $('#summaryTax');
        const totalEl = $('#summaryTotal');
        const taxDisplay = $('#taxDisplay');

        if (subtotalEl) subtotalEl.textContent = formatCurrency(subtotal);
        if (taxEl) taxEl.textContent = formatCurrency(tax);
        if (totalEl) totalEl.textContent = formatCurrency(total);
        if (taxDisplay) taxDisplay.textContent = taxRate;
    }

    function updateCurrencySymbols() {
        const symbol = currencySymbols[currentCurrency] || '$';
        $$('.currency-sym').forEach(el => el.textContent = symbol);
        $$('.mobile-rate-wrap span').forEach(el => el.textContent = symbol);
        
        $$('.item-amount').forEach((el, i) => {
            if (lineItems[i]) {
                const amount = (lineItems[i].quantity || 0) * (lineItems[i].unit_price || 0);
                el.textContent = formatCurrency(amount);
            }
        });
        
        $$('.mobile-amount').forEach((el, i) => {
            if (lineItems[i]) {
                const amount = (lineItems[i].quantity || 0) * (lineItems[i].unit_price || 0);
                el.textContent = formatCurrency(amount);
            }
        });
    }

    function formatCurrency(amount) {
        const symbol = currencySymbols[currentCurrency] || '$';
        return `${symbol}${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
    }

    function toggleSection(e) {
        const btn = e.currentTarget;
        const section = btn.closest('.inv-section');
        const content = section?.querySelector('.section-content');
        const isExpanded = btn.getAttribute('aria-expanded') === 'true';
        
        btn.setAttribute('aria-expanded', !isExpanded);
        section?.classList.toggle('collapsed', isExpanded);
    }

    let draggedIndex = null;

    function handleDragStart(e, index) {
        draggedIndex = index;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDrop(e, targetIndex) {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === targetIndex) return;

        const item = lineItems.splice(draggedIndex, 1)[0];
        lineItems.splice(targetIndex, 0, item);
        
        renderItems();
        updateItemsUI();
        scheduleSave();
        draggedIndex = null;
    }

    function handleDragEnd(e) {
        e.target.classList.remove('dragging');
        draggedIndex = null;
    }

    function scheduleSave() {
        if (saveTimeout) clearTimeout(saveTimeout);
        
        updateSaveStatus('saving');
        
        saveTimeout = setTimeout(() => {
            saveDraft();
            updateSaveStatus('saved');
        }, AUTOSAVE_DELAY);
    }

    function updateSaveStatus(status) {
        const statusPill = $('#saveStatus');
        const dot = statusPill?.querySelector('.status-dot');
        const text = statusPill?.querySelector('.status-text');
        
        if (!statusPill) return;

        if (status === 'saving') {
            statusPill.style.background = '#fef3c7';
            statusPill.style.borderColor = '#fde68a';
            if (dot) dot.style.background = '#f59e0b';
            if (text) {
                text.textContent = 'Saving...';
                text.style.color = '#d97706';
            }
        } else {
            statusPill.style.background = '#f0fdf4';
            statusPill.style.borderColor = '#bbf7d0';
            if (dot) dot.style.background = '#22c55e';
            if (text) {
                text.textContent = 'Saved';
                text.style.color = '#16a34a';
            }
        }
    }

    function saveDraft() {
        const formData = {
            business_name: $('#business_name')?.value || '',
            business_email: $('#business_email')?.value || '',
            business_phone: $('#business_phone')?.value || '',
            business_address: $('#business_address')?.value || '',
            client_name: $('#client_name')?.value || '',
            client_email: $('#client_email')?.value || '',
            client_phone: $('#client_phone')?.value || '',
            client_address: $('#client_address')?.value || '',
            invoice_date: $('#invoice_date')?.value || '',
            due_date: $('#due_date')?.value || '',
            currency: $('#currency')?.value || 'USD',
            tax_rate: $('#tax_rate')?.value || '0',
            notes: $('#notes')?.value || '',
            bank_name: $('#bank_name')?.value || '',
            account_name: $('#account_name')?.value || '',
            account_number: $('#account_number')?.value || '',
            line_items: lineItems
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
                'invoice_date', 'due_date', 'currency', 'tax_rate', 'notes',
                'bank_name', 'account_name', 'account_number'
            ];

            fields.forEach(field => {
                const el = $(`#${field}`);
                if (el && data[field]) {
                    el.value = data[field];
                }
            });

            if (data.currency) {
                currentCurrency = data.currency;
            }

            if (Array.isArray(data.line_items) && data.line_items.length > 0) {
                lineItems = data.line_items;
                renderItems();
            }

            updateSaveStatus('saved');
        } catch (e) {
            console.warn('Could not load draft:', e);
        }
    }

    function clearDraft() {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            console.warn('Could not clear draft:', e);
        }
    }

    function clearForm() {
        if (!confirm('Clear all form data? This cannot be undone.')) return;

        $$('.inv-form input, .inv-form textarea, .inv-form select').forEach(el => {
            if (el.type === 'hidden') return;
            if (el.tagName === 'SELECT') {
                el.selectedIndex = 0;
            } else {
                el.value = '';
            }
        });

        lineItems = [];
        currentCurrency = 'USD';
        
        setupDateDefaults();
        renderItems();
        updateItemsUI();
        updateSummary();
        clearDraft();
        updateSaveStatus('saved');
    }

    function showPreview() {
        const previewOverlay = $('#previewOverlay');
        const previewBody = $('#previewBody');
        
        if (!previewOverlay || !previewBody) return;

        const businessName = $('#business_name')?.value || 'Your Business';
        const clientName = $('#client_name')?.value || 'Client Name';
        const invoiceDate = $('#invoice_date')?.value || '';
        const dueDate = $('#due_date')?.value || '';
        const taxRate = parseFloat($('#tax_rate')?.value) || 0;
        const notes = $('#notes')?.value || '';

        const subtotal = lineItems.reduce((sum, item) => {
            return sum + ((item.quantity || 0) * (item.unit_price || 0));
        }, 0);
        const tax = subtotal * (taxRate / 100);
        const total = subtotal + tax;

        let itemsHtml = lineItems.map((item, i) => `
            <tr>
                <td style="padding:12px;border-bottom:1px solid #e2e8f0;">${item.description || 'Item ' + (i + 1)}</td>
                <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;">${item.quantity || 0}</td>
                <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:right;">${formatCurrency(item.unit_price || 0)}</td>
                <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:600;">${formatCurrency((item.quantity || 0) * (item.unit_price || 0))}</td>
            </tr>
        `).join('');

        if (lineItems.length === 0) {
            itemsHtml = '<tr><td colspan="4" style="padding:40px;text-align:center;color:#94a3b8;">No items added yet</td></tr>';
        }

        previewBody.innerHTML = `
            <div style="max-width:600px;margin:0 auto;font-family:system-ui,-apple-system,sans-serif;">
                <div style="display:flex;justify-content:space-between;margin-bottom:32px;">
                    <div>
                        <h2 style="margin:0;color:#6366f1;font-size:1.5rem;">${businessName}</h2>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:2rem;font-weight:700;color:#0f172a;">INVOICE</div>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-bottom:32px;">
                    <div>
                        <div style="font-size:0.75rem;color:#64748b;margin-bottom:4px;">BILL TO</div>
                        <div style="font-weight:600;color:#0f172a;">${clientName}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="margin-bottom:8px;">
                            <span style="color:#64748b;">Date:</span>
                            <span style="margin-left:8px;font-weight:500;">${invoiceDate || 'Not set'}</span>
                        </div>
                        <div>
                            <span style="color:#64748b;">Due:</span>
                            <span style="margin-left:8px;font-weight:500;">${dueDate || 'Not set'}</span>
                        </div>
                    </div>
                </div>
                
                <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
                    <thead>
                        <tr style="background:#f8fafc;">
                            <th style="padding:12px;text-align:left;font-size:0.75rem;color:#64748b;font-weight:600;">Description</th>
                            <th style="padding:12px;text-align:center;font-size:0.75rem;color:#64748b;font-weight:600;">Qty</th>
                            <th style="padding:12px;text-align:right;font-size:0.75rem;color:#64748b;font-weight:600;">Rate</th>
                            <th style="padding:12px;text-align:right;font-size:0.75rem;color:#64748b;font-weight:600;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${itemsHtml}
                    </tbody>
                </table>
                
                <div style="display:flex;justify-content:flex-end;">
                    <div style="width:200px;">
                        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;">
                            <span style="color:#64748b;">Subtotal</span>
                            <span style="font-weight:500;">${formatCurrency(subtotal)}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;">
                            <span style="color:#64748b;">Tax (${taxRate}%)</span>
                            <span style="font-weight:500;">${formatCurrency(tax)}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:12px 0;font-size:1.125rem;">
                            <span style="font-weight:600;">Total</span>
                            <span style="font-weight:700;color:#6366f1;">${formatCurrency(total)}</span>
                        </div>
                    </div>
                </div>
                
                ${notes ? `
                <div style="margin-top:32px;padding:16px;background:#f8fafc;border-radius:8px;">
                    <div style="font-size:0.75rem;color:#64748b;margin-bottom:4px;">NOTES</div>
                    <div style="color:#334155;white-space:pre-wrap;">${notes}</div>
                </div>
                ` : ''}
            </div>
        `;

        previewOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function hidePreview() {
        const previewOverlay = $('#previewOverlay');
        if (previewOverlay) {
            previewOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
