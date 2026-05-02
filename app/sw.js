// Service worker for the Wildhaven AI Homes device-side PWA.
//
// Cache-first for static shell so the app launches offline; network-first
// for /chat (and any other dynamic API call) so live brainstem responses
// are never stale-served from cache.

const CACHE_VERSION = 'wah-twin-app/v1';
const SHELL_PATHS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.svg',
  './icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL_PATHS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Network-first for /chat and any /api/ call: live data, never cached.
  const isDynamic = (
    url.pathname.endsWith('/chat') ||
    url.pathname.includes('/api/') ||
    url.protocol === 'http:' && url.hostname === 'localhost'
  );
  if (isDynamic) {
    event.respondWith(fetch(event.request).catch(() => new Response(
      JSON.stringify({error: 'offline; local brainstem unreachable'}),
      {headers: {'Content-Type': 'application/json'}, status: 503}
    )));
    return;
  }

  // Cache-first for static shell.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((resp) => {
        // Optionally cache new same-origin GET responses
        if (event.request.method === 'GET' && url.origin === self.location.origin && resp && resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(event.request, clone));
        }
        return resp;
      }).catch(() => cached || Response.error());
    })
  );
});
