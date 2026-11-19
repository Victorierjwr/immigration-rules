/* immigration-rules web：cache-first（同源资源）。首次访问后离线可用。 */
const CACHE = "immigration-web-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(clients.claim()));

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || !e.request.url.startsWith(self.location.origin)) return;
  e.respondWith(
    caches.open(CACHE).then(async cache => {
      const hit = await cache.match(e.request);
      if (hit) return hit;
      const resp = await fetch(e.request);
      if (resp.ok) cache.put(e.request, resp.clone());
      return resp;
    }).catch(() => caches.match(e.request))
  );
});
