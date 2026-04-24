FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy semua file konfigurasi dan source code sekaligus
# Ini memastikan tsconfig.json, lib/, components/, app/, etc. semua ter-copy
COPY . .

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build the application
RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]