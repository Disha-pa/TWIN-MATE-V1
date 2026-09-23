// Kill any old service worker so it cannot break login.
self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))).then(() => {
            return self.registration.unregister();
        })
    );
});
