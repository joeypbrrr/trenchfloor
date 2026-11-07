const CACHE = "trenchfloor-shell-v1";
const ROOT = new URL("./", self.location).pathname;
const SHELL = [ROOT, ROOT + "style.css", ROOT + "app.js", ROOT + "scene.js", ROOT + "three.min.js", ROOT + "manifest.webmanifest", ROOT + "icons/icon-192.png"];
self.addEventListener("install", (event) => event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL))));
self.addEventListener("activate", (event) => event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))));
self.addEventListener("fetch", (event) => {
  if (new URL(event.request.url).pathname.includes("/data/")) return;
  event.respondWith(fetch(event.request).then((res) => {
    const copy = res.clone();
    caches.open(CACHE).then((cache) => cache.put(event.request, copy));
    return res;
  }).catch(() => caches.match(event.request)));
});
