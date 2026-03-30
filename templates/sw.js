{% load static %}
const CACHE_VERSION = 'invoiceflow-v3';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;

const PRECACHE_ASSETS = [
  '/static/css/app.css',
  '/static/css/app-enhanced.css',
  '/static/css/design-system.css',
  '/static/css/tailwind.css',
  '/static/js/app.js',
  '/static/js/app-enhanced.js',
  '/static/manifest.json',
];

const NETWORK_FIRST_PATTERNS = [
  /\/api\//,
  /\/dashboard/,
  /\/invoices\//,
  /\/clients\//,
  /\/payments\//,
  /\/expenses\//,
  /\/reports\//,
];

const CACHE_FIRST_PATTERNS = [
  /\/static\//,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/,
  /cdn\.jsdelivr\.net/,
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== STATIC_CACHE && k !== DYNAMIC_CACHE)
            .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;
  if (url.protocol === 'chrome-extension:') return;
  if (url.origin !== location.origin && !CACHE_FIRST_PATTERNS.some(p => p.test(url.href))) return;

  const isCacheFirst = CACHE_FIRST_PATTERNS.some(p => p.test(url.href));
  const isNetworkFirst = NETWORK_FIRST_PATTERNS.some(p => p.test(url.pathname));

  if (isCacheFirst) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then(c => c.put(request, clone));
          }
          return response;
        }).catch(() => cached);
      })
    );
    return;
  }

  if (isNetworkFirst) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(DYNAMIC_CACHE).then(c => c.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
