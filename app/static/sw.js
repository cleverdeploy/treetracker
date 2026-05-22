// Minimal service worker — caches the app shell for offline read-only use.
const CACHE = 'treetracker-v1';
const SHELL = ['/', '/static/app.css', '/static/map.js', '/static/icons/leaf.svg'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Never cache POST/PATCH or auth or photos.
  if (e.request.method !== 'GET') return;
  if (url.pathname.startsWith('/auth') || url.pathname.startsWith('/api/sightings')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res.ok && url.origin === location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
