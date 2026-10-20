// Coordinate Studio service worker: lets the app be installed on PCs and phones and open instantly.
// The server replaces __VERSION__ with a hash of the page, so every deploy gets a fresh cache.
const SHELL = "cs-shell-__VERSION__";
const LIBRARIES = "cs-libraries";
const SHELL_FILES = [
  "/",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png",
  "/icons/apple-touch-icon.png",
  "/icons/favicon-32.png",
];
// Versioned libraries and fonts never change, so they are served from the cache once downloaded.
const LIBRARY_HOSTS = ["cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== LIBRARIES).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function fromCacheOrNetwork(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || response.type === "opaque") {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return; // calculations (POST /api/compute) always go to the server
  const url = new URL(request.url);

  if (request.mode === "navigate") {
    // Newest page when online; the saved copy when offline.
    event.respondWith(fetch(request).catch(() => caches.match("/")));
  } else if (url.origin === self.location.origin && !url.pathname.startsWith("/api/")) {
    event.respondWith(fromCacheOrNetwork(request, SHELL));
  } else if (LIBRARY_HOSTS.includes(url.hostname)) {
    event.respondWith(fromCacheOrNetwork(request, LIBRARIES));
  }
});
