import copy
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .config import ENVIRONMENT_ORDER, TemplateSpec


def build_environment(
    generated: dict[str, dict[str, Any]],
    specs: Iterable[TemplateSpec],
) -> tuple[dict[str, Any], str]:
    specs_by_slug = {spec.slug: spec for spec in specs}
    nameplate = generated["digital-nameplate"]
    product_uri = _property_value(nameplate, "URIOfTheProduct")
    if not product_uri:
        raise ValueError("Digital Nameplate does not contain URIOfTheProduct")

    submodels: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for slug in ENVIRONMENT_ORDER:
        spec = specs_by_slug[slug]
        source_submodels = generated[slug].get("submodels", [])
        if not source_submodels:
            raise ValueError(f"{spec.output_filename} does not contain a submodel")

        submodel_id = f"{product_uri}/submodels/{slug}"
        submodel = copy.deepcopy(source_submodels[0])
        submodel["id"] = submodel_id
        submodel["idShort"] = spec.instance_id_short
        submodel["kind"] = "Instance"
        submodels.append(submodel)
        references.append(
            {
                "type": "ModelReference",
                "keys": [{"type": "Submodel", "value": submodel_id}],
            }
        )

    environment = {
        "assetAdministrationShells": [
            {
                "id": f"{product_uri}/aas",
                "idShort": "AssetAdministrationShell",
                "modelType": "AssetAdministrationShell",
                "assetInformation": {
                    "assetKind": "Instance",
                    "globalAssetId": product_uri,
                },
                "submodels": references,
            }
        ],
        "submodels": submodels,
        "conceptDescriptions": _merge_concept_descriptions(generated.values()),
    }
    return environment, product_uri


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(value, json_file, indent=2, ensure_ascii=False)
        json_file.write("\n")


def _property_value(environment: dict[str, Any], id_short: str) -> str | None:
    for submodel in environment.get("submodels", []):
        for element in _walk_elements(submodel.get("submodelElements", [])):
            if element.get("idShort") == id_short:
                value = element.get("value")
                return str(value) if value is not None else None
    return None


def _walk_elements(elements: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        nested = element.get("value")
        if element.get("modelType") in {
            "SubmodelElementCollection",
            "SubmodelElementList",
        } and isinstance(nested, list):
            yield from _walk_elements(nested)


def _merge_concept_descriptions(
    environments: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for environment in environments:
        for concept in environment.get("conceptDescriptions", []):
            concept_id = concept.get("id") or concept.get("idShort")
            if concept_id and concept_id not in merged:
                merged[concept_id] = copy.deepcopy(concept)
    return list(merged.values())
