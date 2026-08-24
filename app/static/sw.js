const CACHE_NAME = "cny-fx-mobile-v0.3.0-r1";
const APP_SHELL = [
  "./",
  "./static/styles.css?v=0.3.0-r1",
  "./static/app.js?v=0.3.0-r1",
  "./static/manifest.webmanifest?v=0.3.0-r1",
  "./static/icons/app-192.png",
  "./static/icons/app-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then((response) => response || caches.match("./"))),
    );
    return;
  }

  if (url.pathname.includes("/api/") || url.pathname.endsWith("/health")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(event.request).then(
            (response) =>
              response ||
              new Response(JSON.stringify({ detail: "离线状态下暂无缓存数据" }), {
                status: 503,
                headers: { "Content-Type": "application/json" },
              }),
          ),
        ),
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        }),
    ),
  );
});
