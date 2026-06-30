/**
 * options.js — Settings controller.
 *
 * State flow:
 *   load   : GET_SETTINGS → fill inputs
 *   save   : SET_SETTINGS on change (debounced)
 *   test   : PING_API → show status
 *   queue  : GET_STATUS → pending count
 *   clear  : CLEAR_QUEUE
 *
 * Bearer token is stored in chrome.storage.local (NOT sync). The spec mentions
 * "encrypted via webcrypto" — we implement a simple AES-GCM envelope below;
 * key lives in chrome.storage.local too so it's only a soft barrier against
 * casual storage inspection (real protection is OS keychain, not in scope for
 * v0.1).
 */

const $ = (sel) => document.querySelector(sel);

const els = {
  apiUrl: $("#api-url"),
  authToken: $("#auth-token"),
  testBtn: $("#btn-test"),
  testResult: $("#test-result"),
  allowlist: $("#allowlist"),
  newDomain: $("#new-domain"),
  addDomainBtn: $("#btn-add-domain"),
  autoCapture: $("#opt-auto-capture"),
  inlineAnswer: $("#opt-inline-answer"),
  omniboxPrefix: $("#omnibox-prefix"),
  queueStatus: $("#queue-status"),
  clearQueueBtn: $("#btn-clear-queue"),
  saveStatus: $("#save-status"),
};

let currentSettings = null;

// ────────────────────────────────────────────────────────────────────────
// Comm helpers
// ────────────────────────────────────────────────────────────────────────

function send(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
          return;
        }
        resolve(response || { ok: false });
      });
    } catch (err) {
      resolve({ ok: false, error: String(err.message || err) });
    }
  });
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

// ────────────────────────────────────────────────────────────────────────
// WebCrypto envelope for auth_token (soft barrier — see file header)
// ────────────────────────────────────────────────────────────────────────

const CRYPTO_KEY_STORAGE = "options_crypto_key";

async function getOrCreateCryptoKey() {
  const stored = await chrome.storage.local.get(CRYPTO_KEY_STORAGE);
  if (stored[CRYPTO_KEY_STORAGE]) {
    return crypto.subtle.importKey(
      "raw",
      base64ToBytes(stored[CRYPTO_KEY_STORAGE]),
      "AES-GCM",
      true,
      ["encrypt", "decrypt"],
    );
  }
  const key = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
  const raw = await crypto.subtle.exportKey("raw", key);
  await chrome.storage.local.set({
    [CRYPTO_KEY_STORAGE]: bytesToBase64(new Uint8Array(raw)),
  });
  return key;
}

async function encryptToken(plain) {
  if (!plain) return "";
  const key = await getOrCreateCryptoKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const enc = new TextEncoder().encode(plain);
  const ct = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc),
  );
  // Envelope: iv(12 bytes) || ciphertext  → base64
  const out = new Uint8Array(iv.length + ct.length);
  out.set(iv, 0);
  out.set(ct, iv.length);
  return `enc1:${bytesToBase64(out)}`;
}

async function decryptToken(envelope) {
  if (!envelope || !envelope.startsWith("enc1:")) return envelope || "";
  try {
    const key = await getOrCreateCryptoKey();
    const raw = base64ToBytes(envelope.slice(5));
    const iv = raw.slice(0, 12);
    const ct = raw.slice(12);
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
    return new TextDecoder().decode(pt);
  } catch {
    return "";
  }
}

