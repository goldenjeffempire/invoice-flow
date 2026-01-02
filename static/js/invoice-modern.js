/**
 * Modern Invoice Pages - Enhanced Interactivity
 * Real-time validation, dynamic forms, improved UX
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize form validation
  initializeFormValidation();
  
  // Initialize real-time search
  initializeRealtimeSearch();
  
  // Initialize line items
  initializeLineItems();
  
  // Initialize status badges
  updateStatusBadges();
  
  // Initialize tooltips
  initializeTooltips();
});

/**
 * Form Validation
 */
function initializeFormValidation() {
  const form = document.getElementById('invoiceForm') || document.querySelector('form');
  if (!form) return;
  
  const inputs = form.querySelectorAll('input:not([type="hidden"]), textarea, select');
  
  inputs.forEach(input => {
    // Real-time validation on blur
    input.addEventListener('blur', function() {
      validateField(this);
    });
    
    // Visual feedback on input
    input.addEventListener('input', function() {
      if (this.classList.contains('field-valid')) {
        validateField(this);
      }
    });
  });
  
  // Form submission validation
  form.addEventListener('submit', function(e) {
    let isValid = true;
    inputs.forEach(input => {
      if (!validateField(input)) {
        isValid = false;
      }
    });
    
    if (!isValid) {
      e.preventDefault();
      showMessage('Please fix the errors below', 'error');
    }
  });
}

function validateField(field) {
  const value = field.value.trim();
  let isValid = true;
  let errorMessage = '';
  
  // Check required fields
  if (field.hasAttribute('required') && !value) {
    isValid = false;
    errorMessage = 'This field is required';
  }
  
  // Specific field validation
  if (isValid && value) {
    if (field.type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      isValid = emailRegex.test(value);
      if (!isValid) errorMessage = 'Please enter a valid email';
    }
    
    if (field.type === 'tel' && value) {
      const phoneRegex = /^[\d\s\-\+\(\)]+$/;
      isValid = phoneRegex.test(value);
      if (!isValid) errorMessage = 'Please enter a valid phone number';
    }
    
    if (field.type === 'number' && value) {
      isValid = !isNaN(value) && value > 0;
      if (!isValid) errorMessage = 'Please enter a valid number';
    }
    
    if (field.name === 'due_date' || field.name === 'invoice_date') {
      const date = new Date(value);
      isValid = !isNaN(date.getTime());
      if (!isValid) errorMessage = 'Please enter a valid date';
    }
  }
  
  // Update UI
  const errorElement = field.parentElement.querySelector('.field-error-message');
  if (isValid) {
    field.classList.remove('field-invalid');
    field.classList.add('field-valid');
    if (errorElement) {
      errorElement.classList.remove('show');
      errorElement.textContent = '';
    }
  } else {
    field.classList.remove('field-valid');
    field.classList.add('field-invalid');
    if (errorElement) {
      errorElement.classList.add('show');
      errorElement.textContent = errorMessage;
    }
  }
  
  return isValid;
}

/**
 * Real-time Search
 */
function initializeRealtimeSearch() {
  const searchInput = document.querySelector('[name="search"]');
  if (!searchInput) return;
  
  let searchTimeout;
  
  searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    
    if (query.length === 0) {
      // Reset if empty
      const form = document.getElementById('searchForm');
      if (form) form.submit();
      return;
    }
    
    if (query.length >= 2) {
      // Debounce search
      searchTimeout = setTimeout(() => {
        const form = document.getElementById('searchForm');
        if (form) form.submit();
      }, 300);
    }
  });
}

/**
 * Line Items Management
 */
function initializeLineItems() {
  const addButton = document.querySelector('[data-action="add-line-item"]');
  if (!addButton) return;
  
  addButton.addEventListener('click', function() {
    addLineItem();
  });
  
  // Initialize remove buttons
  updateLineItemRemoveButtons();
}

function addLineItem() {
  const container = document.querySelector('[data-container="line-items"]');
  if (!container) return;
  
  const itemCount = container.querySelectorAll('[data-line-item]').length;
  const newItem = createLineItemElement(itemCount);
  container.appendChild(newItem);
  
  // Add remove button listener
  const removeBtn = newItem.querySelector('[data-action="remove-line-item"]');
  if (removeBtn) {
    removeBtn.addEventListener('click', function() {
      newItem.remove();
      updateLineItemsInput();
    });
  }
  
  // Update totals on input
  const inputs = newItem.querySelectorAll('input[data-field]');
  inputs.forEach(input => {
    input.addEventListener('change', updateLineItemsInput);
    input.addEventListener('input', updateLineItemsInput);
  });
}

