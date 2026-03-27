/* ============================================================
   InvoiceFlow — Enhanced UI Interactions v5.0
   Production-grade micro-interactions and animations
   ============================================================ */
'use strict';

/* ── Bootstrap ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initRippleButtons();
  initScrollReveal();
  initCounterAnimations();
  initToastSystem();
  initScrollTop();
  initTableRowLinks();
  initBellAnimation();
  initQuickActionHover();
  initKeyboardShortcuts();
  initFormEnhancements();
  initPageHeader();
  initCopyButtons();
  initConfirmForms();
  initProgressBars();
});

/* ── Page header entrance ────────────────────────────────── */
function initPageHeader() {
  const headers = document.querySelectorAll('.page-header, [style*="justify-content:space-between"][style*="margin-bottom"]');
  headers.forEach((el, i) => {
    if (!el.classList.contains('page-header')) {
      el.style.animation = `fadeInDown 460ms cubic-bezier(.4,0,.2,1) ${i * 40}ms both`;
    }
  });
}

/* ── Ripple on buttons ───────────────────────────────────── */
function initRippleButtons() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-primary, .btn-success, .btn-danger');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top  - size / 2;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    Object.assign(ripple.style, {
      width: size + 'px', height: size + 'px',
      left: x + 'px', top: y + 'px',
    });
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  });
}

/* ── Scroll Reveal (IntersectionObserver) ────────────────── */
function initScrollReveal() {
  if (!('IntersectionObserver' in window)) {
    document.querySelectorAll('.reveal,.reveal-left').forEach(el => {
      el.classList.add('visible');
    });
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 60);
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });

  document.querySelectorAll('.reveal,.reveal-left').forEach(el => io.observe(el));
}

/* ── Counter animations ──────────────────────────────────── */
function initCounterAnimations() {
  if (!('IntersectionObserver' in window)) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounterEl(entry.target);
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.kpi-value').forEach(el => {
    const raw = el.textContent.trim();
    const num = parseFloat(raw.replace(/[^0-9.-]/g, ''));
    if (!isNaN(num) && num > 0) {
      el.dataset.target = num;
      el.dataset.prefix = raw.replace(/[\d,.]+.*$/, '').trim();
      el.dataset.suffix = raw.replace(/^[^0-9-]*[\d,.]+/, '').trim();
      el.dataset.decimals = (raw.split('.')[1] || '').replace(/[^0-9]/g, '').length;
      io.observe(el);
    }
  });
}

function animateCounterEl(el) {
  const target   = parseFloat(el.dataset.target);
  const prefix   = el.dataset.prefix || '';
  const suffix   = el.dataset.suffix || '';
  const decimals = parseInt(el.dataset.decimals) || 0;
  const duration = Math.min(1200, Math.max(600, target / 50));
  const start    = performance.now();

  function easeOut(t) { return 1 - Math.pow(1 - t, 3) }

  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const val = easeOut(progress) * target;
    el.textContent = prefix + formatNum(val, decimals) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = prefix + formatNum(target, decimals) + suffix;
  }
  requestAnimationFrame(tick);
}

function formatNum(n, decimals) {
  return n.toLocaleString('en', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/* ── Toast system ────────────────────────────────────────── */
function initToastSystem() {
  // Process Django messages
  document.querySelectorAll('[data-msg]').forEach(el => {
    const tags = el.dataset.msg || '';
    const text = el.textContent.trim();
    if (!text) return;
    let type = 'info';
    if (tags.includes('success')) type = 'success';
    else if (tags.includes('error') || tags.includes('danger')) type = 'error';
    else if (tags.includes('warning')) type = 'warning';
    setTimeout(() => showToast(text, type), 300);
  });
  // Expose globally
  window.showToast = showToast;
}

function showToast(message, type = 'info', title = '') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: `<svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>`,
    error:   `<svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`,
    warning: `<svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`,
    info:    `<svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${icons[type] || icons.info}</div>
    <div class="toast-content">
      ${title ? `<p class="toast-title">${title}</p>` : ''}
      <p class="toast-msg">${message}</p>
    </div>
    <button class="toast-close" aria-label="Close">×</button>
    <div class="toast-bar"></div>
  `;

  container.appendChild(toast);
  toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));

  const timer = setTimeout(() => dismissToast(toast), 4400);
  toast.addEventListener('mouseenter', () => clearTimeout(timer));
}

function dismissToast(toast) {
  toast.classList.add('exit');
  toast.addEventListener('animationend', () => toast.remove());
}

