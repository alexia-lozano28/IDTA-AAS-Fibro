# FIBRO Digital Product Passport and BaSyx AAS environment

This repository is a proof of concept for the FIBROTOR ER.15 Digital Product
Passport. It contains:

- a responsive public Next.js product viewer;
- an XLSX-to-AAS generator using IDTA templates;
- an Eclipse BaSyx AAS Environment, AAS Registry and Submodel Registry;
- MongoDB persistence;
- Keycloak authentication;
- a TLS security gateway that applies authentication and role-based access;
- the stock Eclipse BaSyx Web UI for authenticated inspection and upload;
- a deliberately narrow anonymous endpoint for the public DPP use case.

This document is also intended to be sufficient context for an operator, API
consumer, or an LLM helping someone integrate with the running service.

## Current product identifiers

The real FIBROTOR ER.15 AAS identifier used by this project is:

```text
https://www.fibrort.com/downloads?product=25/aas
```

BaSyx API path parameters use unpadded Base64URL encoding of the UTF-8
identifier. The encoded AAS identifier is:

```text
aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz
```

Encode any AAS or Submodel ID with:

```bash
python3 -c 'import base64; value="https://example.com/my-aas"; print(base64.urlsafe_b64encode(value.encode()).decode().rstrip("="))'
```

Do not URL-encode the original identifier and do not retain Base64 padding
characters (`=`).

## Copyable API integration brief

The following is the minimum accurate context to give another developer or an
LLM that needs to build an API integration:

```text
The service is an Eclipse BaSyx AAS Environment behind a custom HTTPS OAuth2
gateway. The intended remote base URL is https://aas.fredcharbonnier.com and
the local base URL is https://localhost:8443. The Keycloak realm is "basyx".

Only GET /api/shells/{unpadded-base64url-aas-id} is anonymous. Registry,
raw /shells, /submodels, /concept-descriptions, uploads and writes require an
Authorization: Bearer <access-token> header.

Read integrations use OAuth2 client credentials:
- token endpoint: {base}/auth/realms/basyx/protocol/openid-connect/token
- client_id: aas-read-client
- client_secret: supplied out of band
- grant_type: client_credentials
- permissions: GET/HEAD only; writes return 403

The FIBROTOR ER.15 AAS ID is:
https://www.fibrort.com/downloads?product=25/aas

Its unpadded Base64URL ID is:
aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz

AAS descriptor:
GET {base}/registry/aas/shell-descriptors/{encoded-aas-id}

Raw shell:
GET {base}/shells/{encoded-aas-id}

Submodel descriptor:
GET {base}/registry/submodels/submodel-descriptors/{encoded-submodel-id}

Raw Submodel:
GET {base}/submodels/{encoded-submodel-id}

IDs must be UTF-8 encoded with URL-safe Base64 and trailing '=' padding removed.
Local TLS is self-signed; production TLS must be verified normally.
```

## Architecture and trust boundary

All external API traffic passes through `security-gateway`. The gateway:

- terminates HTTPS;
- validates Keycloak JWT signatures, issuer, audience and expiry;
- maps the `admin` and `client` realm roles;
- permits read-only tokens to use GET, HEAD and OPTIONS;
- permits admin tokens to use reads and writes;
- proxies authenticated requests to the private BaSyx services;
- permits one exact anonymous route: `GET /api/shells/{encoded-aas-id}`.

MongoDB, the AAS Environment, both registries, Keycloak and the underlying Web
UI container do not publish raw ports to the network. Only loopback-bound ports
are exposed by Compose:

| Port | Service | Purpose |
| --- | --- | --- |
| `3000` | Custom DPP viewer | Public presentation frontend |
| `3001` | Stock BaSyx UI wrapper | Interactive OAuth login and BaSyx management |
| `8443` | Security gateway | HTTPS API, Registry and Keycloak routes |

The gateway routes requests internally to:

