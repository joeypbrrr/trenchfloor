// Retires the old root service worker from when the live app lived at /trenchfloor/.
// The live floor now registers its own worker under /trenchfloor/floor/.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(
  caches.delete('trenchfloor-shell-v1').catch(() => {}).then(() => self.registration.unregister())
));
