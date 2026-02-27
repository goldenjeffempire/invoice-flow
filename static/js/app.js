const InvoiceFlow = {
  init() {
    this.initScrollReveal();
    this.initScrollProgress();
    this.initScrollToTop();
    this.initLazyLoading();
    this.initToasts();
    this.initModals();
    this.initDropdowns();
    this.initTabs();
    this.initMobileMenu();
    this.initFormValidation();
    this.initSmoothScroll();
    this.initImageLoading();
  },

  initScrollReveal() {
    const reveals = document.querySelectorAll('.reveal');
    if (!reveals.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    reveals.forEach(el => observer.observe(el));

    const staggerContainers = document.querySelectorAll('.stagger-children');
    const staggerObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    staggerContainers.forEach(el => staggerObserver.observe(el));
  },

  initScrollProgress() {
    const progressBar = document.querySelector('.scroll-progress');
    if (!progressBar) return;

    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? scrollTop / docHeight : 0;
      progressBar.style.transform = `scaleX(${progress})`;
    }, { passive: true });
  },

  initScrollToTop() {
    const button = document.querySelector('.scroll-to-top');
    if (!button) return;

    window.addEventListener('scroll', () => {
      if (window.scrollY > 500) {
        button.classList.add('visible');
      } else {
        button.classList.remove('visible');
      }
    }, { passive: true });

    button.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  },

  initLazyLoading() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    
    lazyImages.forEach(img => {
      if (img.complete) {
        img.classList.add('loaded');
      } else {
        img.addEventListener('load', () => {
          img.classList.add('loaded');
        });
      }
    });

    if ('IntersectionObserver' in window) {
      const lazyBgs = document.querySelectorAll('[data-bg]');
      const bgObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const el = entry.target;
            el.style.backgroundImage = `url(${el.dataset.bg})`;
            el.classList.add('loaded');
            bgObserver.unobserve(el);
          }
        });
      }, { rootMargin: '100px' });

      lazyBgs.forEach(el => bgObserver.observe(el));
    }
  },

  toastContainer: null,
  toasts: [],

  initToasts() {
    if (!document.querySelector('.toast-container')) {
      const container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('role', 'alert');
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
      this.toastContainer = container;
    } else {
      this.toastContainer = document.querySelector('.toast-container');
    }
  },

  showToast(message, type = 'info', duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-icon">
        ${this.getToastIcon(type)}
      </div>
      <div class="toast-content">
        <p>${message}</p>
      </div>
      <button class="toast-dismiss" aria-label="Dismiss">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    `;

    const dismissBtn = toast.querySelector('.toast-dismiss');
    dismissBtn.addEventListener('click', () => this.dismissToast(toast));

    this.toastContainer.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => this.dismissToast(toast), duration);
    }

    return toast;
  },

  dismissToast(toast) {
    if (!toast.parentNode) return;
    toast.classList.add('exiting');
    setTimeout(() => toast.remove(), 300);
  },

  getToastIcon(type) {
    const icons = {
      success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
      info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };
    return icons[type] || icons.info;
  },

  initModals() {
    document.querySelectorAll('[data-modal-trigger]').forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const modalId = trigger.dataset.modalTrigger;
        this.openModal(modalId);
      });
    });

    document.querySelectorAll('[data-modal-close]').forEach(closeBtn => {
      closeBtn.addEventListener('click', () => {
        const modal = closeBtn.closest('.modal');
        if (modal) this.closeModal(modal.id);
      });
    });

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', () => {
        const modal = document.querySelector('.modal.active');
        if (modal) this.closeModal(modal.id);
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const modal = document.querySelector('.modal.active');
        if (modal) this.closeModal(modal.id);
      }
    });
  },

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.querySelector('.modal-backdrop');
    if (!modal) return;

    document.body.style.overflow = 'hidden';
    if (backdrop) backdrop.classList.add('active');
    modal.classList.add('active');
    
    const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable) focusable.focus();
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.querySelector('.modal-backdrop');
    if (!modal) return;

    modal.classList.remove('active');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  },

  initDropdowns() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
      const trigger = dropdown.querySelector('.dropdown-trigger, button');
      const menu = dropdown.querySelector('.dropdown-menu');
      
      if (!trigger || !menu) return;

      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = dropdown.classList.contains('open');
        
        document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
        
        if (!isOpen) {
          dropdown.classList.add('open');
        }
      });
    });

    document.addEventListener('click', () => {
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    });
  },

  initTabs() {
    document.querySelectorAll('.tabs').forEach(tabContainer => {
      const tabs = tabContainer.querySelectorAll('.tab');
      const parent = tabContainer.parentElement;
      
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const targetId = tab.dataset.tab;
          
          tabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          
          if (targetId && parent) {
            parent.querySelectorAll('.tab-content').forEach(content => {
              content.classList.remove('active');
            });
            const target = parent.querySelector(`#${targetId}`);
            if (target) target.classList.add('active');
          }
        });
      });
    });
  },

  initMobileMenu() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const menu = document.querySelector('.mobile-menu');
    const backdrop = document.querySelector('.mobile-menu-backdrop');
    
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
      const isOpen = menu.classList.contains('open');
      menu.classList.toggle('open');
      if (backdrop) backdrop.classList.toggle('open');
      document.body.style.overflow = isOpen ? '' : 'hidden';
      toggle.setAttribute('aria-expanded', !isOpen);
    });

    if (backdrop) {
      backdrop.addEventListener('click', () => {
        menu.classList.remove('open');
        backdrop.classList.remove('open');
        document.body.style.overflow = '';
        toggle.setAttribute('aria-expanded', 'false');
      });
    }

    menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        menu.classList.remove('open');
        if (backdrop) backdrop.classList.remove('open');
        document.body.style.overflow = '';
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  },

  initFormValidation() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
      form.addEventListener('submit', (e) => {
        let isValid = true;
        
        form.querySelectorAll('[required]').forEach(input => {
          if (!input.value.trim()) {
            isValid = false;
            this.showFieldError(input, 'This field is required');
          } else {
            this.clearFieldError(input);
          }
        });

        form.querySelectorAll('[type="email"]').forEach(input => {
          if (input.value && !this.isValidEmail(input.value)) {
            isValid = false;
            this.showFieldError(input, 'Please enter a valid email address');
          }
        });

        if (!isValid) {
          e.preventDefault();
          const firstError = form.querySelector('.is-invalid');
          if (firstError) firstError.focus();
        }
      });

      form.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('blur', () => {
          if (input.hasAttribute('required') && !input.value.trim()) {
            this.showFieldError(input, 'This field is required');
          } else if (input.type === 'email' && input.value && !this.isValidEmail(input.value)) {
            this.showFieldError(input, 'Please enter a valid email address');
          } else {
            this.clearFieldError(input);
          }
        });

        input.addEventListener('input', () => {
          if (input.classList.contains('is-invalid')) {
            this.clearFieldError(input);
          }
        });
      });
    });
  },

  showFieldError(input, message) {
    input.classList.add('is-invalid');
    input.classList.remove('is-valid');
    
    let errorEl = input.parentNode.querySelector('.form-error');
    if (!errorEl) {
      errorEl = document.createElement('div');
      errorEl.className = 'form-error';
      input.parentNode.appendChild(errorEl);
    }
    errorEl.textContent = message;
  },

  clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorEl = input.parentNode.querySelector('.form-error');
    if (errorEl) errorEl.remove();
  },

  isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        const href = anchor.getAttribute('href');
        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });
  },

  initImageLoading() {
    document.querySelectorAll('img').forEach(img => {
      if (img.complete) {
        img.classList.add('loaded');
      } else {
        img.addEventListener('load', () => img.classList.add('loaded'));
        img.addEventListener('error', () => {
          img.style.display = 'none';
          console.warn('Failed to load image:', img.src);
        });
      }
    });
  },

  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  },

  formatDate(date, options = {}) {
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    };
    return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
  },

  formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
  },

  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },

  showSkeleton(container, count = 3) {
    container.innerHTML = Array(count).fill(`
      <div class="skeleton-row">
        <div class="skeleton skeleton-avatar"></div>
        <div class="flex-1">
          <div class="skeleton skeleton-title"></div>
          <div class="skeleton skeleton-text"></div>
        </div>
      </div>
    `).join('');
  },

  hideSkeleton(container) {
    container.querySelectorAll('.skeleton-row').forEach(el => el.remove());
  },

  setButtonLoading(button, loading = true) {
    if (loading) {
      button.classList.add('btn-loading');
      button.disabled = true;
      button.dataset.originalText = button.innerHTML;
    } else {
      button.classList.remove('btn-loading');
      button.disabled = false;
      if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  InvoiceFlow.init();
});

window.InvoiceFlow = InvoiceFlow;
