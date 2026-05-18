# syntax=docker/dockerfile:1.7
#
# nox-mem — multi-stage Dockerfile
# Supports linux/amd64 and linux/arm64 via BuildKit.
#
# Pinned digest for node:22-alpine3.21 (2025-03, amd64+arm64 manifest):
#   docker pull node:22-alpine3.21@sha256:9bef0ef1e268f60627da9ba7d7605e8831d5b56ad07487d24d1aa386336d1944
#
# To verify: docker manifest inspect node:22-alpine3.21 | jq '.manifests[].digest'
#
ARG NODE_IMAGE=node:22-alpine3.21@sha256:9bef0ef1e268f60627da9ba7d7605e8831d5b56ad07487d24d1aa386336d1944

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder
# Installs ALL deps, compiles TypeScript → dist/
# ─────────────────────────────────────────────────────────────────────────────
FROM ${NODE_IMAGE} AS builder

WORKDIR /build

# Install build toolchain needed by native addons (better-sqlite3 / sqlite-vec)
RUN apk add --no-cache python3 make g++ gcc libc-dev

# Copy manifests first — Docker layer cache: only re-install when lockfile changes
COPY package.json package-lock.json ./

# Full install (dev + prod deps) — needed for tsc compilation
RUN npm ci --ignore-scripts

# Copy source tree
# (staged-* dirs are intentionally included — the build reads them for module
#  stitching. .dockerignore excludes heavy test fixtures and .git.)
COPY . .

# Compile TS → JS
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime
# Lean Alpine image — only production artifacts, non-root user
# ─────────────────────────────────────────────────────────────────────────────
FROM ${NODE_IMAGE} AS runtime

# Runtime only needs sqlite shared lib for better-sqlite3 native addon
RUN apk add --no-cache libstdc++ libgcc

WORKDIR /app

# Create non-root user (uid/gid 10000 — outside typical OS range)
RUN addgroup -g 10000 -S noxmem \
 && adduser  -u 10000 -S noxmem -G noxmem -H -s /sbin/nologin

# Copy compiled artefacts from builder, owned by noxmem
COPY --from=builder --chown=noxmem:noxmem /build/dist        ./dist
COPY --from=builder --chown=noxmem:noxmem /build/node_modules ./node_modules
COPY --from=builder --chown=noxmem:noxmem /build/package.json ./package.json

# Copy entrypoint script (owned root, exec-only — hardened)
COPY --chown=root:root scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

# Data directory — writable by noxmem, separate from code
RUN mkdir -p /data && chown noxmem:noxmem /data

# Drop to non-root
USER noxmem

# SQLite data lives here (mounted as a volume)
VOLUME ["/data"]

# HTTP API
EXPOSE 18802

# Healthcheck — uses wget (available in busybox alpine) to avoid curl dep
HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=10s \
  --retries=3 \
  CMD wget -qO- http://localhost:${NOX_API_PORT:-18802}/api/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
# Default: run the HTTP API + MCP server
CMD ["node", "dist/index.js", "serve"]
