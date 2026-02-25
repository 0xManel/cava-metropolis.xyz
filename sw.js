const SW_BUILD = '2026-02-25-admin-report-v1';
const CACHE = `stock-cava-${SW_BUILD}`;
const ASSETS = ['/', '/index.html', '/login.html', '/admin.html', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches
      .keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', e => {
  if (e?.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') {
    return;
  }

  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  const isNavigation = e.request.mode === 'navigate';
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/data/')) {
    e.respondWith(fetch(e.request, { cache: 'no-store' }));
    return;
  }

  e.respondWith(
    fetch(e.request, isNavigation ? { cache: 'no-store' } : undefined)
      .then(r => {
        const clone = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return r;
      })
      .catch(async () => {
        const cached = await caches.match(e.request);
        if (cached) return cached;
        if (isNavigation) {
          return (await caches.match('/login.html')) || (await caches.match('/index.html')) || Response.error();
        }
        return Response.error();
      })
  );
});
