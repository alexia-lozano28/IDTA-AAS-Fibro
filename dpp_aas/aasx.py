import json
import mimetypes
from pathlib import Path
from typing import Any

import requests
from basyx.aas import model
from basyx.aas.adapter import json as aas_json
from basyx.aas.adapter.aasx import AASXWriter, DictSupplementaryFileContainer

from .templates import iter_file_elements


def write_aasx(
    environment_path: Path,
    aasx_path: Path,
    asset_dir: Path,
) -> None:
    with environment_path.open(encoding="utf-8") as environment_file:
        object_store = aas_json.read_aas_json_file(environment_file)

    aas_ids = [
        item.id
        for item in object_store
        if isinstance(item, model.AssetAdministrationShell)
    ]
    if not aas_ids:
        raise ValueError(f"No Asset Administration Shell found in {environment_path}")

    file_store = DictSupplementaryFileContainer()
    with environment_path.open(encoding="utf-8") as environment_file:
        raw_environment: dict[str, Any] = json.load(environment_file)

    for submodel in raw_environment.get("submodels", []):
        for element in iter_file_elements(submodel.get("submodelElements", [])):
            value = str(element["value"])
            local_path = asset_dir / value.lstrip("/")
            if not local_path.is_file():
                continue
            content_type = element.get("contentType") or (
                mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
            )
            with local_path.open("rb") as supplementary_file:
                file_store.add_file(value, supplementary_file, content_type)

    aasx_path.parent.mkdir(parents=True, exist_ok=True)
    with AASXWriter(aasx_path) as writer:
        writer.write_aas(
            aas_ids=aas_ids,
            object_store=object_store,
            file_store=file_store,
        )


def upload_aasx(
    aasx_path: Path,
    upload_url: str,
    *,
    access_token: str,
    verify: bool | str = True,
    timeout: float = 30,
) -> requests.Response:
    with aasx_path.open("rb") as aasx_file:
        response = requests.post(
            upload_url,
            files={
                "file": (
                    aasx_path.name,
                    aasx_file,
                    "application/octet-stream",
                )
            },
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            verify=verify,
            timeout=timeout,
        )
    response.raise_for_status()
    return response
