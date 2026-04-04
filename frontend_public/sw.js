// NEXO SOBERANO — Service Worker v1.0
const CACHE = 'nexo-v1';
const STATIC = [
  '/', '/omniglobe', '/flowmap', '/control-center',
  '/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // API calls: network first
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;
  // Static: cache first
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request).then(res => {
        if (res.ok) caches.open(CACHE).then(c => c.put(e.request, res.clone()));
        return res;
      });
      return cached || network;
    })
  );
});

// Push notifications for globe alerts
self.addEventListener('push', e => {
  const data = e.data?.json() || {};
  e.waitUntil(self.registration.showNotification(
    data.title || 'NEXO INTEL',
    {
      body: data.body || 'Nuevo evento de inteligencia',
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/badge-72.png',
      tag: 'nexo-alert',
      data: { url: data.url || '/omniglobe' },
      actions: [
        { action: 'view', title: 'Ver en Globo' },
        { action: 'dismiss', title: 'Ignorar' },
      ]
    }
  ));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action !== 'dismiss') {
    e.waitUntil(clients.openWindow(e.notification.data?.url || '/omniglobe'));
  }
});
