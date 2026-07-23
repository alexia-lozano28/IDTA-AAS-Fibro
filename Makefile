UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
SED_INPLACE := sed -i ''
_HOST_IP = $(shell \
	ipconfig getifaddr en0 2>/dev/null || \
	ipconfig getifaddr en1 2>/dev/null || \
	echo "127.0.0.1")
else
SED_INPLACE := sed -i
_HOST_IP = $(shell \
	ip route get 1 2>/dev/null | sed -n 's/.*src \([0-9.]*\).*/\1/p' || \
	echo "127.0.0.1")
endif

HOST_IP ?= $(_HOST_IP)

COMPOSE_FILE = docker-compose.yml
NGINX_CONF = nginx/nginx.conf
KC_REALM = keycloak/realm-export.json
BASYX_INFRA = basyx-infra.yml
APPLICATION_PROPERTIES = basyx/application.properties
PLACEHOLDER_IP = 192.168.56.212
CONFIG_FILES = $(COMPOSE_FILE) $(BASYX_INFRA) $(NGINX_CONF) $(KC_REALM) $(APPLICATION_PROPERTIES)

DETECTED_DC = $(shell \
	if command -v podman-compose >/dev/null 2>&1; then \
		echo "podman-compose -f $(COMPOSE_FILE)"; \
	elif docker compose version >/dev/null 2>&1; then \
		echo "docker compose -f $(COMPOSE_FILE)"; \
	else \
		echo "docker-compose -f $(COMPOSE_FILE)"; \
	fi)

.PHONY: help setup env env-force _generate_env certs dirs update-ip build up down restart \
        status ps logs health-check health clean purge \
        _check_compose _check_openssl

help:
	@echo "BaSyx Digital Twin Infrastructure - Makefile"
	@echo ""
	@echo "  setup              Full setup: dirs + env (random passwords) + certs + update-ip"
	@echo "  env                Create .env with auto-detected IP and random passwords"
	@echo "  env-force          Regenerate .env (overwrites existing)"
	@echo "  certs              Generate self-signed SSL certificates (uses .env IP)"
	@echo "  dirs               Create required directories (aas/, nginx/certs/)"
	@echo "  update-ip          Replace placeholder IP with .env HOST_IP in config files"
	@echo ""
	@echo "  build              Pull/build container images"
	@echo "  up                 Start the stack (detached)"
	@echo "  down               Stop and remove containers"
	@echo "  restart            Restart the stack"
	@echo "  status             Show container status"
	@echo "  ps                 Alias for status"
	@echo "  logs [svc]         View logs (optional: service name)"
	@echo ""
	@echo "  health-check       Run health checks on all services"
	@echo "  health             Alias for health-check"
	@echo ""
	@echo "  clean              Stop stack + remove containers and volumes"
	@echo "  purge              Clean + remove certs, aas/ files, and .env"
	@echo ""
	@echo "  HOST_IP=            Override auto-detected IP (e.g. HOST_IP=10.0.0.5)"
	@echo ""
	@echo "Examples:"
	@echo "  make setup          # auto-detect IP, random passwords, full setup"
	@echo "  make up"
	@echo "  make logs svc=nginx"

# ── Helpers ──────────────────────────────────────────────────

_check_compose:
	@$(DETECTED_DC) ps >/dev/null 2>&1 || { \
		echo "ERROR: No compose command available. Install podman-compose or docker-compose."; \
		exit 1; \
	}

_check_openssl:
	@command -v openssl >/dev/null 2>&1 || { \
		echo "ERROR: openssl is required but not installed."; \
		echo "  Linux:  sudo apt install openssl  (or brew, yum, etc.)"; \
		echo "  macOS:  already bundled (or: brew install openssl)"; \
		exit 1; \
	}

# ── Setup ────────────────────────────────────────────────────

setup: dirs env certs update-ip
	@echo ""
	@echo "Setup complete. Run 'make up' to start the stack."

env: _check_openssl
	@if [ -f .env ]; then \
		echo ".env already exists. Use 'make env-force' to overwrite."; \
	else \
		$(MAKE) _generate_env; \
	fi

env-force: _check_openssl
	@rm -f .env && $(MAKE) _generate_env

