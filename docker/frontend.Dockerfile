# ─── Stage 1: deps ──────────────────────────────────────────────
FROM node:20-alpine AS deps

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy hanya package files untuk layer caching
# Build context = project root (context: ..)
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install — node_modules diinstall di Alpine, tidak ada macOS binary
RUN pnpm install --frozen-lockfile

# ─── Stage 2: builder ────────────────────────────────────────────
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy node_modules dari stage deps (Alpine-compatible, bukan dari host)
COPY --from=deps /app/node_modules ./node_modules

# Copy semua source frontend (.env.local sudah di .dockerignore, tidak masuk image)
COPY frontend/ .

# Inject NEXT_PUBLIC_API_URL saat build — nilai dari docker-compose build.args
# HARUS pakai ARG+ENV karena NEXT_PUBLIC_* di-bake ke bundle saat pnpm build,
# bukan saat runtime. .env.local sengaja di-exclude via .dockerignore.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN pnpm build

# ─── Stage 3: runner ─────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Buat user non-root
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Copy hanya output build yang diperlukan untuk runtime
# public/ opsional — Next.js tidak wajib punya direktori ini
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static     ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
