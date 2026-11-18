#!/usr/bin/env bash
#
# setup_https.sh - pasang HTTPS (Let's Encrypt) untuk stack Docker di server produksi.
#
# Usage (di server, DNS domain sudah mengarah ke server, port 80 dan 443 terbuka):
#   DOMAIN=rag.example.com scripts/setup_https.sh
#   DOMAIN=rag.example.com LETSENCRYPT_EMAIL=saya@example.com scripts/setup_https.sh
#
# Yang dilakukan:
#   1. memasang certbot (apt) bila belum ada
#   2. menerbitkan sertifikat lewat webroot /var/www/certbot (nginx berhenti beberapa detik
#      pada penerbitan pertama saja)
#   3. memasang deploy hook: nginx di-reload setiap sertifikat diperpanjang
#   4. mengaktifkan override docker-compose.https.yml lewat docker/.env
#   5. menguji perpanjangan otomatis (certbot.timer + `certbot renew --dry-run`)
#
# Aman dijalankan ulang: sertifikat yang sudah ada tidak diterbitkan lagi.

set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "$0")/../docker" && pwd)"
ENV_FILE="$DOCKER_DIR/.env"
WEBROOT=/var/www/certbot
HOOK=/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
COMPOSE_FILES="docker-compose.yml:docker-compose.https.yml"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE tidak ditemukan (salin dari .env.example dulu)." >&2
    exit 1
fi

DOMAIN="${DOMAIN:-$(grep -E '^DOMAIN=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)}"
if [ -z "$DOMAIN" ]; then
    echo "ERROR: DOMAIN belum diisi. Contoh: DOMAIN=rag.example.com $0" >&2
    exit 1
fi
EMAIL="${LETSENCRYPT_EMAIL:-}"

echo "==> Domain: $DOMAIN"

# 1. certbot
if ! command -v certbot >/dev/null 2>&1; then
    echo "==> Memasang certbot"
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot
fi
sudo mkdir -p "$WEBROOT"

# 2. Sertifikat
if sudo test -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"; then
    echo "==> Sertifikat untuk $DOMAIN sudah ada, penerbitan dilewati"
else
    echo "==> Menerbitkan sertifikat (nginx berhenti sebentar)"
    # Konfigurasi HTTPS tidak bisa start sebelum sertifikat ada, jadi tantangan ACME
    # pertama dilayani nginx sementara yang hanya menyajikan webroot.
    (cd "$DOCKER_DIR" && docker compose -f docker-compose.yml stop nginx)
    trap 'docker rm -f certbot-bootstrap >/dev/null 2>&1 || true' EXIT
    docker run -d --rm --name certbot-bootstrap -p 80:80 \
        -v "$WEBROOT:/usr/share/nginx/html:ro" nginx:alpine >/dev/null

    if [ -n "$EMAIL" ]; then
        ACCOUNT_ARGS=(--email "$EMAIL" --no-eff-email)
    else
        ACCOUNT_ARGS=(--register-unsafely-without-email)
    fi
    sudo certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" \
        --non-interactive --agree-tos "${ACCOUNT_ARGS[@]}"

    docker rm -f certbot-bootstrap >/dev/null
    trap - EXIT
fi

# 3. Deploy hook: dijalankan certbot setiap sertifikat berhasil diperpanjang
echo "==> Memasang deploy hook $HOOK"
sudo mkdir -p "$(dirname "$HOOK")"
sudo tee "$HOOK" >/dev/null <<EOF
#!/bin/sh
# Dibuat oleh scripts/setup_https.sh: muat ulang nginx agar memakai sertifikat baru.
cd "$DOCKER_DIR" && docker compose exec -T nginx nginx -s reload
EOF
sudo chmod 755 "$HOOK"

# 4. Aktifkan override HTTPS
set_env() {
    local key="$1" value="$2"
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '\n%s=%s\n' "$key" "$value" >>"$ENV_FILE"
    fi
}
set_env DOMAIN "$DOMAIN"
set_env COMPOSE_FILE "$COMPOSE_FILES"

echo "==> Menjalankan nginx dengan konfigurasi HTTPS"
(cd "$DOCKER_DIR" && docker compose up -d --no-deps --force-recreate nginx)

# 5. Perpanjangan otomatis
echo "==> Menguji perpanjangan otomatis"
sudo systemctl enable --now certbot.timer
sudo certbot renew --dry-run
systemctl list-timers certbot.timer --no-pager | sed -n '1,2p'

for key in ALLOWED_ORIGINS NEXT_PUBLIC_API_URL; do
    if ! grep -E "^${key}=" "$ENV_FILE" | grep -q "https://$DOMAIN"; then
        echo "PERHATIAN: $key di docker/.env belum memakai https://$DOMAIN"
    fi
done
echo "    (mengubah NEXT_PUBLIC_API_URL butuh build ulang: docker compose build frontend)"

echo "==> Selesai: https://$DOMAIN"
