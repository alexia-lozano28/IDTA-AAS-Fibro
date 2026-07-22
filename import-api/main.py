from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import JSONResponse
import tempfile
import shutil
import requests
from pathlib import Path
import client.client as AASClient
from dpp_aas.pipeline import run_pipeline

app = FastAPI(title="AAS Import API", version="1.0.0")

BASYX_URL = "http://aas-environment:8081"  # docker service name



app = FastAPI()

@app.get("/")
async def connect():
    return {
        "status": "connected",
    }

@app.post("/api/admin/import")
async def import_aas(
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    print("FILE:", file.filename)
    print("AUTH:", authorization[:30])

    temp_file = Path("/tmp") / file.filename

    with temp_file.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    result = run_pipeline(
        project_root=Path("/app"),
        workbook_path=temp_file,
        upload_url="https://security-gateway:8443/upload",
        upload_access_token=authorization.replace("Bearer ", ""),
        upload_verify=False,
    )


    return {
        "environment": str(result.environment_path),
        "aasx": str(result.aasx_path),
        "product_uri": result.product_uri,
        "upload_status": result.upload_status,
        "warnings": result.warnings,
        "missing_fields": [
            str(x)
            for x in result.missing_mandatory
        ]
    }