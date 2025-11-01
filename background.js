// background service worker (MV3)
// - 保存ポリシー: ローカルの chrome.storage.local のみ。
// - サーバーに送らないことを強く推奨。

const API_KEY = "rbx-secure-25"; // 既存サーバー連携があるならそのまま利用可能。ただしトークンは送らないこと。

// keys in storage:
// manual_token -> user-provided .ROBLOSECURITY
// use_cookies -> boolean: true = use browser cookie automatically

async function getManualToken() {
  const data = await chrome.storage.local.get(["manual_token", "use_cookies"]);
  return { manual_token: data.manual_token || null, use_cookies: !!data.use_cookies };
}

async function getCookieToken() {
  // domain: .roblox.com ; name: .ROBLOSECURITY
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

// 汎用 fetch 利用関数: ログイン cookie を用いて Roblox API へリクエスト
async function fetchWithRobloxSession(url, options = {}) {
  // determine token source
  const { manual_token, use_cookies } = await getManualToken();
  let token = null;

  if (use_cookies) {
    token = await getCookieToken();
  }
  if (!token && manual_token) {
    token = manual_token;
  }

  if (!token) {
    throw new Error("No Roblox session token available (set manual token or enable cookie use).");
  }

  // We cannot set arbitrary Cookie header in some environments, but as a service_worker we can use fetch
  // and rely on chrome.cookies.set to set a cookie for the domain prior to the fetch (temporary).
  // Safer approach: use chrome.cookies.set to ensure the cookie exists for roblox domain.
  await new Promise((resolve, reject) => {
    chrome.cookies.set({
      url: "https://www.roblox.com",
      name: ".ROBLOSECURITY",
      value: token,
      secure: true,
      httpOnly: false, // cannot change HttpOnly property, but cookie.set will create non-Httponly cookie; used temporarily
      domain: ".roblox.com",
      path: "/"
    }, (cookie) => {
      if (chrome.runtime.lastError) {
        console.warn("cookies.set error", chrome.runtime.lastError);
        // still attempt fetch (may fail)
      }
      resolve();
    });
  });

  // Do the fetch (example endpoint, verify actual path/format)
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body,
    credentials: "include"
  });

  if (!resp.ok) {
    // If Roblox requires X-CSRF-TOKEN, handle the 403 pattern to fetch CSRF and retry (not fully implemented here)
    throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
  }

  const ctype = resp.headers.get("Content-Type") || "";
  if (ctype.includes("application/json")) return resp.json();
  return resp.text();
}

// Example: get presence for user ids (adjust endpoint to the one you use)
async function getPresenceForUserIds(userIds = []) {
  const url = "https://presence.roblox.com/v1/presence/users";
  const body = JSON.stringify({ userIds });
  return fetchWithRobloxSession(url, { method: "POST", body, headers: { "Content-Type": "application/json" } });
}

// Handle messages from content script UI
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === "start_monitor") {
        // start periodic check using alarms
        const userIds = msg.userIds || [];
        const webhook = msg.webhook;
        // store webhook & userIds locally for alarm handler
        await chrome.storage.local.set({ monitor_userIds: userIds, monitor_webhook: webhook });
        chrome.alarms.create("presence-check", { periodInMinutes: msg.intervalMinutes || 5 });
        sendResponse({ ok: true, message: "monitor started" });
      } else if (msg.type === "stop_monitor") {
        chrome.alarms.clear("presence-check");
        sendResponse({ ok: true, message: "monitor stopped" });
      } else if (msg.type === "fetch_now") {
        const data = await getPresenceForUserIds(msg.userIds || []);
        sendResponse({ ok: true, data });
      } else {
        sendResponse({ ok: false, error: "unknown message" });
      }
    } catch (err) {
      console.error(err);
      sendResponse({ ok: false, error: String(err) });
    }
  })();
  // required for async sendResponse
  return true;
});

// Alarm handler: periodic checks
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "presence-check") return;
  try {
    const store = await chrome.storage.local.get(["monitor_userIds", "monitor_webhook"]);
    const ids = store.monitor_userIds || [];
    const webhook = store.monitor_webhook;
    if (!ids.length) return;
    const pres = await getPresenceForUserIds(ids);
    // TODO: diffing / previous state management and Discord webhook send.
    console.log("presence result", pres);

    // Example: send to webhook (do NOT include session token)
    if (webhook) {
      await fetch(webhook, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: `Presence check result: ${JSON.stringify(pres)}` })
      });
    }
  } catch (err) {
    console.error("presence-check failed", err);
  }
});
