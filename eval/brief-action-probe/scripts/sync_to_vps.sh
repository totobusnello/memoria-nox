#!/usr/bin/env bash
# Copies the probe code to the VPS. Host comes from $NOX_VPS (public repo: never hard-code it).
set -euo pipefail
: "${NOX_VPS:?set NOX_VPS=root@<host>}"
here="$(cd "$(dirname "$0")/.." && pwd)"
ssh "$NOX_VPS" 'mkdir -p /root/medicoes/7b/code && chmod 700 /root/medicoes/7b'
rsync -a --delete --exclude out --exclude frozen --exclude __pycache__ "$here/" "$NOX_VPS:/root/medicoes/7b/code/"
echo "synced to $NOX_VPS:/root/medicoes/7b/code"
