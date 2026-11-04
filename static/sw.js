/* BookBridge service worker.
 *
 * WHY THIS EXISTS
 * ---------------
 * A free Render web service falls asleep after 15 idle minutes.  The next
 * visitor waits ~40 seconds on Render's "spinning up" screen before our app
 * even starts.  A service worker cannot wake the server, but it *can* show the
 * last page instantly, so opening the app feels like an app instead of a
 * blank wait.  While the saved page is on screen we quietly re-check the
 * server and, as soon as it answers, tell the page to load the fresh copy.
 *
 * RULES
 *  - Only same-origin GET requests are touched.
 *  - /admin/ is never cached.
 *  - HTML is only stored when the response carries X-BB-App: 1, so Render's
 *    own boot page never ends up in the cache.
 *  - Saved pages expire after 24 hours (and are removed on logout).
 *  - Nothing here can break a first visit: if the cache is empty we simply
 *    wait for the network exactly like before.
 */
const VERSION = 'bookbridge-v1';
const PAGE_CACHE = VERSION + '-pages';
const STATIC_CACHE = VERSION + '-static';
const MEDIA_CACHE = VERSION + '-media';
const PAGE_TTL_MS = 24 * 60 * 60 * 1000;
const NAV_TIMEOUT_MS = 4000;

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = [PAGE_CACHE, STATIC_CACHE, MEDIA_CACHE];
    const names = await caches.keys();
    await Promise.all(names.filter((n) => !keep.includes(n)).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

// The page can ask for the cache to be wiped (logout, or "refresh" pressed).
self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'bb-clear-pages') {
    event.waitUntil(caches.delete(PAGE_CACHE));
  }
});

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

async function putPage(request, response) {
  try {
    const copy = response.clone();
    const body = await copy.blob();
    const headers = new Headers(copy.headers);
    headers.set('X-BB-Cached-At', String(Date.now()));
    await caches.open(PAGE_CACHE).put(request, new Response(body, {
      status: copy.status,
      statusText: copy.statusText,
      headers,
    }));
  } catch (err) {
    /* quota or opaque response — never fatal */
  }
}

async function freshPage(request) {
  const cache = await caches.open(PAGE_CACHE);
  const hit = await cache.match(request, { ignoreSearch: true });
  if (!hit) return null;
  const savedAt = Number(hit.headers.get('X-BB-Cached-At') || 0);
  if (!savedAt || Date.now() - savedAt > PAGE_TTL_MS) {
    await cache.delete(request, { ignoreSearch: true });
    return null;
  }
  return hit;
}

/* Put a small banner at the top of a saved page so the user knows it is a
 * stored copy and the app is re-connecting.  The base template's script finds
 * #bbWakingBar and hides it once the server answers. */
async function withWakingBar(response) {
  const contentType = response.headers.get('Content-Type') || '';
  if (!contentType.includes('text/html')) return response;
  let html = await response.text();
  const bar = '<div id="bbWakingBar" style="position:fixed;top:0;left:0;right:0;z-index:99999;'
    + 'background:#0284c7;color:#fff;font:600 13px/1.4 system-ui,sans-serif;padding:9px 14px;'
    + 'text-align:center;box-shadow:0 2px 10px rgba(2,132,199,.35)">'
    + '&#9889; Saved copy &mdash; reconnecting to BookBridge&hellip;</div>';
  html = html.includes('</body>') ? html.replace('</body>', bar + '</body>') : html + bar;
  return new Response(html, {
    status: response.status,
    statusText: response.statusText,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'X-BB-From-Cache': '1' },
  });
}

async function handleNavigation(event) {
  const request = event.request;

  // Race the network against a short timer: on a sleeping instance the network
  // simply hangs, and waiting for it is exactly the experience we are fixing.
  const network = fetch(request).then(async (response) => {
    if (response && response.ok && response.headers.get('X-BB-App') === '1') {
      event.waitUntil(putPage(request, response));
    }
    return response;
  }).catch(() => null);

  const timeout = new Promise((resolve) => setTimeout(() => resolve('timeout'), NAV_TIMEOUT_MS));
  const winner = await Promise.race([network, timeout]);

  if (winner && winner !== 'timeout') {
    return winner;
  }

  const cached = await freshPage(request);
  if (cached) {
    // Keep revalidating in the background; the page reloads when this lands.
    event.waitUntil(network);
    return withWakingBar(cached);
  }

  const late = await network;
  if (late) return late;
  return new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<title>BookBridge</title><body style="font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0;background:#f8fafc">'
    + '<div style="text-align:center"><div style="font-size:2rem">📚</div><h2 style="color:#0f172a">BookBridge is waking up</h2>'
    + '<p style="color:#64748b">This can take up to 40 seconds on the free plan.</p>'
    + '<button onclick="location.reload()" style="background:#0284c7;color:#fff;border:0;padding:12px 26px;border-radius:999px;font-weight:700;cursor:pointer">Try again</button></div></body>',
    { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

async function handleStatic(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request).then((response) => {
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);
  return cached || (await network) || Response.error();
}

async function handleMedia(request) {
  const cache = await caches.open(MEDIA_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response && response.ok && Number(response.headers.get('Content-Length') || 0) < 400000) {
    cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (!isSameOrigin(url)) return;                       // Google Fonts / CDN: leave alone
  if (url.pathname.startsWith('/admin')) return;        // never cache the admin
  if (url.pathname === '/sw.js') return;
  if (url.pathname.startsWith('/wake')) return;

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(event));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(handleStatic(request));
    return;
  }
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(handleMedia(request));
  }
});
