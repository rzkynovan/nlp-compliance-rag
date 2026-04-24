# Build dari root context agar semua file ter-copy dengan benar
FROM node:20-alpine

WORKDIR /app/frontend

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy seluruh frontend folder
COPY frontend/ .

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build
RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]