- `aas-environment:8081` for shells, Submodels, concept descriptions and AASX uploads;
- `aas-registry:8080` for AAS discovery and descriptors;
- `submodel-registry:8080` for Submodel descriptors;
- `keycloak:8080` for `/auth`.

## Public and protected API matrix

Only the curated shell-instance route is anonymous. Everything else requires a
Bearer token unless noted otherwise.

| Route | Anonymous | Read-only token | Admin token |
| --- | --- | --- | --- |
| `GET /api/shells/{encoded-id}` | Yes | Yes | Yes |
| `/registry/aas/**` | No | GET/HEAD | Full access |
| `/registry/submodels/**` | No | GET/HEAD | Full access |
| `/shells/**` | No | GET/HEAD | Full access |
| `/submodels/**` | No | GET/HEAD | Full access |
| `/concept-descriptions/**` | No | GET/HEAD | Full access |
| `/api/submodels/**` | No | GET/HEAD | Full access |
| `/api/concept-descriptions/**` | No | GET/HEAD | Full access |
| `POST /upload` | No | 403 | Allowed |
| `/auth/**` | OAuth endpoint | OAuth endpoint | OAuth endpoint |
| `GET /gateway/health` | Yes | Yes | Yes |

The authenticated `/api/submodels` and `/api/concept-descriptions` aliases are
intentional. BaSyx uses one external base URL when it generates Registry
descriptors. The gateway removes the `/api` prefix before forwarding these
protected requests to the AAS Environment. Only an exact, valid Base64URL shell
instance under `/api/shells/` receives the anonymous exception.

Expected authentication errors:

- HTTP 401: no token, invalid token, expired token, wrong issuer or wrong audience;
- HTTP 403: valid token without a recognized role, or a read-only token attempting a write;
- HTTP 404: the encoded resource does not exist or the wrong repository route was used.

## Quick start

Requirements:

- Docker with Docker Compose;
- Python 3.10 or newer for scripts and generation;
- Node.js 24 only when running the frontend outside Docker.

Create local configuration:

```bash
cp .env.example .env
```

Replace every `replace-with-...` value in `.env`, especially:

```dotenv
MONGODB_ROOT_PASSWORD=replace-with-a-long-random-password
KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD=replace-with-a-long-random-password
AAS_READ_CLIENT_SECRET=replace-with-a-long-random-machine-client-secret
```

Local browser-facing URLs must not end with a slash:

```dotenv
PUBLIC_GATEWAY_URL=https://localhost:8443
PUBLIC_AAS_BASE_URL=https://localhost:8443
```

Start everything:

```bash
docker compose up -d --build
docker compose ps
```

Open:

- custom DPP viewer: http://localhost:3000
- stock BaSyx UI: http://localhost:3001
- gateway health: https://localhost:8443/gateway/health

The gateway generates a local certificate in `security/certs/`. For browser
development, open the health URL once and accept or trust that certificate.
Command examples use `--insecure` only for this local self-signed certificate.
Never use `--insecure` against the deployed service.

## Authentication model

The Keycloak realm is `basyx`. Its API audience is `basyx-api`.

### Browser users

The stock BaSyx UI uses OAuth 2.0 authorization code flow with PKCE through the
public `basyx-web-ui` client. Keycloak receives the password; the UI does not.

Local demonstration accounts imported with the realm are:

- `admin` / `admin`: realm role `admin`, read and write access;
- `client` / `client`: realm role `client`, read-only access.

These credentials are intentionally unsafe demo defaults. Change or remove
them before sharing a deployment.

The custom frontend has a separate public PKCE client named `dpp-viewer`; its
standalone Admin Upload page still uses a mock session. The working XLSX import
flow is currently integrated into the stock BaSyx UI and reuses that UI's real
`basyx-web-ui` access token.

### Read-only machine client

API integrations use the confidential client `aas-read-client`. It has:

- client authentication by secret;
- service accounts enabled;
- client-credentials grant enabled;
- only the `client` realm role;
- a `basyx-api` audience mapper;
- no browser standard flow and no password/direct-access grant.

