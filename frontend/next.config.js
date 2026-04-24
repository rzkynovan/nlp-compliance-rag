/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output untuk Docker multi-stage build (hemat ukuran image)
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  },
  // Catatan: path alias @/* sudah di-handle otomatis oleh Next.js 14
  // via tsconfig.json "paths": {"@/*": ["./*"]} — tidak perlu webpack alias manual
};

module.exports = nextConfig;