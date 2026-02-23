// Kill-switch service worker: unregisters itself so browsers that cached
// the old PWA service worker will clean up on next visit.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => {
  self.registration.unregister();
  self.clients.matchAll({ type: 'window' }).then(clients => {
    clients.forEach(client => client.navigate(client.url));
  });
});