Its secret comes from `AAS_READ_CLIENT_SECRET` at Keycloak realm import time.
Do not send this secret to browsers, commit it, paste it into tickets, or expose
it in logs.

The browser clients cannot use client credentials. The read-only machine client
cannot upload, edit or delete resources.

### Admin automation

There is intentionally no confidential admin machine client in this proof of
concept. Administrative actions are supported through the PKCE-authenticated
BaSyx UI. Python upload code can accept an admin access token through
`OIDC_ACCESS_TOKEN`, but obtaining and managing such a token is currently an
external operator responsibility.

Do not enable the Resource Owner Password Credentials/direct-access grant as a
shortcut. If non-interactive write automation is required, create a separate
confidential service client, assign only the necessary write role, rotate its
secret, and audit its use.

## Obtain a read-only access token

Define local variables:

```bash
export AAS_API_BASE_URL='https://localhost:8443'
export AAS_READ_CLIENT_SECRET='the-value-from-your-dot-env-file'
```

Request a token:

```bash
curl --insecure --request POST \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=aas-read-client' \
  --data-urlencode "client_secret=${AAS_READ_CLIENT_SECRET}" \
  "${AAS_API_BASE_URL}/auth/realms/basyx/protocol/openid-connect/token" \
  --output /tmp/aas-token.json
```

Check for token-endpoint errors before continuing:

```bash
python3 -m json.tool /tmp/aas-token.json
```

Load the access token into the current shell without printing it:

```bash
export AAS_ACCESS_TOKEN="$(python3 -c 'import json; print(json.load(open("/tmp/aas-token.json"))["access_token"])')"
```

Access tokens are short-lived. Request a new token after expiry; do not persist
one as application configuration.

## API workflow: anonymous public shell

No token is required for the curated DPP shell route:

```bash
export ENCODED_AAS_ID='aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz'

curl --insecure \
  "https://localhost:8443/api/shells/${ENCODED_AAS_ID}"
```

This returns only the shell JSON. Following its Submodel references requires an
authenticated token. Anonymous Registry enumeration and raw repository access
are deliberately unavailable.

Remote form:

```bash
curl \
  'https://aas.fredcharbonnier.com/api/shells/aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz'
```

Use the remote hostname only after DNS, TLS and reverse proxy deployment are
complete.

## API workflow: authenticated Registry discovery

Obtain `AAS_ACCESS_TOKEN` as described above, then fetch the exact AAS Registry
descriptor:

```bash
export ENCODED_AAS_ID='aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz'

curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/registry/aas/shell-descriptors/${ENCODED_AAS_ID}" \
  --output /tmp/aas-descriptor.json
```

Extract the advertised shell endpoint:

```bash
export SHELL_ENDPOINT="$(python3 -c 'import json; print(json.load(open("/tmp/aas-descriptor.json"))["endpoints"][0]["protocolInformation"]["href"])')"
```

Fetch it. Supplying the token is harmless even when the descriptor advertises
the curated anonymous shell endpoint:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${SHELL_ENDPOINT}" \
  --output /tmp/aas-shell.json
```

Fetch from the protected raw shell repository instead:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/shells/${ENCODED_AAS_ID}"
```

List shell descriptors or repository shells:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/registry/aas/shell-descriptors"

curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/shells"
```

## API workflow: fetch Submodels

The shell JSON contains Submodel references with original identifiers. Encode a
Submodel ID using the same unpadded Base64URL rule.

Example for the Technical Data Submodel:

```bash
export SUBMODEL_ID='https://www.fibrort.com/downloads?product=25/submodels/technical-data'
export ENCODED_SUBMODEL_ID="$(python3 -c 'import base64,os; value=os.environ["SUBMODEL_ID"]; print(base64.urlsafe_b64encode(value.encode()).decode().rstrip("="))')"
```

Fetch its Registry descriptor:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/registry/submodels/submodel-descriptors/${ENCODED_SUBMODEL_ID}" \
  --output /tmp/submodel-descriptor.json
```

