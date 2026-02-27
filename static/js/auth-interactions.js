/**
 * InvoiceFlow Authentication Interactions
 * Micro-interactions, real-time validation, and enhanced UX
 */

(function() {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const ValidationRules = {
    username: {
      minLength: 3,
      maxLength: 30,
      pattern: /^[a-zA-Z0-9_]+$/,
      messages: {
        required: 'Username is required',
        minLength: 'Username must be at least 3 characters',
        maxLength: 'Username must be less than 30 characters',
        pattern: 'Username can only contain letters, numbers, and underscores'
      }
    },
    email: {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      messages: {
        required: 'Email is required',
        pattern: 'Please enter a valid email address'
      }
    },
    password: {
      minLength: 8,
      requirements: [
        { test: (v) => v.length >= 8, label: '8+ characters', key: 'length' },
        { test: (v) => /[A-Z]/.test(v), label: 'Uppercase letter', key: 'upper' },
        { test: (v) => /[a-z]/.test(v), label: 'Lowercase letter', key: 'lower' },
        { test: (v) => /\d/.test(v), label: 'Number', key: 'number' },
        { test: (v) => /[!@#$%^&*(),.?":{}|<>]/.test(v), label: 'Special character', key: 'special' }
      ]
    }
  };

  function addClass(el, className) {
    if (el) el.classList.add(className);
  }

  function removeClass(el, className) {
    if (el) el.classList.remove(className);
  }

  function animateElement(el, animation, duration = 300) {
    if (prefersReducedMotion || !el) return Promise.resolve();
    return new Promise((resolve) => {
      el.style.animation = `${animation} ${duration}ms ease`;
      setTimeout(() => {
        el.style.animation = '';
        resolve();
      }, duration);
    });
  }

  function showFieldError(input, message) {
    const wrapper = input.closest('.form-group') || input.parentElement;
    let errorEl = wrapper.querySelector('.field-error');
    
    if (!errorEl) {
      errorEl = document.createElement('p');
      errorEl.className = 'field-error text-sm text-red-600 mt-2 flex items-center gap-1.5 opacity-0';
      errorEl.innerHTML = `
        <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <span class="error-text"></span>
      `;
      wrapper.appendChild(errorEl);
    }
    
    errorEl.querySelector('.error-text').textContent = message;
    addClass(input, 'border-red-400');
    addClass(input, 'focus:border-red-500');
    addClass(input, 'focus:ring-red-100');
    removeClass(input, 'border-slate-200');
    removeClass(input, 'border-emerald-400');
    
    requestAnimationFrame(() => {
      errorEl.style.opacity = '1';
      errorEl.style.transform = 'translateY(0)';
    });
    
    if (!prefersReducedMotion) {
      input.style.animation = 'shake 0.4s ease';
      setTimeout(() => input.style.animation = '', 400);
    }
  }

  function showFieldSuccess(input) {
    const wrapper = input.closest('.form-group') || input.parentElement;
    const errorEl = wrapper.querySelector('.field-error');
    
    if (errorEl) {
      errorEl.style.opacity = '0';
      setTimeout(() => errorEl.remove(), 200);
    }
    
    removeClass(input, 'border-red-400');
    removeClass(input, 'focus:border-red-500');
    removeClass(input, 'focus:ring-red-100');
    addClass(input, 'border-emerald-400');
    addClass(input, 'focus:border-emerald-500');
    addClass(input, 'focus:ring-emerald-100');
  }

  function clearFieldState(input) {
    const wrapper = input.closest('.form-group') || input.parentElement;
    const errorEl = wrapper.querySelector('.field-error');
    if (errorEl) errorEl.remove();
    
    removeClass(input, 'border-red-400');
    removeClass(input, 'border-emerald-400');
    addClass(input, 'border-slate-200');
  }

  function validateField(input) {
    const name = input.name;
    const value = input.value.trim();
    
    if (input.required && !value) {
      const fieldName = input.closest('.form-group')?.querySelector('label')?.textContent || name;
      showFieldError(input, `${fieldName} is required`);
      return false;
    }
    
    if (!value) {
      clearFieldState(input);
      return true;
    }

    if (name === 'username') {
      const rules = ValidationRules.username;
      if (value.length < rules.minLength) {
        showFieldError(input, rules.messages.minLength);
        return false;
      }
      if (value.length > rules.maxLength) {
        showFieldError(input, rules.messages.maxLength);
        return false;
      }
      if (!rules.pattern.test(value)) {
        showFieldError(input, rules.messages.pattern);
        return false;
      }
    }
    
    if (name === 'email' || input.type === 'email') {
      if (!ValidationRules.email.pattern.test(value)) {
        showFieldError(input, ValidationRules.email.messages.pattern);
        return false;
      }
    }
    
    if (name === 'password' || name === 'password1') {
      const reqs = ValidationRules.password.requirements;
      const failed = reqs.filter(r => !r.test(value));
      if (failed.length > 0) {
        showFieldError(input, `Password needs: ${failed.map(f => f.label.toLowerCase()).join(', ')}`);
        return false;
      }
    }
    
    if (name === 'confirm_password' || name === 'password2') {
      const passwordInput = document.querySelector('input[name="password"], input[name="password1"]');
      if (passwordInput && value !== passwordInput.value) {
        showFieldError(input, 'Passwords do not match');
        return false;
      }
    }
    
    showFieldSuccess(input);
    return true;
  }

  function createPasswordStrengthUI(passwordInput) {
    const wrapper = passwordInput.closest('.form-group') || passwordInput.parentElement;
    let strengthContainer = wrapper.querySelector('.password-strength-container');
    
    if (!strengthContainer) {
      strengthContainer = document.createElement('div');
      strengthContainer.className = 'password-strength-container mt-3';
      strengthContainer.innerHTML = `
        <div class="flex gap-1 mb-2">
          <div class="strength-bar h-1 flex-1 rounded-full bg-slate-200 transition-all duration-300"></div>
          <div class="strength-bar h-1 flex-1 rounded-full bg-slate-200 transition-all duration-300"></div>
          <div class="strength-bar h-1 flex-1 rounded-full bg-slate-200 transition-all duration-300"></div>
          <div class="strength-bar h-1 flex-1 rounded-full bg-slate-200 transition-all duration-300"></div>
        </div>
        <div class="password-requirements grid grid-cols-2 gap-2 text-xs">
          ${ValidationRules.password.requirements.map(r => `
            <div class="requirement flex items-center gap-1.5 text-slate-400" data-key="${r.key}">
              <svg class="w-3.5 h-3.5 check-icon hidden text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              <svg class="w-3.5 h-3.5 circle-icon text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke-width="2"/>
              </svg>
              <span>${r.label}</span>
            </div>
          `).join('')}
        </div>
      `;
      
      const existingStrength = wrapper.querySelector('.password-strength');
      if (existingStrength) {
        existingStrength.replaceWith(strengthContainer);
      } else {
        passwordInput.parentNode.insertBefore(strengthContainer, passwordInput.nextSibling);
      }
    }
    
    return strengthContainer;
  }

  function updatePasswordStrength(passwordInput, strengthContainer) {
    const value = passwordInput.value;
    const requirements = ValidationRules.password.requirements;
    let passed = 0;
    
    requirements.forEach(req => {
      const el = strengthContainer.querySelector(`[data-key="${req.key}"]`);
      if (el) {
        const isPassed = req.test(value);
        const checkIcon = el.querySelector('.check-icon');
        const circleIcon = el.querySelector('.circle-icon');
        
        if (isPassed) {
          passed++;
          addClass(el, 'text-emerald-600');
          removeClass(el, 'text-slate-400');
          checkIcon.classList.remove('hidden');
          circleIcon.classList.add('hidden');
        } else {
          removeClass(el, 'text-emerald-600');
          addClass(el, 'text-slate-400');
          checkIcon.classList.add('hidden');
          circleIcon.classList.remove('hidden');
        }
      }
    });
    
    const bars = strengthContainer.querySelectorAll('.strength-bar');
    const strengthLevel = Math.ceil((passed / requirements.length) * 4);
    const colors = ['', 'bg-red-500', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500'];
    
    bars.forEach((bar, i) => {
      bar.className = 'strength-bar h-1 flex-1 rounded-full transition-all duration-300';
      if (i < strengthLevel) {
        addClass(bar, colors[strengthLevel]);
      } else {
        addClass(bar, 'bg-slate-200');
      }
    });
  }

  function setupPasswordToggle(passwordInput) {
    const wrapper = passwordInput.parentElement;
    if (wrapper.querySelector('.password-toggle')) return;
    
    wrapper.style.position = 'relative';
    
    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'password-toggle absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:text-primary-600';
    toggleBtn.setAttribute('aria-label', 'Toggle password visibility');
    toggleBtn.innerHTML = `
      <svg class="eye-open w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
      </svg>
      <svg class="eye-closed w-5 h-5 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
      </svg>
    `;
    
    toggleBtn.addEventListener('click', () => {
      const isPassword = passwordInput.type === 'password';
      passwordInput.type = isPassword ? 'text' : 'password';
      toggleBtn.querySelector('.eye-open').classList.toggle('hidden', !isPassword);
      toggleBtn.querySelector('.eye-closed').classList.toggle('hidden', isPassword);
    });
    
    wrapper.appendChild(toggleBtn);
    passwordInput.style.paddingRight = '3rem';
  }

  function setupFormSubmitState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    const originalContent = submitBtn.innerHTML;
    
    form.addEventListener('submit', (e) => {
      const inputs = form.querySelectorAll('input[required]');
      let isValid = true;
      
      inputs.forEach(input => {
        if (!validateField(input)) {
          isValid = false;
        }
      });
      
      if (!isValid) {
        e.preventDefault();
        const firstError = form.querySelector('.border-red-400');
        if (firstError) firstError.focus();
        return;
      }
      
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <span class="flex items-center justify-center gap-2">
          <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Processing...</span>
        </span>
      `;
      
      setTimeout(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalContent;
      }, 10000);
    });
  }

  function setupMFACodeInput(input) {
    if (!input) return;
    
    input.addEventListener('input', (e) => {
      let value = e.target.value.replace(/[^0-9A-Za-z]/g, '').toUpperCase();
      
      if (value.length > 8 && !value.match(/[A-Z]/)) {
        value = value.slice(0, 6);
      }
      
      e.target.value = value;
      
      if (value.length === 6 && /^\d{6}$/.test(value)) {
        addClass(input, 'border-emerald-400');
        removeClass(input, 'border-slate-200');
        
        if (!prefersReducedMotion) {
          input.style.animation = 'pulse 0.3s ease';
          setTimeout(() => input.style.animation = '', 300);
        }
      } else if (value.length === 8) {
        addClass(input, 'border-emerald-400');
        removeClass(input, 'border-slate-200');
      } else {
        removeClass(input, 'border-emerald-400');
        addClass(input, 'border-slate-200');
      }
    });
    
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && input.value.length >= 6) {
        const form = input.closest('form');
        if (form) form.submit();
      }
    });
  }

  function init() {
    const forms = document.querySelectorAll('form[data-validate], form');
    
    forms.forEach(form => {
      const inputs = form.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"])');
      
      inputs.forEach(input => {
        input.addEventListener('blur', () => validateField(input));
        
        if (input.name.includes('password') && !input.name.includes('confirm')) {
          const strengthContainer = createPasswordStrengthUI(input);
          input.addEventListener('input', () => updatePasswordStrength(input, strengthContainer));
          setupPasswordToggle(input);
        }
        
        if (input.name.includes('confirm_password') || input.name === 'password2') {
          setupPasswordToggle(input);
        }
        
        if (input.name === 'code' && input.closest('.code-input, [inputmode="numeric"]')) {
          setupMFACodeInput(input);
        }
      });
      
      setupFormSubmitState(form);
    });
    
    const mfaInput = document.querySelector('input[name="code"]');
    if (mfaInput) setupMFACodeInput(mfaInput);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  const style = document.createElement('style');
  style.textContent = `
    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      20%, 60% { transform: translateX(-4px); }
      40%, 80% { transform: translateX(4px); }
    }
    
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.02); }
    }
    
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .field-error {
      animation: fadeIn 0.2s ease;
    }
    
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
      }
    }
    
    .form-group {
      position: relative;
    }
    
    input:focus {
      outline: none;
    }
    
    .password-toggle:focus {
      outline: 2px solid currentColor;
      outline-offset: 2px;
    }
  `;
  document.head.appendChild(style);
})();
