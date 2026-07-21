# FIBRO Digital Product Passport

This project contains a public Digital Product Passport viewer for the FIBROTOR
ER.15, an AAS generator, and a secured Eclipse BaSyx infrastructure.

## DPP Viewer MVP

The responsive Next.js viewer is in `frontend/`. Product values are mapped from
`data/generated/final_basyx_aas_environment.json`, allowing the public product
experience to work without authentication or a live BaSyx query. Missing and
explicitly unavailable values are omitted. The stock BaSyx UI remains available
for infrastructure inspection.

Run the complete stack:

```bash
docker compose up -d --build
```

Then open:

- DPP viewer: http://localhost:3000
- Stock BaSyx UI: http://localhost:3001
- Secured gateway: https://localhost:8443

For frontend-only development on a machine with Node.js 24:

```bash
cd frontend
npm install
npm run dev
```

The product data boundary is `frontend/lib/product/product-api.ts`; replace its
generated-JSON reader with BaSyx discovery and repository calls later. The import
boundary is `frontend/lib/import/import-api.ts`. Its live implementation sends
`multipart/form-data` to `POST /api/admin/import` using the field name `file`.
Admin authentication is isolated in `frontend/lib/auth/admin-auth.ts`. A
`dpp-viewer` PKCE client is prepared in Keycloak, but the MVP uses an explicit
mock admin session until server-side session handling and the import endpoint
are connected.

## Generate the AAS

Create a virtual environment and install the project:

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

Run the complete local pipeline from any directory inside the repository:

```bash
.venv/bin/python generate_aas.py
```

Use `--project-root /path/to/alexia` when running from outside the repository.

The command discovers the project root relative to the current directory and uses:

- `data/input/` for the source workbook;
- `data/templates/` for IDTA templates;
- `data/assets/` for supplementary files referenced by AAS `File` elements;
- `data/generated/` for one `output_*.json` file per workbook sheet, the final
  environment JSON, and the AASX package.

Useful options:

```bash
# Generate JSON without creating an AASX package
.venv/bin/python generate_aas.py --no-aasx

# Write artifacts somewhere else
.venv/bin/python generate_aas.py --output-dir /tmp/dpp-output

# Generate and upload with an admin OIDC access token (automation only)
OIDC_ACCESS_TOKEN=... .venv/bin/python generate_aas.py \
  --upload \
  --ca-certificate security/certs/gateway.crt
```

Uploading is deliberately opt-in and requires an admin OIDC access token. Pass a URL
after `--upload` to use a server other than
`https://localhost:8443/upload`. `--insecure` is available only for local
certificate troubleshooting.

## Code Layout

- `dpp_aas/workbook.py` reads the table-shaped workbook data from `data/input`.
- `dpp_aas/templates.py` fills and normalizes IDTA templates.
- `dpp_aas/environment.py` assembles the product AAS environment.
- `dpp_aas/aasx.py` validates and packages assets into an AASX.
- `dpp_aas/client.py` provides the single client for the secured BaSyx API.
- `dpp_aas/pipeline.py` coordinates the complete workflow.
- `dpp_aas/cli.py` provides the command-line interface.

Carbon-footprint placeholder declarations live in
`dpp_aas/config.py:DPP_VALUE_DISCLOSURES`. They preserve the official field
semantics and datatype while adding explicit AAS qualifiers that mark values as
non-authoritative placeholders.

## Empty Values

The generator treats the workbook's `Actual Value`, `Obligation`, and field
structure as follows:

- an empty optional element or branch is omitted;
- every populated workbook leaf is emitted, including workbook fields for which
  an IDTA template only provides an `Arbitrary*` prototype;
- custom field names are converted to valid AAS `idShort` values while their
  exact workbook labels are retained as `displayName`;
- an empty mandatory leaf receives an unmistakable
  `DUMMY — MANDATORY VALUE MISSING` value and `DppValueStatus=Dummy` qualifier;
- mandatory leaves inside inactive optional branches are collected in an
  `UnresolvedMandatoryWorkbookValues` collection rather than silently omitted;
- example-column values are never presented as actual product data.

Workbook tables and repeated sections are retained as separate records during
generation. In particular, repeated handover documents are emitted as distinct
list items rather than being merged by `idShort`.

## Tests

```bash
.venv/bin/python -m unittest discover -v
```

## Local BaSyx Stack

Create local secrets and replace every `replace-with-...` value:

```bash
cp .env.example .env
```

Start the secured BaSyx components:

