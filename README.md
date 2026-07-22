# BaSyx Setup
This setup uses BaSyx Go components and PostgreSQL.

# Machine Setup Guide

This document lists all changes required to run this stack on a new machine after cloning the repository.

---

## 1. Get your machine's IP address

```bash
ipconfig getifaddr en0   # Wi-Fi
ipconfig getifaddr en1   # Ethernet
```

Note the IP (e.g. `192.168.56.158`). You will need it for every step below.

---

## 2. Create `.env` file

Create a `.env` file in the project root with your credentials:

```env
HOST_IP=<YOUR_IP>

MONGO_USERNAME=admin
MONGO_PASSWORD=<CHANGE_ME>

KC_DB_USERNAME=keycloak
KC_DB_PASSWORD=<CHANGE_ME>
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=<CHANGE_ME>
```

---

## 3. Generate self-signed SSL certificates

Nginx requires TLS certs. Create the directory and generate a cert for your IP:

```bash
mkdir -p nginx/certs

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout nginx/certs/server.key \
  -out nginx/certs/server.crt \
  -subj "/CN=<YOUR_IP>" \
  -addext "subjectAltName=IP:<YOUR_IP>"
```

---

## 4. Create `aas/` directory

The AAS Environment container mounts this directory:

```bash
mkdir -p aas
```

Place your `.aasx` or AAS JSON files here, or upload them through the UI later.

---

## 5. Update IP address in config files

Replace the placeholder IP (`192.168.56.212`) with your machine's IP in these files:

| File | What to replace |
|------|----------------|
| `basyx-infra.yml` | All occurrences of `192.168.56.212` |
| `docker-compose.yml` | `KEYCLOAK_URL` value |
| `nginx/nginx.conf` | All `server_name` values |
| `keycloak/realm-export.json` | All `redirectUris`, `webOrigins`, and `post.logout.redirect.uris` |
| `basyx/application.properties` | Comment with issuer URL |

Quick one-liner (run from project root):

```bash
grep -rl '192.168.56.212' . --include='*.yml' --include='*.yaml' --include='*.conf' --include='*.json' --include='*.properties' | xargs sed -i '' 's/192.168.56.212/<YOUR_IP>/g'
```

---

## 6. Fix nginx resolver for Podman

The default `nginx.conf` hardcodes a Podman DNS resolver IP (`10.89.0.1`) that may not match your network. Update the `resolver` line in `nginx/nginx.conf` to use your Podman DNS:

```bash
# Find your Podman DNS
cat /etc/resolv.conf  # look for nameserver in the 10.89.x.x range
# or check inside the container after first run:
podman exec nginx cat /etc/resolv.conf
```

Then edit `nginx/nginx.conf` and set:

```nginx
resolver <YOUR_PODMAN_DNS_IP> valid=30s ipv6=off;
```

---

## 7. Fix privileged port (rootless Podman)

Rootless Podman cannot bind to ports below 1024. In `docker-compose.yml`, change the nginx HTTP redirect port:

```yaml
# Before (will fail on rootless Podman)
ports:
  - "80:80"

# After
ports:
  - "8080:80"
```

---

## 8. Add `default` network for podman-compose

Podman-compose does not auto-create the implicit `default` network. Ensure the `networks:` block in `docker-compose.yml` includes it:

```yaml
networks:
  default:
    driver: bridge
  basyx-shared:
    driver: bridge
```

---

## 9. Configure Podman to use podman-compose

If `podman compose` tries to use Docker's `docker-compose` binary (wrong CPU architecture or not installed):

```bash
export COMPOSE_PROVIDER=podman-compose
```

Add to `~/.zshrc` (or `~/.bashrc`) to make it permanent:

```bash
echo 'export COMPOSE_PROVIDER=podman-compose' >> ~/.zshrc
source ~/.zshrc
```

---

## 10. Start the stack

```bash
podman-compose up -d
```

Verify all containers are running:

```bash
podman ps -a --format "table {{.Names}}\t{{.Status}}"
```

---

## Endpoints

| Service | URL |
|---------|-----|
| AAS Web UI | `https://<YOUR_IP>:8443` |
| AAS Environment API | `https://<YOUR_IP>:8443/shells` |
| Keycloak Admin | `https://<YOUR_IP>:9443` |
| HTTP redirect | `http://<YOUR_IP>:8080` |

> The self-signed certificate will trigger a browser warning. Click through to proceed.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `502 Bad Gateway` on UI/Keycloak | Check nginx resolver IP matches your Podman DNS (`podman exec nginx cat /etc/resolv.conf`) |
| `bad CPU type in executable` | You're running x86_64 terminal trying to execute an arm64 binary. Use `podman-compose` instead or run terminal natively |
| `port 80: permission denied` | Rootless Podman can't bind to ports <1024. Use port 8080+ |
| `missing networks: default` | Add `default` network to `networks:` block in `docker-compose.yml` |
| Container name already in use | `podman-compose down` then `podman rm -f <name>` for stuck containers |

## Endpoints
- AAS Environment: http://localhost:8082
- AAS Web UI: http://localhost:3000

## Notes
- The generated setup includes a sample RSA private key at `basyx/rsa-key.pem`.
- Infrastructure connections for the UI are defined in `basyx-infra.yml`.
- Place your own AAS files into the `aas/` folder or upload through the UI.