Fetch the raw Submodel or all its elements:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/submodels/${ENCODED_SUBMODEL_ID}"

curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/submodels/${ENCODED_SUBMODEL_ID}/submodel-elements"
```

Registry descriptors may advertise `/api/submodels/{encoded-id}`. That URL is
also valid, but remains authenticated:

```bash
curl --insecure --fail-with-body \
  --header "Authorization: Bearer ${AAS_ACCESS_TOKEN}" \
  "${AAS_API_BASE_URL}/api/submodels/${ENCODED_SUBMODEL_ID}"
```

## Automated Registry-to-shell test

The standard-library-only test script obtains a client-credentials token,
encodes the supplied AAS ID, resolves its descriptor, follows the advertised
endpoint and prints a short summary:

```bash
python3 scripts/test_distributed_aas.py \
  https://localhost:8443/registry/aas/shell-descriptors \
  'https://www.fibrort.com/downloads?product=25/aas' \
  --token-url https://localhost:8443/auth/realms/basyx/protocol/openid-connect/token \
  --client-id aas-read-client \
  --client-secret "$AAS_READ_CLIENT_SECRET" \
  --insecure \
  --output /tmp/fibrotor-er15-shell.json
```

Remote form:

```bash
python3 scripts/test_distributed_aas.py \
  https://aas.fredcharbonnier.com/registry/aas/shell-descriptors \
  'https://www.fibrort.com/downloads?product=25/aas' \
  --token-url https://aas.fredcharbonnier.com/auth/realms/basyx/protocol/openid-connect/token \
  --client-id aas-read-client \
  --client-secret "$AAS_READ_CLIENT_SECRET" \
  --output /tmp/fibrotor-er15-shell.json
```

## Stock BaSyx Web UI workflow

1. Open `https://localhost:8443/gateway/health` and trust the local certificate.
2. Open http://localhost:3001.
3. Sign in through Keycloak as `admin` for uploads/edits or `client` for reads.
4. Open the AAS navigation dropdown. After **AAS SM Visualizations**, select
   **Upload XLSX as AAS**. This item is rendered only for an `admin` token.
5. Choose a completed `.xlsx` product workbook and select
   **Generate and upload AAS**. The authenticated request runs the complete
   workbook-to-JSON-to-AASX pipeline and posts the AASX to BaSyx.
6. Review any generation warnings, then close and refresh the AAS list.
7. Select the shell. The UI resolves AAS and Submodel Registry descriptors and
   follows the advertised `/api/shells` and authenticated `/api/submodels` URLs.

The UI visibility check is only a convenience. `POST /api/admin/import` is
protected by the gateway: no token receives HTTP 401 and a read-only token
receives HTTP 403 before the import service is called.

If shells load but every Submodel reports “Submodel not found,” inspect gateway
logs for `/api/submodels/...` responses. These advertised aliases must be
handled by the gateway and must return 200 for authenticated users:

```bash
docker compose logs --tail=200 security-gateway
```

After changing Keycloak configuration, sign out and back in so the UI obtains a
new token. After changing frontend configuration, use a hard browser refresh.

## Generate the FIBROTOR AAS

Create a Python environment and install the project:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Generate the complete environment JSON and AASX package:

```bash
.venv/bin/python generate_aas.py
```

Inputs and outputs:

- `data/input/`: source XLSX workbook;
- `data/templates/`: IDTA JSON templates used for structure;
- `data/assets/`: supplementary files included in or referenced by the AAS;
- `data/generated/output_*.json`: generated Submodels;
- `data/generated/final_basyx_aas_environment.json`: complete environment;
- `data/generated/finaltemplate.aasx`: generated upload package.

Useful options:

