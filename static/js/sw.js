/**
 * InvoiceFlow Service Worker
 * Offline support and caching strategies
 */

const CACHE_VERSION = 'v2.0.0';
const STATIC_CACHE = `invoiceflow-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `invoiceflow-dynamic-${CACHE_VERSION}`;
const IMAGE_CACHE = `invoiceflow-images-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/offline/',
  '/static/css/critical.css',
  '/static/css/main.css',
  '/static/css/design-tokens.css',
  '/static/js/app.js',
  '/static/favicon.svg'
];

const CACHE_STRATEGIES = {
  cacheFirst: async (request, cacheName) => {
    const cached = await caches.match(request);
    if (cached) return cached;
    
    try {
      const response = await fetch(request);
      if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
      return response;
    } catch {
      return new Response('Offline', { status: 503 });
    }
  },

  networkFirst: async (request, cacheName) => {
    try {
      const response = await fetch(request);
      if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
      return response;
    } catch {
      const cached = await caches.match(request);
      return cached || caches.match('/offline/');
    }
  },

  staleWhileRevalidate: async (request, cacheName) => {
    const cached = await caches.match(request);
    
    const fetchPromise = fetch(request).then(response => {
      if (response.ok) {
        caches.open(cacheName).then(cache => {
          cache.put(request, response.clone());
        });
      }
      return response;
    }).catch(() => cached);

    return cached || fetchPromise;
  }
};

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => {
          return key.startsWith('invoiceflow-') && 
                 key !== STATIC_CACHE && 
                 key !== DYNAMIC_CACHE && 
                 key !== IMAGE_CACHE;
        }).map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  if (url.origin !== location.origin) return;

  if (url.pathname.startsWith('/static/')) {
    if (url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/)) {
      event.respondWith(CACHE_STRATEGIES.cacheFirst(request, IMAGE_CACHE));
    } else {
      event.respondWith(CACHE_STRATEGIES.cacheFirst(request, STATIC_CACHE));
    }
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(CACHE_STRATEGIES.networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  if (request.headers.get('Accept')?.includes('text/html')) {
    event.respondWith(CACHE_STRATEGIES.networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  event.respondWith(CACHE_STRATEGIES.staleWhileRevalidate(request, DYNAMIC_CACHE));
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data?.type === 'CACHE_URLS') {
    const urls = event.data.urls;
    caches.open(DYNAMIC_CACHE).then(cache => {
      cache.addAll(urls);
    });
  }
});

self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  
  const options = {
    body: data.body || 'You have a new notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      dateOfArrival: Date.now()
    },
    actions: data.actions || [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'InvoiceFlow', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-invoices') {
    event.waitUntil(syncInvoices());
  }
});

async function syncInvoices() {
  const cache = await caches.open('invoiceflow-pending');
  const requests = await cache.keys();
  
  for (const request of requests) {
    try {
      const response = await fetch(request.clone());
      if (response.ok) {
        await cache.delete(request);
      }
    } catch (error) {
      // Sync failed
    }
  }
}
