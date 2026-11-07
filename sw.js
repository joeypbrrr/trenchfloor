// Trenchfloor no longer uses a service worker, so a stale copy is never served.
// Any browser that still has an old worker installs this one, which clears the
// old Trenchfloor cache and unregisters itself.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(
  caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith('trenchfloor-shell')).map((k) => caches.delete(k))))
    .catch(() => {})
    .then(() => self.registration.unregister())
));
