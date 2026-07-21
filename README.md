# DPP AAS Generator

This project converts the FIBROTOR Digital Product Passport workbook into
IDTA-based submodel JSON files, one combined AAS environment, and an AASX
package.

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

The generator treats the workbook's `Actual Value`, `Obligation`, and
`Example Value` columns as follows:

- an empty optional element or branch is omitted;
- an empty mandatory leaf uses a datatype-valid example when one exists;
- every substituted example is marked with `DppValueStatus=Placeholder` and a
  `DppValueStatusNote` qualifier;
- an empty mandatory leaf without a safe example is omitted and reported with
  its worksheet, table, and row number.

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
- AAS Web UI: http://localhost:3000

The gateway generates a local TLS certificate in `security/certs/`. Open
`https://localhost:8443/gateway/health` once and trust the local certificate.
Then open the web UI. It redirects to Keycloak at
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

For production, use a CA-issued certificate, restrict CORS and Keycloak redirect
origins, store the Keycloak bootstrap secret outside Compose, and manage users
and roles through your identity provider rather than the imported demo realm.
