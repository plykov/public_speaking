// Service worker for installability + real Web Push delivery (§4.2).
//
// No offline caching strategy is implemented — that's a separate
// concern from what this feature needed (installability + push). The
// fetch handler below is a plain passthrough, present because some
// browsers' install-eligibility checks still look for one.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});

self.addEventListener("push", (event) => {
  let payload = { title: "Cadence", body: "You have a new notification." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch {
      payload = { title: "Cadence", body: event.data.text() };
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title || "Cadence", {
      body: payload.body || "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow("/");
    }),
  );
});