```bash
# Generate JSON without AASX packaging.
.venv/bin/python generate_aas.py --no-aasx

# Override the output directory.
.venv/bin/python generate_aas.py --output-dir /tmp/dpp-output

# Run from outside the repository.
.venv/bin/python generate_aas.py --project-root /path/to/IDTA-AAS-Fibro
```

The workbook is the source of truth. Populated workbook leaves are preserved,
including fields that only correspond to arbitrary template prototypes. Empty
optional fields are omitted. Empty mandatory leaves receive an explicit
`DUMMY — MANDATORY VALUE MISSING` value and a `DppValueStatus=Dummy` qualifier.
Template example values are never presented as real product data.

## Upload an AASX

### Convert and upload an XLSX through the BaSyx UI

The private `import-api` container accepts a multipart request routed through
the security gateway:

```text
POST /api/admin/import
Authorization: Bearer <admin-access-token>
Content-Type: multipart/form-data
file: <workbook.xlsx>
```

It accepts `.xlsx` only, defaults to a 20 MiB limit, uses a unique temporary
workspace, calls the repository's `run_pipeline()`, uploads the generated AASX
through the authenticated gateway, and deletes temporary artifacts when the
request finishes. It is not published on a host port.

Successful responses include `aasId`, `productUri`, `uploadStatus`, `warnings`
and `missingMandatory`. Workbook validation errors return HTTP 422. The request
is synchronous and uses `GATEWAY_UPSTREAM_TIMEOUT` (180 seconds by default).

### Recommended interactive upload

Use the stock BaSyx UI on port 3001 while signed in as `admin`. The gateway
authorizes `POST /upload`, and BaSyx registers the uploaded shells and Submodels.

External files referenced by URL may produce “Skipped external file URL”
warnings during upload. These warnings do not mean that the AASX upload failed.

### Upload with an existing admin token

If an operator has supplied a valid access token containing the `admin` realm
role and `basyx-api` audience:

```bash
export OIDC_ACCESS_TOKEN='short-lived-admin-access-token'

.venv/bin/python generate_aas.py \
  --upload \
  --ca-certificate security/certs/gateway.crt
```

For local certificate troubleshooting only:

```bash
.venv/bin/python generate_aas.py --upload --insecure
```

Upload an already generated package directly:

```bash
curl --insecure --fail-with-body \
  --request POST \
  --header "Authorization: Bearer ${OIDC_ACCESS_TOKEN}" \
  --form 'file=@data/generated/finaltemplate.aasx;type=application/octet-stream' \
  'https://localhost:8443/upload'
```

A read-only `aas-read-client` token receives HTTP 403 from this endpoint.

After changing `PUBLIC_AAS_BASE_URL`, recreate the AAS Environment and re-upload
or update the AAS. Registry descriptors are persisted when resources are
registered; restarting alone may not rewrite existing descriptor endpoints.

## Custom DPP frontend

The custom responsive viewer lives in `frontend/` and runs on port 3000. It
currently maps product data from:

```text
data/generated/final_basyx_aas_environment.json
```

The data adapter is `frontend/lib/product/product-api.ts`. Missing values are not
invented or displayed. The real product image comes from `data/assets/product.png`.

For frontend-only development with Node.js 24:

```bash
cd frontend
npm install
npm run dev
```

The standalone custom frontend page still uses its mock adapter. Its live
request boundary matches the implemented service—`multipart/form-data`,
`POST /api/admin/import`, field name `file`—but its independent Keycloak session
must be completed before enabling that page. The stock BaSyx UI integration is
the supported authenticated entry point for now.

The visual palette is defined in `frontend/app/theme.css`, including the FIBRO
orange brand variables.

## Deployment

Recommended external value:

```dotenv
PUBLIC_GATEWAY_URL=https://aas.fredcharbonnier.com
PUBLIC_AAS_BASE_URL=https://aas.fredcharbonnier.com
AAS_READ_CLIENT_SECRET=replace-with-a-production-secret
```

`PUBLIC_GATEWAY_URL` controls Keycloak issuer URLs and authenticated UI/API
configuration. `PUBLIC_AAS_BASE_URL` controls the endpoints BaSyx advertises in
Registry descriptors. Neither value should have a trailing slash.

