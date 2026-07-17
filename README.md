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

# Generate and upload to the local BaSyx environment
.venv/bin/python generate_aas.py --upload
```

Uploading is deliberately opt-in. Pass a URL after `--upload` to use a server
other than `http://localhost:8081/upload`.

## Code Layout

- `dpp_aas/workbook.py` reads the table-shaped workbook data from `data/input`.
- `dpp_aas/templates.py` fills and normalizes IDTA templates.
- `dpp_aas/environment.py` assembles the product AAS environment.
- `dpp_aas/aasx.py` validates, packages assets, and optionally uploads the AASX.
- `dpp_aas/pipeline.py` coordinates the complete workflow.
- `dpp_aas/cli.py` provides the command-line interface.

Carbon-footprint placeholder declarations live in
`dpp_aas/config.py:DPP_VALUE_DISCLOSURES`. They preserve the official field
semantics and datatype while adding explicit AAS qualifiers that mark values as
non-authoritative placeholders.

## Tests

```bash
.venv/bin/python -m unittest discover -v
```

## Local BaSyx Stack

Start the BaSyx Go components and PostgreSQL:

```bash
docker compose up -d
```

Endpoints:

- AAS Environment: http://localhost:8081
- AAS Registry: http://localhost:8082
- Submodel Registry: http://localhost:8083
- AAS Web UI: http://localhost:3000

Infrastructure connections for the UI are defined in `basyx-infra.yml`.