function createLineItemElement(index) {
  const div = document.createElement('div');
  div.className = 'line-item-modern';
  div.setAttribute('data-line-item', index);
  div.innerHTML = `
    <input type="text" class="form-input-modern" placeholder="Description" data-field="description">
    <input type="number" class="form-input-modern" placeholder="Qty" step="0.01" data-field="quantity" value="1">
    <input type="number" class="form-input-modern" placeholder="Unit Price" step="0.01" data-field="unit_price">
    <input type="number" class="form-input-modern" placeholder="Amount" step="0.01" data-field="amount" readonly>
    <button type="button" class="line-item-remove-btn" data-action="remove-line-item" title="Remove">×</button>
  `;
  return div;
}

function updateLineItemRemoveButtons() {
  const items = document.querySelectorAll('[data-container="line-items"] [data-line-item]');
  items.forEach((item, index) => {
    const removeBtn = item.querySelector('[data-action="remove-line-item"]');
    if (removeBtn) {
      removeBtn.addEventListener('click', function(e) {
        e.preventDefault();
        item.remove();
        updateLineItemsInput();
      });
    }
  });
}

function updateLineItemsInput() {
  const container = document.querySelector('[data-container="line-items"]');
  const input = document.getElementById('lineItemsInput');
  if (!container || !input) return;
  
  const items = [];
  container.querySelectorAll('[data-line-item]').forEach(item => {
    const data = {};
    item.querySelectorAll('input[data-field]').forEach(field => {
      const fieldName = field.getAttribute('data-field');
      data[fieldName] = field.value;
    });
    items.push(data);
  });
  
  input.value = JSON.stringify(items);
}

/**
 * Status Badges
 */
function updateStatusBadges() {
  const badges = document.querySelectorAll('[data-status]');
  badges.forEach(badge => {
    const status = badge.getAttribute('data-status');
    badge.classList.add(`status-${status}`);
  });
}

/**
 * Tooltips
 */
function initializeTooltips() {
  const tooltips = document.querySelectorAll('[title]');
  tooltips.forEach(element => {
    element.addEventListener('mouseenter', showTooltip);
    element.addEventListener('mouseleave', hideTooltip);
  });
}

function showTooltip(e) {
  const title = e.target.getAttribute('title');
  if (!title) return;
  
  const tooltip = document.createElement('div');
  tooltip.className = 'tooltip';
  tooltip.textContent = title;
  tooltip.style.cssText = `
    position: absolute;
    background: #1f2937;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.8125rem;
    white-space: nowrap;
    z-index: 1000;
    pointer-events: none;
  `;
  
  document.body.appendChild(tooltip);
  
  const rect = e.target.getBoundingClientRect();
  tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
  tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
  
  e.target._tooltip = tooltip;
}

function hideTooltip(e) {
  if (e.target._tooltip) {
    e.target._tooltip.remove();
    delete e.target._tooltip;
  }
}

/**
 * Messages
 */
function showMessage(message, type = 'info') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message message-${type}`;
  messageDiv.textContent = message;
  messageDiv.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 16px 20px;
    background: ${type === 'error' ? '#ef4444' : '#10b981'};
    color: white;
    border-radius: 8px;
    font-size: 0.9375rem;
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(messageDiv);
  
  setTimeout(() => {
    messageDiv.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => messageDiv.remove(), 300);
  }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

/**
 * Utility: Export selected invoices
 */
function exportSelected() {
  const selected = document.querySelectorAll('input.invoice-row-checkbox:checked');
  if (selected.length === 0) {
    showMessage('Please select invoices to export', 'error');
    return;
  }
  
  const ids = Array.from(selected).map(cb => cb.value).join(',');
  window.location.href = `/invoices/export/?ids=${ids}`;
}

/**
 * Utility: Clear selection
 */
function clearSelection() {
  document.querySelectorAll('input.invoice-row-checkbox').forEach(cb => cb.checked = false);
  document.getElementById('bulkActionsBar').classList.remove('active');
}