/* ── Scroll-to-top button ────────────────────────────────── */
function initScrollTop() {
  const btn = document.createElement('button');
  btn.id = 'scroll-top-btn';
  btn.setAttribute('aria-label', 'Scroll to top');
  btn.innerHTML = `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>`;
  document.body.appendChild(btn);

  const scrollEl = document.querySelector('.main') || window;
  const getScroll = () => scrollEl === window ? window.scrollY : scrollEl.scrollTop;

  function onScroll() {
    btn.classList.toggle('visible', getScroll() > 320);
  }
  scrollEl.addEventListener('scroll', onScroll, { passive: true });
  btn.addEventListener('click', () => {
    scrollEl === window
      ? window.scrollTo({ top: 0, behavior: 'smooth' })
      : scrollEl.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ── Clickable table rows ────────────────────────────────── */
function initTableRowLinks() {
  document.addEventListener('click', (e) => {
    const row = e.target.closest('tr[data-href]');
    if (!row) return;
    const tag = e.target.tagName;
    if (['A','BUTTON','INPUT','FORM','SELECT','TEXTAREA'].includes(tag)) return;
    if (e.target.closest('a, button, form')) return;
    window.location.href = row.dataset.href;
  });
}

/* ── Bell animation ──────────────────────────────────────── */
function initBellAnimation() {
  const bell = document.querySelector('[data-bell]');
  if (!bell) return;
  setInterval(() => {
    const dot = bell.querySelector('.n-dot');
    if (dot) bell.querySelector('svg')?.animate(
      [{ transform:'rotate(0)' },{transform:'rotate(18deg)'},{transform:'rotate(-12deg)'},{transform:'rotate(6deg)'},{transform:'rotate(0)'}],
      { duration: 700, easing: 'ease-in-out' }
    );
  }, 6000);
}

/* ── Quick action hover ──────────────────────────────────── */
function initQuickActionHover() {
  document.querySelectorAll('.quick-action-btn').forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      btn.style.paddingLeft = '20px';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.paddingLeft = '';
    });
  });
}

/* ── Keyboard shortcuts ──────────────────────────────────── */
function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      document.querySelector('.search-trigger')?.click();
    }
    // Escape closes any open modal backdrop
    if (e.key === 'Escape') {
      document.querySelectorAll('[x-data]').forEach(el => {
        if (el.__x) {
          const data = el.__x.$data;
          Object.keys(data).forEach(k => {
            if (k.endsWith('Modal') || k === 'open') data[k] = false;
          });
        }
      });
    }
  });
}

/* ── Form enhancements ───────────────────────────────────── */
function initFormEnhancements() {
  // Auto-focus first input in a form card
  const firstInput = document.querySelector('.card form input:not([type=hidden]):not([readonly]):not([disabled])');
  // Don't auto-focus — it can be disruptive on pages with multiple inputs

  // Validate required fields on submit
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', (e) => {
      let valid = true;
      form.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) {
          field.style.borderColor = '#dc2626';
          field.style.boxShadow = '0 0 0 3px rgba(220,38,38,.15)';
          valid = false;
          field.addEventListener('input', () => {
            field.style.borderColor = '';
            field.style.boxShadow = '';
          }, { once: true });
        }
      });
      if (!valid) e.preventDefault();
    });
  });

  // Loading state on form submit buttons
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('[type=submit]');
      if (btn && !btn.dataset.noLoading) {
        btn.disabled = true;
        const original = btn.innerHTML;
        btn.innerHTML = `<span class="spinner" style="width:14px;height:14px;border-width:2px"></span> Saving…`;
        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = original;
        }, 8000);
      }
    });
  });
}

/* ── Copy buttons ────────────────────────────────────────── */
function initCopyButtons() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy]');
    if (!btn) return;
    const text = btn.dataset.copy;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      const original = btn.innerHTML;
      btn.innerHTML = `<svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg> Copied!`;
      btn.style.color = '#16a34a';
      setTimeout(() => {
        btn.innerHTML = original;
        btn.style.color = '';
      }, 2000);
    }).catch(() => {});
  });

  // Also handle the inline copy pattern (input + button)
  document.querySelectorAll('button[onclick*="clipboard"]').forEach(btn => {
    btn.removeAttribute('onclick');
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (input) {
        navigator.clipboard.writeText(input.value).then(() => {
          const orig = btn.textContent;
          btn.textContent = '✓ Copied';
          btn.style.color = '#16a34a';
          setTimeout(() => {
            btn.textContent = orig;
            btn.style.color = '';
          }, 2000);
        });
      }
    });
  });
}

/* ── Confirm dangerous actions ───────────────────────────── */
function initConfirmForms() {
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', (e) => {
      if (!confirm(form.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });
}

/* ── Animated progress bars ──────────────────────────────── */
function initProgressBars() {
  if (!('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target;
        const width = fill.dataset.width || fill.style.width;
        fill.style.width = '0';
        setTimeout(() => { fill.style.width = width; }, 100);
        io.unobserve(fill);
      }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.progress-fill[data-width]').forEach(el => io.observe(el));
}

/* ── Global app helpers ──────────────────────────────────── */
window.invoiceFlow = {
  toast: (msg, type) => showToast(msg, type),
  copyText: (text) => navigator.clipboard.writeText(text),
};
