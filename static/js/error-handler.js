/**
 * Centralized Error Handler for InvoiceFlow
 * 
 * Provides consistent error display:
 * - Toast notifications for transient errors
 * - Inline field errors for validation
 * - Error pages for fatal errors
 */

const ErrorHandler = {
  toastContainer: null,

  init() {
    this.createToastContainer();
    this.setupGlobalErrorHandler();
  },

  createToastContainer() {
    if (document.getElementById('toast-container')) {
      this.toastContainer = document.getElementById('toast-container');
      return;
    }

    this.toastContainer = document.createElement('div');
    this.toastContainer.id = 'toast-container';
    this.toastContainer.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm';
    document.body.appendChild(this.toastContainer);
  },

  setupGlobalErrorHandler() {
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
    });
  },

  showToast(message, type = 'error', duration = 5000) {
    const toast = document.createElement('div');
    
    const bgColors = {
      error: 'bg-red-500',
      warning: 'bg-yellow-500',
      success: 'bg-green-500',
      info: 'bg-blue-500',
    };

    const icons = {
      error: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`,
      warning: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>`,
      success: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`,
      info: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`,
    };

    toast.className = `${bgColors[type]} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-slide-in`;
    toast.innerHTML = `
      ${icons[type]}
      <span class="flex-1">${this.escapeHtml(message)}</span>
      <button class="opacity-70 hover:opacity-100 transition-opacity" onclick="this.parentElement.remove()">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    `;

    this.toastContainer.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add('animate-fade-out');
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }

    return toast;
  },

  showError(message, duration = 5000) {
    return this.showToast(message, 'error', duration);
  },

  showWarning(message, duration = 5000) {
    return this.showToast(message, 'warning', duration);
  },

  showSuccess(message, duration = 3000) {
    return this.showToast(message, 'success', duration);
  },

  showInfo(message, duration = 4000) {
    return this.showToast(message, 'info', duration);
  },

  handleApiError(response) {
    if (!response.success && response.error) {
      const { code, message, fields } = response.error;

      this.showError(message);

      if (fields && fields.length > 0) {
        this.showFieldErrors(fields);
      }

      return {
        code,
        message,
        fields: fields || [],
        requestId: response.request_id,
      };
    }

    return null;
  },

  showFieldErrors(fields) {
    this.clearFieldErrors();

    fields.forEach(({ field, message }) => {
      const input = document.querySelector(`[name="${field}"]`);
      if (input) {
        input.classList.add('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
        
        const errorEl = document.createElement('p');
        errorEl.className = 'mt-1 text-sm text-red-600 field-error';
        errorEl.textContent = message;
        errorEl.dataset.field = field;
        
        input.parentElement.appendChild(errorEl);
      }
    });
  },

  clearFieldErrors() {
    document.querySelectorAll('.field-error').forEach(el => el.remove());
    
    document.querySelectorAll('.border-red-500').forEach(el => {
      el.classList.remove('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
    });
  },

  clearFieldError(fieldName) {
    const errorEl = document.querySelector(`.field-error[data-field="${fieldName}"]`);
    if (errorEl) errorEl.remove();

    const input = document.querySelector(`[name="${fieldName}"]`);
    if (input) {
      input.classList.remove('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
    }
  },

  async handleFetch(url, options = {}) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...options.headers,
        },
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        this.handleApiError(data);
        return { success: false, error: data.error, requestId: data.request_id };
      }

      return { success: true, data: data.data || data };
    } catch (error) {
      console.error('Fetch error:', error);
      this.showError('Network error. Please check your connection.');
      return { success: false, error: { code: 'NETWORK_ERROR', message: error.message } };
    }
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(100%);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes fadeOut {
    from {
      opacity: 1;
    }
    to {
      opacity: 0;
    }
  }

  .animate-slide-in {
    animation: slideIn 0.3s ease-out forwards;
  }

  .animate-fade-out {
    animation: fadeOut 0.3s ease-out forwards;
  }
`;
document.head.appendChild(styleSheet);

document.addEventListener('DOMContentLoaded', () => {
  ErrorHandler.init();
});

window.ErrorHandler = ErrorHandler;