_generate_env:
	@echo "Detecting machine IP..."; \
	if [ "$(UNAME_S)" = "Darwin" ]; then \
		ip=$$(ipconfig getifaddr en0 2>/dev/null); \
		[ -z "$$ip" ] && ip=$$(ipconfig getifaddr en1 2>/dev/null); \
	else \
		ip=$$(ip route get 1 2>/dev/null | sed -n 's/.*src \([0-9.]*\).*/\1/p'); \
	fi; \
	[ -z "$$ip" ] && ip="127.0.0.1"; \
	echo "  IP: $$ip"; \
	echo "Generating random passwords..."; \
	mongo_pw=$$(openssl rand -base64 16 | tr -d '=' | tr '/+' '_-'); \
	kc_db_pw=$$(openssl rand -base64 16 | tr -d '=' | tr '/+' '_-'); \
	kc_admin_pw=$$(openssl rand -base64 16 | tr -d '=' | tr '/+' '_-'); \
	{ \
		echo "HOST_IP=$$ip"; \
		echo "MONGO_USERNAME=admin"; \
		echo "MONGO_PASSWORD=$$mongo_pw"; \
		echo "KC_DB_USERNAME=keycloak"; \
		echo "KC_DB_PASSWORD=$$kc_db_pw"; \
		echo "KC_BOOTSTRAP_ADMIN_USERNAME=admin"; \
		echo "KC_BOOTSTRAP_ADMIN_PASSWORD=$$kc_admin_pw"; \
	} > .env; \
	echo ".env created with random credentials."

certs: env _check_openssl
	@mkdir -p nginx/certs; \
	if [ ! -f nginx/certs/server.crt ]; then \
		. ./.env; \
		echo "Generating self-signed SSL certificates for $$HOST_IP..."; \
		openssl req -x509 -nodes -days 365 \
			-newkey rsa:2048 \
			-keyout nginx/certs/server.key \
			-out nginx/certs/server.crt \
			-subj "/CN=$$HOST_IP" \
			-addext "subjectAltName=IP:$$HOST_IP" 2>/dev/null; \
		echo "Certificates created in nginx/certs/."; \
	else \
		echo "Certificates already exist (nginx/certs/server.crt)."; \
	fi

dirs:
	@mkdir -p aas nginx/certs
	@echo "Directories ready: aas/, nginx/certs/"

# ── IP Configuration ─────────────────────────────────────────

update-ip: env
	@. ./.env && \
	echo "Updating placeholder IP ($(PLACEHOLDER_IP)) -> $$HOST_IP in config files..." && \
	$(SED_INPLACE) 's/$(PLACEHOLDER_IP)/'"$$HOST_IP"'/g' $(CONFIG_FILES) && \
	echo "IP updated in: $(CONFIG_FILES)"

# ── Stack Lifecycle ─────────────────────────────────────────

build: _check_compose
	$(DETECTED_DC) pull
	$(DETECTED_DC) build

up: _check_compose env
	$(DETECTED_DC) up -d
	@. ./.env && { \
		echo ""; \
		echo "Stack started. Check status with 'make status'."; \
		echo "Endpoints:"; \
		echo "  AAS Web UI:           https://$$HOST_IP:8443"; \
		echo "  AAS Environment API:  https://$$HOST_IP:8443/shells"; \
		echo "  Keycloak Admin:       https://$$HOST_IP:9443"; \
		echo "  HTTP Redirect:        http://$$HOST_IP:8080"; \
	}

down: _check_compose
	$(DETECTED_DC) down

restart: down up

status ps: _check_compose
	$(DETECTED_DC) ps

logs: _check_compose
	$(DETECTED_DC) logs --tail=50 -f $(svc)

# ── Health ───────────────────────────────────────────────────

health-check health: _check_compose
	@. ./.env 2>/dev/null || true; \
	ip=$${HOST_IP:-$(HOST_IP)}; \
	echo "=== Service Status ==="; \
	$(DETECTED_DC) ps; \
	echo ""; \
	echo "=== Health Endpoints ==="; \
	echo "  AAS Environment:  curl -sk https://$$ip:8443/shells"; \
	echo "  Keycloak:         curl -sk https://$$ip:9443/health/ready"; \
	echo "  Registry:         curl -s  http://$$ip:8083/actuator/health"; \
	echo "  MongoDB:          $(DETECTED_DC) exec mongo mongosh --quiet --eval \"db.adminCommand('ping')\""; \
	echo "  Keycloak DB:      $(DETECTED_DC) exec keycloak-db pg_isready -U \$${KC_DB_USERNAME}"; \
	echo "  Kafka:            $(DETECTED_DC) exec kafka kafka-topics --bootstrap-server localhost:9092 --list"

# ── Cleanup ──────────────────────────────────────────────────

clean: _check_compose
	$(DETECTED_DC) down -v --remove-orphans
	@echo "Stack stopped, containers and volumes removed."

purge: clean
	@rm -rf aas/ nginx/certs/
	@rm -f .env
	@echo "All generated files and directories removed."
