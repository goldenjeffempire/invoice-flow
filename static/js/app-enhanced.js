/* InvoiceFlow — Enhanced UI Interactions v4.0 */
'use strict';

/* ── Initialization ────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initRippleButtons();
  initScrollReveal();
  initCounterAnimations();
  initToastSystem();
  initScrollTop();
  initBellAnimation();
  initKPICards();
  initTableRowLinks();
  initQuickActions();
  initPageTransition();
  initSearchShortcut();
});

/* ── Page Transition ─────────────────────────────────────── */
function initPageTransition() {
  document.querySelectorAll('a').forEach(a => {
    if (a.href && !a.href.includes('#') && !a.target && a.origin === location.origin && !a.hasAttribute('download') && !a.dataset.noTransition) {
      a.addEventListener('click', e => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        const content = document.querySelector('.content');
        if (content) {
          e.preventDefault();
          content.style.transition = 'opacity 180ms ease, transform 180ms ease';
          content.style.opacity = '0';
          content.style.transform = 'translateY(6px)';
          setTimeout(() => { window.location.href = a.href; }, 180);
        }
      });
    }
  });
}

/* ── Ripple Effect ───────────────────────────────────────── */
function initRippleButtons() {
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const rect = this.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const size = Math.max(rect.width, rect.height) * 2;
      const ripple = document.createElement('span');
      ripple.classList.add('ripple');
      ripple.style.cssText = `width:${size}px;height:${size}px;left:${x - size/2}px;top:${y - size/2}px`;
      this.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
}

/* ── Scroll Reveal ───────────────────────────────────────── */
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.classList.add('revealed');
        }, entry.target.dataset.delay || 0);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.06, rootMargin: '0px 0px -30px 0px' });

  document.querySelectorAll('.reveal, .reveal-left').forEach(el => observer.observe(el));
}

/* ── Counter Animations ──────────────────────────────────── */
function initCounterAnimations() {
  const counters = document.querySelectorAll('[data-counter]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  counters.forEach(el => observer.observe(el));
}

function animateCounter(el) {
  const target = parseFloat(el.dataset.counter);
  const prefix = el.dataset.prefix || '';
  const suffix = el.dataset.suffix || '';
  const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
  const duration = 1000;
  const start = performance.now();

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = target * eased;
    el.textContent = prefix + current.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

/* ── KPI Card Enhancements ───────────────────────────────── */
function initKPICards() {
  document.querySelectorAll('.kpi-card').forEach((card, i) => {
    card.style.animationDelay = `${i * 60}ms`;
    card.style.animation = 'fadeInUp 350ms cubic-bezier(0,0,.2,1) both';
    card.style.animationDelay = `${i * 60}ms`;
  });
}

/* ── Toast System ────────────────────────────────────────── */
function initToastSystem() {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  /* Parse existing Django messages */
  document.querySelectorAll('[data-msg]').forEach(el => {
    const level = el.dataset.msg || 'info';
    const msg = el.textContent.trim();
    if (msg) showToast(msg, level.includes('error') ? 'error' : level.includes('warning') ? 'warning' : level.includes('success') ? 'success' : 'info');
    el.remove();
  });

  window.showToast = showToast;
}

function showToast(message, type = 'info', duration = 5000) {
  const container = document.querySelector('.toast-container');
  if (!container) return;

  const icons = {
    success: `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
    error:   `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
    warning: `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`,
    info:    `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span style="flex-shrink:0;margin-top:1px">${icons[type] || icons.info}</span>
    <span style="flex:1;line-height:1.5">${message}</span>
    <button class="toast-close" onclick="removeToast(this.parentElement)">×</button>
    <div class="toast-progress" style="width:100%"></div>
  `;
  container.appendChild(toast);

  const bar = toast.querySelector('.toast-progress');
  const start = performance.now();
  function tick(now) {
    const pct = Math.max(0, 1 - (now - start) / duration);
    if (bar) bar.style.width = (pct * 100) + '%';
    if (pct > 0) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  const timer = setTimeout(() => removeToast(toast), duration);
  toast._timer = timer;
}

window.removeToast = function(toast) {
  if (!toast || toast._removing) return;
  toast._removing = true;
  clearTimeout(toast._timer);
  toast.classList.add('removing');
  setTimeout(() => toast.remove(), 260);
};

/* ── Scroll-to-Top ───────────────────────────────────────── */
function initScrollTop() {
  const content = document.querySelector('.content');
  if (!content) return;

  const btn = document.createElement('button');
  btn.className = 'scroll-top';
  btn.setAttribute('aria-label', 'Scroll to top');
  btn.innerHTML = `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>`;
  document.body.appendChild(btn);

  content.addEventListener('scroll', () => {
    btn.classList.toggle('visible', content.scrollTop > 400);
  });
  btn.addEventListener('click', () => {
    content.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ── Bell Notification Animation ────────────────────────── */
function initBellAnimation() {
  const bellBtn = document.querySelector('[data-bell]');
  if (!bellBtn) return;
  const dot = bellBtn.querySelector('.n-dot');
  if (!dot) return;

  let hasRung = false;
  setTimeout(() => {
    if (!hasRung) {
      bellBtn.querySelector('svg')?.classList.add('bell-ring');
      hasRung = true;
    }
  }, 1200);
}

/* ── Table Row Clickability ──────────────────────────────── */
function initTableRowLinks() {
  document.querySelectorAll('.tbl tbody tr[data-href]').forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', e => {
      if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || e.target.closest('a,button')) return;
      window.location.href = row.dataset.href;
    });
  });
}

/* ── Quick Actions Hover ─────────────────────────────────── */
function initQuickActions() {
  document.querySelectorAll('.quick-action-btn').forEach(btn => {
    btn.addEventListener('mouseenter', function() {
      this.style.transform = 'translateX(3px)';
    });
    btn.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });
  });
}

/* ── CMD+K Search Shortcut ───────────────────────────────── */
function initSearchShortcut() {
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const searchTrigger = document.querySelector('.search-trigger');
      if (searchTrigger) searchTrigger.click();
    }
  });
}

/* ── Utility: Stagger animate elements ───────────────────── */
window.staggerAnimate = function(selector, cls = 'anim-fade-up', stagger = 60) {
  document.querySelectorAll(selector).forEach((el, i) => {
    el.classList.add(cls);
    el.style.animationDelay = `${i * stagger}ms`;
  });
};

/* ── Number formatter ────────────────────────────────────── */
window.formatCurrency = function(val, symbol = '$', decimals = 2) {
  return symbol + parseFloat(val).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};
