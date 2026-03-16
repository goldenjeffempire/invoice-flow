/* InvoiceFlow App Shell v3.0 */
'use strict';

/* ── Alpine app shell component ── */
function appShell() {
  return {
    dark: false,
    col: false,
    mob: false,
    srch: false,
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
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); this.srch = true }
        if (e.key === 'Escape') { this.srch = false; this.mob = false; this.notifOpen = false; this.userOpen = false; this.wsOpen = false }
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

/* ── Global search ── */
function searchPalette() {
  return {
    q: '',
    results: [],
    loading: false,
    selected: -1,
    timer: null,

    async search() {
      if (!this.q.trim() || this.q.length < 2) { this.results = []; return }
      this.loading = true;
      clearTimeout(this.timer);
      this.timer = setTimeout(async () => {
        try {
          const r = await fetch(`/api/search/?q=${encodeURIComponent(this.q)}`);
          const d = await r.json();
          this.results = d.results || [];
        } catch { this.results = [] }
        this.loading = false;
      }, 220);
    },

    navigate(dir) {
      const max = this.results.length - 1;
      if (dir === 'up') this.selected = Math.max(0, this.selected - 1);
      else this.selected = Math.min(max, this.selected + 1);
    },

    select() {
      if (this.selected >= 0 && this.results[this.selected]) {
        window.location = this.results[this.selected].url;
      }
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

/* ── Invoice builder ── */
function invoiceBuilder(opts = {}) {
  return {
    items: opts.items || [],
    currency: opts.currency || 'NGN',
    taxMode: opts.taxMode || 'exclusive',
    defaultTaxRate: parseFloat(opts.defaultTaxRate || 0),
    discountType: opts.discountType || 'flat',
    globalDiscount: parseFloat(opts.globalDiscount || 0),

    addItem() {
      this.items.push({ id: Date.now(), description: '', quantity: 1, unit_price: 0, tax_rate: this.defaultTaxRate, discount_type: 'flat', discount_value: 0 });
    },

    removeItem(idx) {
      this.items.splice(idx, 1);
    },

    itemSubtotal(item) {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.unit_price) || 0;
      const dv = parseFloat(item.discount_value) || 0;
      const gross = qty * price;
      const disc = item.discount_type === 'percentage' ? gross * dv / 100 : dv;
      return Math.max(0, gross - disc);
    },

    get subtotal() { return this.items.reduce((s, i) => s + this.itemSubtotal(i), 0) },

    get discountAmount() {
      if (this.discountType === 'percentage') return this.subtotal * this.globalDiscount / 100;
      return Math.min(this.globalDiscount, this.subtotal);
    },

    get taxBase() { return this.subtotal - this.discountAmount },

    get taxTotal() {
      return this.items.reduce((s, i) => {
        const base = this.itemSubtotal(i);
        const rate = parseFloat(i.tax_rate) || 0;
        return s + (base * rate / 100);
      }, 0);
    },

    get total() {
      const base = this.taxBase;
      return this.taxMode === 'exclusive' ? base + this.taxTotal : base;
    },

    fmt(n) { return fmt(n, this.currency) },

    get itemsJson() { return JSON.stringify(this.items) }
  }
}

/* ── Estimate builder (same as invoice builder) ── */
const estimateBuilder = invoiceBuilder;
