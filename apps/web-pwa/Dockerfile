# Multi-stage build for the Splashh PWA.
#
# Stage 1: build the production bundle with Vite.
# Stage 2: serve the static assets with nginx + SPA fallback for React Router.

# ---------- Stage 1: build ----------
FROM node:20-alpine AS build

# pnpm via corepack (matches repo's packageManager field)
ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH
RUN corepack enable

WORKDIR /repo

# Fetch dependencies first for better layer caching.
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/web-pwa/package.json ./apps/web-pwa/
COPY packages/ui/package.json ./packages/ui/
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/config/package.json ./packages/config/
RUN pnpm install --frozen-lockfile

# Now bring in the sources and build.
COPY apps/web-pwa ./apps/web-pwa
COPY packages ./packages
RUN pnpm --filter web-pwa build

# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine AS runtime

# Replace the default site with our SPA config (fallback to index.html so
# React Router deep links like /book/facilities/:id resolve correctly).
COPY apps/web-pwa/nginx.conf /etc/nginx/conf.d/default.conf

# Static assets emitted by `vite build` go to apps/web-pwa/dist.
COPY --from=build /repo/apps/web-pwa/dist /usr/share/nginx/html

EXPOSE 80

# nginx runs in the foreground by default; no explicit CMD required.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
