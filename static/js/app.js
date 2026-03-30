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

/* ── DOMContentLoaded helpers ── */
document.addEventListener('DOMContentLoaded', () => {
  /* Confirm-delete on links/buttons (not forms — those are handled by app-enhanced.js) */
  document.querySelectorAll('a[data-confirm], button[data-confirm]:not(form button)').forEach(el => {
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
    selectedIndex: -1,
    _debounceTimer: null,

    doSearch() {
      this.selectedIndex = -1;
      if (this._debounceTimer) clearTimeout(this._debounceTimer);
      if (this.query.length < 2) { this.results = []; this.loading = false; return; }
      this.loading = true;
      this._debounceTimer = setTimeout(async () => {
        try {
          const resp = await fetch(`/api/search/?q=${encodeURIComponent(this.query)}`);
          const data = await resp.json();
          this.results = data.results || [];
        } catch(e) { this.results = []; }
        this.loading = false;
      }, 300);
    },

    handleKey(e) {
      if (!this.results.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
        this._scrollToSelected();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
        this._scrollToSelected();
      } else if (e.key === 'Enter' && this.selectedIndex >= 0) {
        e.preventDefault();
        const item = this.results[this.selectedIndex];
        if (item && item.url) window.location.href = item.url;
      } else if (e.key === 'Escape') {
        this.open = false;
        this.query = '';
        this.results = [];
        this.selectedIndex = -1;
      }
    },

    _scrollToSelected() {
      this.$nextTick(() => {
        const el = this.$el.querySelector(`[data-idx="${this.selectedIndex}"]`);
        if (el) el.scrollIntoView({ block: 'nearest' });
      });
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

/* ── Navigation keyboard shortcuts (g + key, like Gmail) ── */
(function() {
  let gPressed = false;
  let gTimer = null;

  const ROUTES = {
    'i': '/invoices/',
    'c': '/clients/',
    'e': '/expenses/',
    'd': '/dashboard/',
    'p': '/payments/',
    'x': '/estimates/',
    'r': '/reports/',
    'w': '/wallet/',
    's': '/settings/',
    'u': '/recurring/',
  };

  function isEditing() {
    const el = document.activeElement;
    return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
  }

  document.addEventListener('keydown', e => {
    if (isEditing()) { gPressed = false; return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    if (gPressed) {
      clearTimeout(gTimer);
      gPressed = false;
      const route = ROUTES[e.key.toLowerCase()];
      if (route) {
        e.preventDefault();
        window.location.href = route;
      }
      return;
    }

    // g prefix
    if (e.key === 'g') {
      gPressed = true;
      gTimer = setTimeout(() => { gPressed = false; }, 1000);
      return;
    }

    // ? = show shortcuts panel
    if (e.key === '?') {
      const panel = document.getElementById('shortcuts-panel');
      if (panel) {
        e.preventDefault();
        panel.style.display = panel.style.display === 'flex' ? 'none' : 'flex';
      }
    }

    // n = new invoice (from anywhere)
    if (e.key === 'n' && !e.shiftKey) {
      if (window.location.pathname === '/invoices/') {
        const btn = document.querySelector('a[href*="invoice/create"]');
        if (btn) { e.preventDefault(); window.location.href = btn.href; }
      }
    }
  });
})();

/* ── CSRF token helper ── */
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
    || '';
}

/* ── Mark notification read ── */
function markNotifRead(id, el) {
  if (el.dataset.read === '1') return;
  el.dataset.read = '1';
  fetch(`/notifications/mark-read/${id}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() }
  }).then(() => {
    // Remove blue dot on this item
    el.querySelectorAll('[data-notif-dot]').forEach(d => d.remove());
    el.style.background = 'transparent';
    const title = el.querySelector('p');
    if (title) title.style.fontWeight = '500';
    // Decrement badge counter
    const badge = document.querySelector('[data-notif-badge]');
    if (badge) {
      const count = parseInt(badge.textContent, 10) - 1;
      if (count <= 0) {
        badge.remove();
        // Remove bell dot if no more unread
        document.querySelectorAll('.n-dot').forEach(d => d.remove());
        // Hide "Mark all read" button
        const markAllBtn = document.querySelector('[data-mark-all-btn]');
        if (markAllBtn) markAllBtn.style.display = 'none';
      } else {
        badge.textContent = count;
      }
    }
  }).catch(() => { delete el.dataset.read; });
}

/* ── Mark all notifications read ── */
function markAllNotifsRead(btn) {
  fetch('/notifications/mark-all-read/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() }
  }).then(r => r.json()).then(() => {
    btn.style.display = 'none';
    document.querySelectorAll('[data-notif-dot]').forEach(d => d.remove());
    document.querySelectorAll('.n-dot').forEach(d => d.remove());
    const badge = document.querySelector('[data-notif-badge]');
    if (badge) badge.remove();
    // Reset all item backgrounds
    document.querySelectorAll('[data-notif-item]').forEach(el => {
      el.style.background = 'transparent';
      const title = el.querySelector('p');
      if (title) title.style.fontWeight = '500';
      el.dataset.read = '1';
    });
  }).catch(() => {});
}

/* ── Spin animation (used by search loader) ── */
if (!document.querySelector('#spin-keyframes')) {
  const s = document.createElement('style');
  s.id = 'spin-keyframes';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg) } }';
  document.head.appendChild(s);
}

/* ── Clickable table rows via data-href ─────────────────────
   Any <tr data-href="/some/url"> becomes a navigable row.
   Clicks on <a>, <button>, or cells with onclick are ignored.
──────────────────────────────────────────────────────────── */
(function initClickableRows() {
  function bind(root) {
    root.querySelectorAll('tr[data-href]').forEach(row => {
      if (row._clickBound) return;
      row._clickBound = true;
      row.style.cursor = 'pointer';
      row.addEventListener('click', function(e) {
        if (e.target.closest('a, button, [onclick], input, select, textarea')) return;
        const href = row.dataset.href;
        if (href) {
          if (e.metaKey || e.ctrlKey) {
            window.open(href, '_blank');
          } else {
            window.location.href = href;
          }
        }
      });
      row.addEventListener('mouseenter', function() {
        row.style.background = 'var(--bg-hover)';
      });
      row.addEventListener('mouseleave', function() {
        row.style.background = '';
      });
    });
  }

  // Bind on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => bind(document));
  } else {
    bind(document);
  }

  // Re-bind if content is dynamically added (Alpine.js mutations)
  if (window.MutationObserver) {
    new MutationObserver(mutations => {
      mutations.forEach(m => m.addedNodes.forEach(node => {
        if (node.nodeType === 1) bind(node.tagName === 'TR' ? node.parentElement || node : node);
      }));
    }).observe(document.body, { childList: true, subtree: true });
  }
})();
