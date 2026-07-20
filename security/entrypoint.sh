#!/bin/sh
set -eu

CERT_FILE="${TLS_CERT_FILE:-/certs/gateway.crt}"
KEY_FILE="${TLS_KEY_FILE:-/certs/gateway.key}"

mkdir -p "$(dirname "$CERT_FILE")" "$(dirname "$KEY_FILE")"

if [ ! -s "$CERT_FILE" ] || [ ! -s "$KEY_FILE" ]; then
    openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    chmod 600 "$KEY_FILE"
fi

python -m dpp_aas.render_security_config

exec python -m dpp_aas.security_gateway \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --port "${GATEWAY_PORT:-8443}"
