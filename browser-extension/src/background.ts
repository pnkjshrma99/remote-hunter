import type { ProfileData, StoredAuth } from "./types";

const STORAGE_KEY = "remote_hunter_auth";
const REFRESH_INTERVAL_MINUTES = 5;

async function refreshProfile() {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  const auth: StoredAuth | undefined = result[STORAGE_KEY];
  if (!auth) return;

  try {
    const resp = await fetch(`${auth.api_url}/api/v1/profile/autofill-data`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (resp.ok) {
      const data: ProfileData = await resp.json();
      await chrome.storage.local.set({ remote_hunter_profile: data });
    }
  } catch {
    // Silently fail — will retry on next interval
  }
}

chrome.runtime.onInstalled.addListener(() => {
  // Set up periodic profile refresh
  chrome.alarms.create("refreshProfile", { periodInMinutes: REFRESH_INTERVAL_MINUTES });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "refreshProfile") {
    refreshProfile();
  }
});

chrome.runtime.onMessage.addListener(
  (
    message: any,
    sender: chrome.runtime.MessageSender,
    sendResponse: (response?: any) => void
  ) => {
    switch (message.type) {
      case "GET_AUTH":
        chrome.storage.local.get(STORAGE_KEY).then((result) => {
          sendResponse(result[STORAGE_KEY] || null);
        });
        return true;

      case "SAVE_AUTH":
        chrome.storage.local
          .set({ [STORAGE_KEY]: message.auth })
          .then(() => sendResponse({ success: true }));
        return true;

      case "CLEAR_AUTH":
        chrome.storage.local
          .remove(STORAGE_KEY)
          .then(() => {
            chrome.storage.local.remove("remote_hunter_profile");
            sendResponse({ success: true });
          });
        return true;

      case "FETCH_PROFILE": {
        chrome.storage.local.get(STORAGE_KEY).then(async (result) => {
          const auth: StoredAuth | undefined = result[STORAGE_KEY];
          if (!auth) {
            sendResponse({ success: false, error: "Not authenticated" });
            return;
          }
          try {
            const resp = await fetch(
              `${auth.api_url}/api/v1/profile/autofill-data`,
              { headers: { Authorization: `Bearer ${auth.token}` } }
            );
            if (!resp.ok) {
              sendResponse({
                success: false,
                error: `API error: ${resp.status}`,
              });
              return;
            }
            const data: ProfileData = await resp.json();
            await chrome.storage.local.set({ remote_hunter_profile: data });
            sendResponse({ success: true, data });
          } catch (err: any) {
            sendResponse({ success: false, error: err.message });
          }
        });
        return true;
      }

      case "AUTOFILL_PAGE":
        chrome.tabs
          .query({ active: true, currentWindow: true })
          .then((tabs) => {
            const tab = tabs[0];
            if (!tab?.id) {
              sendResponse({ success: false, error: "No active tab" });
              return;
            }
            chrome.tabs
              .sendMessage(tab.id, { type: "AUTOFILL" })
              .then((res) =>
                sendResponse(
                  res || { success: false, error: "No response from page" }
                )
              )
              .catch((err) =>
                sendResponse({ success: false, error: err.message })
              );
          });
        return true;

      case "AUTOFILL_TAB_ID": {
        const tabId = message.tabId as number;
        if (!tabId) {
          sendResponse({ success: false, error: "No tab ID provided" });
          return true;
        }
        chrome.tabs
          .sendMessage(tabId, { type: "AUTOFILL" })
          .then((res) =>
            sendResponse(
              res || { success: false, error: "No response from page" }
            )
          )
          .catch((err) =>
            sendResponse({ success: false, error: err.message })
          );
        return true;
      }

      case "CHECK_INSTALLED":
        sendResponse({ installed: true });
        return true;

      case "PROXY_FETCH": {
        const proxyUrl = message.url as string;
        const options: RequestInit = {
          method: message.method || "GET",
          headers: (message.headers || {}) as Record<string, string>,
        };
        if (message.body) options.body = message.body;
        const timeoutMs = (message.timeout as number) || 15000;

        (async () => {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeoutMs);
          options.signal = controller.signal;
          try {
            const resp = await fetch(proxyUrl, options);
            const text = await resp.text();
            clearTimeout(timer);
            let json: any;
            try { json = JSON.parse(text); } catch { json = text; }
            sendResponse({ success: resp.ok, status: resp.status, data: json });
          } catch (err: any) {
            clearTimeout(timer);
            sendResponse({ success: false, error: err.message, name: err.name });
          }
        })();
        return true;
      }

      default:
        sendResponse({ error: `Unknown type: ${message.type}` });
        return true;
    }
  }
);