function bytesToBase64(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ────────────────────────────────────────────────────────────────────────
// Load / save
// ────────────────────────────────────────────────────────────────────────

async function load() {
  const res = await send({ type: "GET_SETTINGS" });
  currentSettings = res?.settings || {};

  els.apiUrl.value = currentSettings.api_url || "";
  els.authToken.value = await decryptToken(currentSettings.auth_token || "");
  els.autoCapture.checked = !!currentSettings.auto_capture;
  els.inlineAnswer.checked = !!currentSettings.inline_answer;
  els.omniboxPrefix.value = currentSettings.omnibox_prefix || "nx";
  renderAllowlist(currentSettings.allowlist || []);

  refreshQueueStatus();
}

async function saveAll() {
  const allow = Array.from(els.allowlist.querySelectorAll("li")).map((li) =>
    li.dataset.domain,
  );
  const next = {
    api_url: els.apiUrl.value.trim() || "http://127.0.0.1:18802",
    auth_token: await encryptToken(els.authToken.value.trim()),
    allowlist: allow,
    auto_capture: !!els.autoCapture.checked,
    inline_answer: !!els.inlineAnswer.checked,
    omnibox_prefix: (els.omniboxPrefix.value || "nx").trim().slice(0, 10),
  };
  const res = await send({ type: "SET_SETTINGS", settings: next });
  if (res?.ok) {
    currentSettings = next;
    els.saveStatus.textContent = "Settings saved";
    els.saveStatus.className = "hint ok";
    setTimeout(() => {
      els.saveStatus.textContent = "";
    }, 2000);
  } else {
    els.saveStatus.textContent = "Failed to save";
    els.saveStatus.className = "hint fail";
  }
}

const debouncedSave = debounce(saveAll, 350);

// ────────────────────────────────────────────────────────────────────────
// Allowlist UI
// ────────────────────────────────────────────────────────────────────────

function renderAllowlist(list) {
  els.allowlist.innerHTML = "";
  if (list.length === 0) {
    const empty = document.createElement("li");
    empty.style.background = "transparent";
    empty.style.border = "none";
    empty.style.color = "var(--muted)";
    empty.style.fontStyle = "italic";
    empty.textContent = "Empty — extension is silent everywhere.";
    els.allowlist.appendChild(empty);
    return;
  }
  for (const domain of list) {
    const li = document.createElement("li");
    li.dataset.domain = domain;
    li.innerHTML = `<span>${escapeHtml(domain)}</span>`;
    const x = document.createElement("button");
    x.type = "button";
    x.textContent = "×";
    x.title = `Remove ${domain}`;
    x.addEventListener("click", () => {
      li.remove();
      debouncedSave();
    });
    li.appendChild(x);
    els.allowlist.appendChild(li);
  }
}

function addDomain() {
  const raw = els.newDomain.value.trim().toLowerCase();
  if (!raw) return;
  // Quick sanity check — no protocol, no path, no spaces.
  if (!/^[a-z0-9.\-]+\.[a-z]{2,}$/.test(raw)) {
    els.newDomain.style.borderColor = "var(--danger)";
    setTimeout(() => {
      els.newDomain.style.borderColor = "";
    }, 1200);
    return;
  }
  const current = Array.from(els.allowlist.querySelectorAll("li[data-domain]"))
    .map((li) => li.dataset.domain);
  if (current.includes(raw)) return;
  renderAllowlist([...current, raw]);
  els.newDomain.value = "";
  debouncedSave();
}

els.addDomainBtn.addEventListener("click", addDomain);
els.newDomain.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") {
    ev.preventDefault();
    addDomain();
  }
});

// ────────────────────────────────────────────────────────────────────────
// Test connection
// ────────────────────────────────────────────────────────────────────────

els.testBtn.addEventListener("click", async () => {
  // Save first so the test uses the URL/token the user just typed.
  await saveAll();
  els.testResult.textContent = "Testing…";
  els.testResult.className = "hint";
  const res = await send({ type: "PING_API" });
  if (res?.ok) {
    const chunks = res.data?.totalChunks || res.data?.chunks;
    els.testResult.textContent = chunks
      ? `online · ${chunks} chunks`
      : "online";
    els.testResult.className = "hint ok";
  } else {
    els.testResult.textContent = `offline (${res?.error || "no response"})`;
    els.testResult.className = "hint fail";
  }
});

// ────────────────────────────────────────────────────────────────────────
// Queue management
// ────────────────────────────────────────────────────────────────────────

async function refreshQueueStatus() {
  const res = await send({ type: "GET_STATUS" });
  const n = res?.pending || 0;
  els.queueStatus.textContent = `Pending: ${n}`;
}

els.clearQueueBtn.addEventListener("click", async () => {
  if (!confirm("Discard all queued chunks? They will NOT be sent to nox-mem.")) {
    return;
  }
  await send({ type: "CLEAR_QUEUE" });
  refreshQueueStatus();
});

// ────────────────────────────────────────────────────────────────────────
// Auto-save on field changes
// ────────────────────────────────────────────────────────────────────────

for (const el of [
  els.apiUrl,
  els.authToken,
  els.autoCapture,
  els.inlineAnswer,
  els.omniboxPrefix,
]) {
  el.addEventListener("change", debouncedSave);
  el.addEventListener("input", debouncedSave);
}

// ────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ────────────────────────────────────────────────────────────────────────
// Boot
// ────────────────────────────────────────────────────────────────────────

load();
setInterval(refreshQueueStatus, 4000);