```bash
docker compose up -d --build
```

Endpoints:

- Secured AAS API: https://localhost:8443
- AAS Registry through gateway: https://localhost:8443/registry/aas
- Submodel Registry through gateway:
  https://localhost:8443/registry/submodels
- Public DPP viewer: http://localhost:3000
- AAS Web UI: http://localhost:3001

The gateway generates a local TLS certificate in `security/certs/`. Open
`https://localhost:8443/gateway/health` once and trust the local certificate.
Then open the AAS Web UI on port 3001. It redirects to Keycloak at
`https://localhost:8443/auth/realms/basyx/protocol/openid-connect/auth` and
returns to the UI after login.

## Authentication And Roles

The browser uses OAuth 2.0 authorization-code flow with PKCE. Keycloak owns
the login page; the Web UI never receives a password. The gateway validates
the access token signature against Keycloak's JWKS endpoint, then checks the
token issuer, intended API audience, expiry, and realm role.

- `admin` / `admin` has unrestricted GET, POST, PUT, PATCH, and DELETE access.
- `client` / `client` can use GET and HEAD only. Write attempts receive HTTP 403.
- Missing, expired, or invalid tokens receive HTTP 401.

Both accounts use the same browser UI. Editing and uploading are available to
the UI so administrators can manage AASX files. A client may see these controls
but cannot complete a write because the gateway rejects it with HTTP 403.
For automation, pass a short-lived OIDC access token to `AASClient` or the
`--access-token` command-line option; static API keys are no longer accepted.

The two passwords above are deliberately simple local-demo credentials. Change
or remove the users in `security/keycloak/realm-basyx.json` before any shared
deployment. The UI is served over HTTP only for local development; place it
behind HTTPS with a real hostname and certificate in a deployed environment.

The BaSyx repositories and registries are not published directly to the host,
so the gateway cannot be bypassed. All programmatic API access uses the same
`AASClient` and HTTPS gateway.

## Public distributed AAS read

The FIBROTOR ER.15 shell ID is:

```text
https://www.fibrort.com/downloads?product=25/aas
```

An exact shell lookup and its exact Registry descriptor lookup are public and
read-only. Collection reads, submodels, uploads, and every write operation stay
behind the existing OAuth gateway. For local use, set these values in `.env`:

```dotenv
PUBLIC_GATEWAY_URL=https://localhost:8443
PUBLIC_AAS_BASE_URL=https://localhost:8443
```

Recreate the AAS Environment and gateway so newly registered descriptors use
the public endpoint, then upload the generated package if the repository is
empty:

```bash
docker compose up -d --build --force-recreate aas-environment security-gateway
OIDC_ACCESS_TOKEN=... .venv/bin/python generate_aas.py --upload --ca-certificate security/certs/gateway.crt
```

Test local discovery and retrieval through the Registry (the second command
also saves the returned shell):

```bash
python scripts/test_distributed_aas.py https://localhost:8443/registry/aas/shell-descriptors 'https://www.fibrort.com/downloads?product=25/aas' --insecure
python scripts/test_distributed_aas.py https://localhost:8443/registry/aas/shell-descriptors 'https://www.fibrort.com/downloads?product=25/aas' --insecure --output /tmp/fibrotor-er15-shell.json
```

For deployment, set `PUBLIC_AAS_BASE_URL=https://aas.fredcharbonnier.com`,
recreate `aas-environment`, and route both `/api/shells/` and the public exact
descriptor path `/registry/aas/shell-descriptors/` to the security gateway on
`127.0.0.1:8443`. Preserve the path and query string. The gateway itself limits
anonymous access to GET, HEAD, and OPTIONS on exact instance URLs.

For example, the relevant Nginx locations are:

```nginx
location /api/shells/ {
    proxy_pass https://127.0.0.1:8443;
    proxy_ssl_verify off; # only when the gateway uses its local self-signed cert
}

location /registry/aas/shell-descriptors/ {
    proxy_pass https://127.0.0.1:8443;
    proxy_ssl_verify off; # remove when the upstream certificate is trusted
}
```

Remote test:

```bash
python scripts/test_distributed_aas.py https://aas.fredcharbonnier.com/registry/aas/shell-descriptors 'https://www.fibrort.com/downloads?product=25/aas'
```

For production, use a CA-issued certificate, restrict CORS and Keycloak redirect
origins, store the Keycloak bootstrap secret outside Compose, and manage users
and roles through your identity provider rather than the imported demo realm.
