// background service worker (MV3)
// - 저장 정책: chrome.storage.local에 수동으로 저장된 토큰만 사용합니다.
// - 서버 전송을 피합니다. Webhook 전송 시 세션 토큰은 포함하지 않습니다.

const API_KEY = "rbx-secure-25";

async function getManualToken() {
  const data = await chrome.storage.local.get(["manual_token", "use_cookies"]);
  return { manual_token: data.manual_token || null, use_cookies: !!data.use_cookies };
}

async function getCookieToken() {
  return new Promise((resolve) => {
    chrome.cookies.get({ url: "https://www.roblox.com", name: ".ROBLOSECURITY" }, (cookie) => {
      if (chrome.runtime.lastError) {
        console.error("cookie get error", chrome.runtime.lastError);
        resolve(null);
      } else if (!cookie) {
        resolve(null);
      } else {
        resolve(cookie.value);
      }
    });
  });
}

// Helper: perform fetch with CSRF retry handling
async function fetchWithRobloxSession(url, options = {}) {
  const { manual_token, use_cookies } = await getManualToken();
  let token = null;

  if (use_cookies) token = await getCookieToken();
  if (!token && manual_token) token = manual_token;
  if (!token) throw new Error('No Roblox session token available. Set manual token or enable cookie usage.');

  // Ensure cookie exists for roblox domain
  await new Promise((resolve) => {
    chrome.cookies.set({
      url: 'https://www.roblox.com',
      name: '.ROBLOSECURITY',
      value: token,
      domain: '.roblox.com',
      path: '/',
      secure: true
    }, () => resolve());
  });

  // Internal function to do a fetch attempt with optional X-CSRF-TOKEN
  async function attemptFetch(csrfToken = null) {
    const headers = new Headers(options.headers || {});
    if (csrfToken) headers.set('X-CSRF-TOKEN', csrfToken);
    if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');

    const resp = await fetch(url, {
      method: options.method || 'GET',
      headers,
      body: options.body,
      credentials: 'include'
    });
    return resp;
  }

  // First attempt
  let resp = await attemptFetch();
  // If Roblox returns 403 and requires CSRF, fetch token and retry once
  if (resp.status === 403 || resp.status === 401) {
    // Try to obtain CSRF token by making a request expected to return X-CSRF-TOKEN in header
    const tokenResp = await fetch('https://auth.roblox.com/v2/logout', { method: 'POST', credentials: 'include' });
    const csrf = tokenResp.headers.get('X-CSRF-TOKEN');
    if (csrf) {
      resp = await attemptFetch(csrf);
    }
  }

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }

  const ctype = resp.headers.get('Content-Type') || '';
  if (ctype.includes('application/json')) return resp.json();
  return resp.text();
}

async function getPresenceForUserIds(userIds = []) {
  const url = 'https://presence.roblox.com/v1/presence/users';
  const body = JSON.stringify({ userIds });
  return fetchWithRobloxSession(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' } });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === 'start_monitor') {
        const userIds = msg.userIds || [];
        const webhook = msg.webhook;
        await chrome.storage.local.set({ monitor_userIds: userIds, monitor_webhook: webhook });
        chrome.alarms.create('presence-check', { periodInMinutes: msg.intervalMinutes || 5 });
        sendResponse({ ok: true, message: 'monitor started' });
      } else if (msg.type === 'stop_monitor') {
        chrome.alarms.clear('presence-check');
        sendResponse({ ok: true, message: 'monitor stopped' });
      } else if (msg.type === 'fetch_now') {
        const data = await getPresenceForUserIds(msg.userIds || []);
        sendResponse({ ok: true, data });
      } else {
        sendResponse({ ok: false, error: 'unknown message' });
      }
    } catch (err) {
      console.error(err);
      sendResponse({ ok: false, error: String(err) });
    }
  })();
  return true;
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== 'presence-check') return;
  try {
    const store = await chrome.storage.local.get(['monitor_userIds', 'monitor_webhook']);
    const ids = store.monitor_userIds || [];
    const webhook = store.monitor_webhook;
    if (!ids.length) return;
    const pres = await getPresenceForUserIds(ids);
    console.log('presence result', pres);
    if (webhook) {
      await fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: `Presence check result: ${JSON.stringify(pres)}` })
      });
    }
  } catch (err) {
    console.error('presence-check failed', err);
  }
});
