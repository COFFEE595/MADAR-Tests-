/* عامل الخدمة: يخزن الواجهة والكتب للعمل دون اتصال */
const VER = 'lr-v3',
      SHELL = ['./', 'index.html', 'generators.js', 'manifest.webmanifest', 'favicon.svg', 'books/index.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== VER).map(k => caches.delete(k))))
    .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== location.origin) return;
  /* شبكة أولًا مع الرجوع للذاكرة: يضمن ظهور تحديثات الكتب ويسهل دون اتصال */
  e.respondWith(
    fetch(r).then(res => {
      if (res.ok) {
        const cp = res.clone();
        caches.open(VER).then(c => c.put(r, cp));
      }
      return res;
    }).catch(() => caches.match(r))
  );
});
