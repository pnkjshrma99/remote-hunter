"use strict";
(() => {
  // src/popup.ts
  var $ = (id) => document.getElementById(id);
  var unauthed = $("unauthenticated");
  var authed = $("authenticated");
  var apiUrlInput = $("apiUrl");
  var tokenInput = $("token");
  var showTokenBtn = $("showTokenBtn");
  var connectBtn = $("connectBtn");
  var connectError = $("connectError");
  var emailDisplay = $("emailDisplay");
  var fillBtn = $("fillBtn");
  var fillStatus = $("fillStatus");
  var refreshBtn = $("refreshBtn");
  var disconnectBtn = $("disconnectBtn");
  var sectionCount = $("sectionCount");
  var fieldCount = $("fieldCount");
  var tokenVisible = false;
  var smartFillBtn = $("smartFillBtn");
  var smartFillStatus = $("smartFillStatus");
  showTokenBtn.addEventListener("click", () => {
    tokenVisible = !tokenVisible;
    tokenInput.type = tokenVisible ? "text" : "password";
    showTokenBtn.textContent = tokenVisible ? "\u{1F648}" : "\u{1F441}";
  });
  function show(el) {
    el.classList.remove("hidden");
  }
  function hide(el) {
    el.classList.add("hidden");
  }
  async function getAuth() {
    return chrome.runtime.sendMessage({ type: "GET_AUTH" });
  }
  async function fetchAndCacheProfile() {
    const result = await chrome.runtime.sendMessage({ type: "FETCH_PROFILE" });
    if (!result.success) return null;
    return result.data;
  }
  async function updateStats() {
    await chrome.runtime.sendMessage({ type: "FETCH_PROFILE" }).catch(() => {
    });
    const result = await chrome.storage.local.get("remote_hunter_profile");
    const profile = result.remote_hunter_profile;
    if (profile) {
      let total = 0;
      for (const s of profile.sections) total += s.fields.length;
      sectionCount.textContent = String(profile.sections.length);
      fieldCount.textContent = String(total);
    }
  }
  async function render() {
    const auth = await getAuth();
    if (auth) {
      hide(unauthed);
      show(authed);
      emailDisplay.textContent = auth.email || "Connected";
      await updateStats();
    } else {
      show(unauthed);
      hide(authed);
    }
  }
  async function proxyFetch(url, options) {
    return chrome.runtime.sendMessage({
      type: "PROXY_FETCH",
      url,
      ...options
    });
  }
  connectBtn.addEventListener("click", async () => {
    const apiUrl = apiUrlInput.value.trim().replace(/\/+$/, "");
    const token = tokenInput.value.trim();
    if (!apiUrl || !token) {
      connectError.textContent = "Please fill in both fields.";
      show(connectError);
      return;
    }
    connectBtn.disabled = true;
    connectBtn.textContent = "Verifying...";
    hide(connectError);
    try {
      const resp = await proxyFetch(`${apiUrl}/api/v1/profile/autofill-data`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 25e3
      });
      if (!resp.success) {
        throw new Error(
          resp.name === "AbortError" ? "Request timed out \u2014 the server may be waking up. Try again." : `API error: ${resp.status || resp.error}`
        );
      }
      const data = resp.data;
      let email = "";
      try {
        const meResp = await proxyFetch(`${apiUrl}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 1e4
        });
        if (meResp.success) {
          email = meResp.data?.email || meResp.data?.full_name || "";
        }
      } catch {
      }
      await chrome.runtime.sendMessage({
        type: "SAVE_AUTH",
        auth: { api_url: apiUrl, token, email }
      });
      await chrome.storage.local.set({ remote_hunter_profile: data });
      await render();
    } catch (err) {
      connectError.textContent = err.message;
      show(connectError);
    } finally {
      connectBtn.disabled = false;
      connectBtn.textContent = "Connect";
    }
  });
  fillBtn.addEventListener("click", async () => {
    fillBtn.disabled = true;
    hide(fillStatus);
    const profile = await fetchAndCacheProfile();
    if (!profile) {
      fillStatus.textContent = "Could not fetch profile. Check your connection.";
      fillStatus.className = "msg error";
      show(fillStatus);
      fillBtn.disabled = false;
      return;
    }
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs[0]?.id) {
      fillStatus.textContent = "No active tab found.";
      fillStatus.className = "msg error";
      show(fillStatus);
      fillBtn.disabled = false;
      return;
    }
    const tabId = tabs[0].id;
    try {
      const result = await chrome.tabs.sendMessage(tabId, { type: "AUTOFILL" });
      if (result?.success) {
        fillStatus.textContent = `\u2713 Filled ${result.filled} field${result.filled === 1 ? "" : "s"}.`;
        fillStatus.className = "msg success";
      } else {
        fillStatus.textContent = result?.error || "No matching form fields.";
        fillStatus.className = "msg error";
      }
      show(fillStatus);
      fillBtn.disabled = false;
      return;
    } catch {
    }
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        files: ["autofill-inject.js"]
      });
      const result = results?.[0]?.result;
      if (result?.success) {
        fillStatus.textContent = `\u2713 Filled ${result.filled} field${result.filled === 1 ? "" : "s"}.`;
        fillStatus.className = "msg success";
      } else {
        fillStatus.textContent = result?.error || "No matching form fields.";
        fillStatus.className = "msg error";
      }
    } catch {
      fillStatus.textContent = "Cannot reach this page. Try reloading the page first.";
      fillStatus.className = "msg error";
    }
    show(fillStatus);
    fillBtn.disabled = false;
  });
  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    const profile = await fetchAndCacheProfile();
    if (profile) {
      await updateStats();
      fillStatus.textContent = `\u2713 Refreshed \u2014 ${profile.sections.length} sections loaded.`;
      fillStatus.className = "msg success";
    } else {
      fillStatus.textContent = "Could not refresh. Reconnect?";
      fillStatus.className = "msg error";
    }
    show(fillStatus);
    refreshBtn.disabled = false;
  });
  disconnectBtn.addEventListener("click", async () => {
    await chrome.runtime.sendMessage({ type: "CLEAR_AUTH" });
    await render();
  });
  smartFillBtn.addEventListener("click", async () => {
    smartFillBtn.disabled = true;
    hide(smartFillStatus);
    const auth = await getAuth();
    if (!auth) {
      smartFillStatus.textContent = "Not connected. Connect first.";
      smartFillStatus.className = "msg error";
      show(smartFillStatus);
      smartFillBtn.disabled = false;
      return;
    }
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs[0]?.id) {
      smartFillStatus.textContent = "No active tab found.";
      smartFillStatus.className = "msg error";
      show(smartFillStatus);
      smartFillBtn.disabled = false;
      return;
    }
    const tabId = tabs[0].id;
    smartFillStatus.textContent = "Analyzing form fields...";
    smartFillStatus.className = "msg";
    show(smartFillStatus);
    try {
      const scrapeResult = await chrome.tabs.sendMessage(tabId, { type: "SCRAPE_FIELDS" }).catch(async () => {
        const results = await chrome.scripting.executeScript({
          target: { tabId },
          func: () => {
            const fields = [];
            document.querySelectorAll("input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select").forEach((el) => {
              const id = el.id;
              let label = "";
              if (id) {
                const lbl = document.querySelector(`label[for="${CSS.escape(id)}"]`);
                if (lbl) label = lbl.textContent?.trim() || "";
              }
              if (!label) {
                const parentLabel = el.closest("label");
                if (parentLabel) label = parentLabel.textContent?.trim() || "";
              }
              if (!label) label = el.getAttribute("aria-label") || el.getAttribute("placeholder") || "";
              fields.push({
                label,
                name: el.getAttribute("name") || el.id || "",
                type: el.type || "text"
              });
            });
            return fields;
          }
        });
        return results?.[0]?.result || [];
      });
      const formFields = Array.isArray(scrapeResult) ? scrapeResult : scrapeResult?.fields || [];
      if (!formFields.length) {
        smartFillStatus.textContent = "No form fields found on this page.";
        smartFillStatus.className = "msg error";
        show(smartFillStatus);
        smartFillBtn.disabled = false;
        return;
      }
      smartFillStatus.textContent = `AI analyzing ${formFields.length} fields...`;
      smartFillStatus.className = "msg";
      const resp = await proxyFetch(`${auth.api_url}/api/v1/profile/ai-autofill`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${auth.token}`
        },
        body: JSON.stringify(formFields),
        timeout: 3e4
      });
      let aiFields = [];
      if (!resp.success) {
        const detail = resp.data?.detail || "";
        const fallbackFields = resp.data?.fields || [];
        if (fallbackFields.length > 0) {
          aiFields = fallbackFields;
        } else {
          throw new Error(detail || resp.error || "AI autofill failed");
        }
      } else {
        aiFields = resp.data?.fields || [];
      }
      if (!aiFields.length) {
        smartFillStatus.textContent = "AI could not match any fields.";
        smartFillStatus.className = "msg error";
        show(smartFillStatus);
        smartFillBtn.disabled = false;
        return;
      }
      const fillResult = await chrome.tabs.sendMessage(tabId, {
        type: "SMART_FILL",
        fields: aiFields
      }).catch(async () => {
        const results = await chrome.scripting.executeScript({
          target: { tabId },
          args: [aiFields],
          func: (fields) => {
            let filled = 0;
            for (const f of fields) {
              const name = f.name;
              const label = f.label;
              let el = null;
              if (name) {
                el = document.querySelector(`[name="${CSS.escape(name)}"], #${CSS.escape(name)}`);
              }
              if (!el && label) {
                const id = document.querySelector(`label`)?.getAttribute("for");
                const labels = document.querySelectorAll("label");
                for (const lbl of labels) {
                  if (lbl.textContent?.trim().toLowerCase().includes(label.toLowerCase())) {
                    const forId = lbl.getAttribute("for");
                    if (forId) {
                      el = document.getElementById(forId);
                      if (el) break;
                    }
                  }
                }
              }
              if (!el) continue;
              if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
                el.value = f.value;
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
                el.style.outline = "2px solid #22c55e";
                el.style.outlineOffset = "1px";
                filled++;
              } else if (el instanceof HTMLSelectElement) {
                const opts = Array.from(el.options);
                const match = opts.find((o) => o.text.toLowerCase().includes(f.value.toLowerCase()));
                if (match) {
                  el.value = match.value;
                  el.dispatchEvent(new Event("change", { bubbles: true }));
                  el.style.outline = "2px solid #22c55e";
                  el.style.outlineOffset = "1px";
                  filled++;
                }
              }
            }
            return filled;
          }
        });
        return results?.[0]?.result || 0;
      });
      const filledCount = typeof fillResult === "number" ? fillResult : fillResult?.filled || 0;
      smartFillStatus.textContent = `\u2728 AI filled ${filledCount} field${filledCount === 1 ? "" : "s"}!`;
      smartFillStatus.className = "msg success";
    } catch (err) {
      smartFillStatus.textContent = `AI error: ${err.message}`;
      smartFillStatus.className = "msg error";
    }
    show(smartFillStatus);
    smartFillBtn.disabled = false;
  });
  render();
})();
