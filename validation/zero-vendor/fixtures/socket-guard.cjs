/**
 * socket-guard.cjs — Preload module (--require) that monkey-patches
 * net.Socket.prototype.connect to log every TCP connect attempt and
 * (when NOX_OFFLINE_MODE=1) reject any attempt to a non-loopback peer.
 *
 * Activated via:
 *   NODE_OPTIONS="--require /path/to/socket-guard.cjs"
 *
 * Records attempts to the file at NOX_SOCKET_LOG. Each line is the
 * resolved peer in the form "host:port".
 *
 * This catches native HTTPS / fetch / undici / raw net.connect callers
 * — anything that ultimately reaches Socket.connect.
 */

"use strict";

const net = require("node:net");
const fs = require("node:fs");

const LOG = process.env.NOX_SOCKET_LOG;
const OFFLINE = process.env.NOX_OFFLINE_MODE === "1";

function logAttempt(target) {
  if (!LOG) return;
  try {
    fs.appendFileSync(LOG, target + "\n", "utf8");
  } catch {
    /* best-effort */
  }
}

function isLoopback(host) {
  if (!host) return false;
  return (
    host === "127.0.0.1" ||
    host === "localhost" ||
    host === "::1" ||
    host.startsWith("127.")
  );
}

const realConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function patchedConnect(options, ...rest) {
  let host = "unknown";
  let port = 0;

  if (typeof options === "object" && options !== null) {
    host = options.host || options.hostname || "unknown";
    port = options.port || 0;
  } else if (typeof options === "number") {
    port = options;
    if (typeof rest[0] === "string") host = rest[0];
  } else if (typeof options === "string") {
    // Unix domain socket — record as loopback-equivalent.
    host = options;
    port = 0;
  }

  const target = `${host}:${port}`;
  logAttempt(target);

  if (OFFLINE && !isLoopback(host)) {
    const err = new Error(
      `OFFLINE_MODE_BLOCKED: socket connect to ${target} refused by socket-guard preload`
    );
    err.code = "EOFFLINE";
    // Defer the error so callers see it as a connection error, not a throw.
    setImmediate(() => this.emit("error", err));
    return this;
  }

  return realConnect.call(this, options, ...rest);
};
