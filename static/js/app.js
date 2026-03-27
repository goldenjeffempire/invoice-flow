/* InvoiceFlow App Shell v3.0 */
'use strict';

/* ── Alpine app shell component ── */
function appShell() {
  return {
    dark: false,
    col: false,
    mob: false,
    notifOpen: false,
    userOpen: false,
    wsOpen: false,

    boot() {
      // Theme
      const saved = localStorage.getItem('theme');
      this.dark = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.classList.toggle('dark', this.dark);

      // Sidebar collapsed state
      this.col = localStorage.getItem('sb_col') === '1';

      // Keyboard shortcuts
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
          this.mob = false;
          this.notifOpen = false;
          this.userOpen = false;
          this.wsOpen = false;
        }
      });
    },

    toggleTheme() {
      this.dark = !this.dark;
      localStorage.setItem('theme', this.dark ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', this.dark);
    },

    toggleCol() {
      this.col = !this.col;
      localStorage.setItem('sb_col', this.col ? '1' : '0');
    },

    get sbClass() {
      return { 'collapsed': this.col, 'open': this.mob }
    },
    get mainClass() {
      return { 'collapsed': this.col }
    }
  }
}

/* ── Toast system ── */
const Toast = {
  container: null,

  show(msg, type = 'info', duration = 4000) {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-wrap';
      document.body.appendChild(this.container);
    }
    const t = document.createElement('div');
    const icons = {
      success: `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>`,
      error:   `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/></svg>`,
      info:    `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 16h-1v-4h-1m1-4h.01"/></svg>`,
    };
    t.className = `toast toast-${type}`;
    t.innerHTML = `${icons[type] || icons.info}<span style="flex:1">${msg}</span>`;
    this.container.appendChild(t);
    setTimeout(() => {
      t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; t.style.transition = 'all .2s';
      setTimeout(() => t.remove(), 220);
    }, duration);
  }
};

/* ── Auto-dismiss Django messages ── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-msg]').forEach(el => {
    const type = el.dataset.msg;
    const text = el.textContent.trim();
    if (text) Toast.show(text, type === 'error' ? 'error' : type === 'success' ? 'success' : 'info');
    el.remove();
  });

  /* Confirm-delete forms */
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });

  /* Auto-resize textareas */
  document.querySelectorAll('textarea[data-auto]').forEach(el => {
    const resize = () => { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' };
    el.addEventListener('input', resize);
    resize();
  });
});

/* ── Currency formatter ── */
function fmt(amount, currency = 'NGN') {
  const symbols = { NGN:'₦', USD:'$', EUR:'€', GBP:'£', GHS:'₵', ZAR:'R', KES:'KSh' };
  const sym = symbols[currency] || currency + ' ';
  const n = parseFloat(amount) || 0;
  return sym + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/* ── Global Search ── */
function globalSearch() {
  return {
    open: false,
    query: '',
    results: [],
    loading: false,

    async doSearch() {
      if (this.query.length < 2) { this.results = []; return; }
      this.loading = true;
      try {
        const resp = await fetch(`/api/search/?q=${encodeURIComponent(this.query)}`);
        const data = await resp.json();
        this.results = data.results || [];
      } catch(e) { this.results = []; }
      this.loading = false;
    },

    iconClass(type) {
      const map = { invoice: 'si-indigo', client: 'si-green', expense: 'si-amber', estimate: 'si-violet' };
      return `stat-icon ${map[type] || 'si-blue'}`;
    }
  }
}

/* ── Global keyboard shortcut: Cmd/Ctrl+K opens search ── */
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const searchEl = document.querySelector('[x-data*="globalSearch"]');
    if (searchEl && searchEl._x_dataStack) {
      const comp = searchEl._x_dataStack[0];
      if (comp) { comp.open = true; setTimeout(() => { const inp = searchEl.querySelector('input'); if (inp) inp.focus(); }, 50); }
    }
  }
});

/* ── CSRF token helper ── */
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
    || '';
}

/* ── Mark notification read ── */
function markNotifRead(id, el) {
  fetch(`/notifications/mark-read/${id}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() }
  }).then(() => {
    const dot = el.querySelector('[style*="background:#6366f1"][style*="border-radius:50%"]');
    if (dot) dot.remove();
    el.style.background = 'transparent';
    const title = el.querySelector('p');
    if (title) title.style.fontWeight = '500';
  }).catch(() => {});
}

/* ── Spin animation (used by search loader) ── */
if (!document.querySelector('#spin-keyframes')) {
  const s = document.createElement('style');
  s.id = 'spin-keyframes';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg) } }';
  document.head.appendChild(s);
}
