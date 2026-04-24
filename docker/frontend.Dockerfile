FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files first untuk caching
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy all frontend files
COPY frontend/ .

# Debug: Verify structure
RUN echo "=== Directory structure ===" && ls -la && \
    echo "=== lib folder ===" && ls -la lib/ && \
    echo "=== components folder ===" && ls -la components/

# Build the application
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]