Recreate affected services after changing them:

```bash
docker compose up -d --build --force-recreate keycloak aas-environment security-gateway web-ui
```

If the realm already exists in a persistent or externally managed Keycloak,
startup import may use `IGNORE_EXISTING`. Create or update `aas-read-client`
manually with service accounts enabled, assign its service-account user only
the `client` realm role, and include the `basyx-api` audience in access tokens.

The external reverse proxy must forward all gateway paths, including:

- `/api/shells/`;
- `/api/submodels/`;
- `/registry/aas/`;
- `/registry/submodels/`;
- `/shells/`;
- `/submodels/`;
- `/concept-descriptions/`;
- `/upload`;
- `/auth/`;
- `/gateway/health`.

The safest configuration proxies the entire hostname to the loopback-bound
gateway, preserving the original path, query string, host and scheme:

```nginx
server {
    listen 443 ssl;
    server_name aas.fredcharbonnier.com;

    # Configure the public certificate and key here.
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass https://127.0.0.1:8443;

        # Only necessary while the internal gateway uses its generated cert.
        proxy_ssl_verify off;
    }
}
```

Do not proxy directly to MongoDB, `aas-environment`, either Registry, Keycloak,
or the underlying Web UI container. Do not publish their Docker ports.

Before production use:

- use CA-issued public TLS;
- use strong, separately managed secrets;
- remove or change demo users and passwords;
- restrict CORS from its current development wildcard;
- update Keycloak redirect URIs and web origins for deployed UI hostnames;
- use persistent/external Keycloak storage and a production Keycloak mode;
- rotate the machine-client secret;
- add audit logging, backups, monitoring and rate limiting;
- decide whether public shell JSON requires caching or abuse protection.

## Tests and operational checks

Run the Python test suite after installing dependencies:

```bash
.venv/bin/python -m unittest discover -v
```

Validate Compose:

```bash
docker compose config --quiet
```

Inspect health and logs:

```bash
docker compose ps
curl --insecure https://localhost:8443/gateway/health
docker compose logs --tail=200 security-gateway keycloak aas-environment aas-registry submodel-registry
```

Check that the intended authentication boundary is intact:

```bash
# Expected: 200
curl --insecure --output /dev/null --write-out '%{http_code}\n' \
  "https://localhost:8443/api/shells/${ENCODED_AAS_ID}"

# Expected: 401 without a token
curl --insecure --output /dev/null --write-out '%{http_code}\n' \
  "https://localhost:8443/registry/aas/shell-descriptors/${ENCODED_AAS_ID}"

# Expected: 401 without a token
curl --insecure --output /dev/null --write-out '%{http_code}\n' \
  "https://localhost:8443/api/submodels/${ENCODED_SUBMODEL_ID}"
```

## Code layout

- `generate_aas.py`: convenient generator entry point;
- `dpp_aas/workbook.py`: reads structured workbook tables;
- `dpp_aas/templates.py`: binds workbook data into IDTA structures;
- `dpp_aas/environment.py`: assembles the AAS environment;
- `dpp_aas/aasx.py`: validates and packages the AASX;
- `dpp_aas/client.py`: authenticated BaSyx API client;
- `dpp_aas/pipeline.py`: coordinates generation and optional upload;
- `dpp_aas/security_gateway.py`: TLS proxy, JWT validation, authorization and routing;
- `scripts/test_distributed_aas.py`: client-credentials Registry-to-shell test;
- `security/keycloak/realm-basyx.json`: demo realm, clients, roles and users;
- `security/basyx-infra.yml.template`: generated Web UI infrastructure configuration;
- `config/aas-environment/application.properties`: BaSyx persistence and Registry integration;
- `frontend/`: custom DPP viewer;
- `data/input/`, `data/templates/`, `data/assets/`, `data/generated/`: source and generated product data.
