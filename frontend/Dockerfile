# Single source of truth for Playwright version. Bump BOTH package.json and this
# ARG together. The assertion step in the `visual-test` target fails the build
# on drift (Eng review 1B).
ARG PLAYWRIGHT_VERSION=1.49.0

# ── Dev stage — Vite dev server with HMR ──────────────────────────────────────
FROM node:20-slim AS dev
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# ── Preview stage — prod bundle served by `vite preview` ──────────────────────
# Used by the visual-test suite so specs run against the same bundle produced
# for production. VITE_API_BASE_URL MUST be passed as a build ARG because Vite
# inlines `import.meta.env.VITE_*` at build time. Inside the docker network, the
# api service is reachable as `api-test:8000`, NOT `localhost:8000` — a
# localhost-baked bundle would 404 every fetch from inside the container.
FROM node:20-slim AS preview
WORKDIR /app
ARG VITE_API_BASE_URL=http://api-test:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 4173

CMD ["npx", "vite", "preview"]

# ── Visual-test stage — Playwright + Chromium ─────────────────────────────────
# Base image pins browser + OS + font stack so geometric bbox assertions
# reproduce across Mac dev and Ubuntu CI. Geometric assertions are the primary
# safety net; the base image just removes one category of flake.
FROM mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-jammy AS visual-test
ARG PLAYWRIGHT_VERSION
WORKDIR /app

COPY package*.json ./

# Assert @playwright/test in package-lock.json matches the ARG so the JS client
# and the base-image browser never drift silently.
RUN PKG_VERSION=$(node -e "console.log(require('./package-lock.json').packages['node_modules/@playwright/test'].version)") \
 && if [ "$PKG_VERSION" != "$PLAYWRIGHT_VERSION" ]; then \
      echo "Playwright version mismatch: package-lock.json has $PKG_VERSION, Dockerfile ARG has $PLAYWRIGHT_VERSION. Align both or the browser will not match the JS client." >&2; \
      exit 1; \
    fi

RUN npm ci

COPY . .

# CMD intentionally omitted (Eng 6): docker-compose `command:` is the single
# source of truth for what this container runs.
