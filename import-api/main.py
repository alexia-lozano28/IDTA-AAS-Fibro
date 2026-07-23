import logging
import os
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile

from dpp_aas.pipeline import run_pipeline


LOGGER = logging.getLogger("aas-import-api")
CHUNK_SIZE = 1024 * 1024
MAX_FILE_BYTES = int(os.getenv("IMPORT_MAX_FILE_BYTES", str(20 * 1024 * 1024)))
UPLOAD_URL = os.getenv(
    "IMPORT_UPLOAD_URL", "https://security-gateway:8443/upload"
)
UPLOAD_VERIFY: bool | str = os.getenv("IMPORT_UPLOAD_VERIFY", "true")
if isinstance(UPLOAD_VERIFY, str):
    normalized_verify = UPLOAD_VERIFY.strip().lower()
    if normalized_verify in {"false", "0", "no"}:
        UPLOAD_VERIFY = False
    elif normalized_verify in {"true", "1", "yes"}:
        UPLOAD_VERIFY = True

app = FastAPI(title="FIBRO XLSX to AAS import service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/admin/import")
def import_workbook(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    x_authenticated_role: str = Header(...),
) -> dict[str, object]:
    if x_authenticated_role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="A Bearer access token is required")

    original_name = Path(file.filename or "upload.xlsx").name
    if Path(original_name).suffix.lower() != ".xlsx":
        raise HTTPException(
            status_code=415,
            detail="Only .xlsx product workbooks can be converted to an AAS",
        )

    import_id = str(uuid.uuid4())
    try:
        with tempfile.TemporaryDirectory(prefix="aas-import-") as temp_directory:
            workspace = Path(temp_directory)
            workbook_path = workspace / "product.xlsx"
            _save_upload(file, workbook_path)

            output_directory = workspace / "generated"
            aasx_path = workspace / "generated.aasx"
            result = run_pipeline(
                project_root=Path("/app"),
                workbook_path=workbook_path,
                output_dir=output_directory,
                aasx_path=aasx_path,
                upload_url=UPLOAD_URL,
                upload_access_token=token.strip(),
                upload_verify=UPLOAD_VERIFY,
            )
    except HTTPException:
        raise
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        upstream_status = exc.response.status_code if exc.response else None
        LOGGER.warning("BaSyx upload failed with status %s", upstream_status)
        raise HTTPException(
            status_code=502,
            detail=f"AAS generation succeeded but BaSyx upload failed ({upstream_status or 'unknown status'})",
        ) from exc
    except Exception as exc:
        LOGGER.exception("Import %s failed", import_id)
        raise HTTPException(
            status_code=500,
            detail="The workbook could not be converted and uploaded",
        ) from exc
    finally:
        file.file.close()

    aas_id = f"{result.product_uri}/aas"
    return {
        "success": True,
        "importId": import_id,
        "fileName": original_name,
        "message": "Workbook converted to AASX and uploaded to BaSyx.",
        "productUri": result.product_uri,
        "aasId": aas_id,
        "uploadStatus": result.upload_status,
        "warnings": list(result.warnings),
        "missingMandatory": [str(item) for item in result.missing_mandatory],
    }


def _save_upload(file: UploadFile, destination: Path) -> None:
    total = 0
    signature = b""
    with destination.open("wb") as output:
        while chunk := file.file.read(CHUNK_SIZE):
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Workbook exceeds the {MAX_FILE_BYTES} byte upload limit",
                )
            if not signature:
                signature = chunk[:4]
            output.write(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="The uploaded workbook is empty")
    if not signature.startswith(b"PK"):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid XLSX package")
