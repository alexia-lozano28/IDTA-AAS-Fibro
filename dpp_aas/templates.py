import copy
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .values import MISSING_MARKER, coerce_value


COLLECTION_MODELS = {"SubmodelElementCollection", "SubmodelElementList"}
DISCLOSURE_TYPES = {"DppValueStatus", "DppValueStatusNote"}


def instantiate_template(
    template_path: Path,
    values: dict[str, Any],
    disclosures: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    with template_path.open(encoding="utf-8") as template_file:
        environment = json.load(template_file)

    submodels = environment.get("submodels", [])
    if not submodels:
        raise ValueError(f"Template has no submodels: {template_path}")

    warnings: list[str] = []
    elements = submodels[0].get("submodelElements", [])
    fill_elements(elements, values, warnings=warnings)
    apply_value_disclosures(elements, disclosures or {})
    normalize_elements(elements, warnings)
    return environment, warnings


def fill_elements(
    elements: Iterable[dict[str, Any]],
    values: dict[str, Any],
    *,
    path: tuple[str, ...] = (),
    warnings: list[str] | None = None,
) -> None:
    warning_log = warnings if warnings is not None else []
    for element in elements:
        if not isinstance(element, dict):
            continue

        model_type = element.get("modelType")
        id_short = element.get("idShort")
        current_path = path + ((id_short,) if id_short else ())
        value = _lookup_value(values, current_path, id_short)

        try:
            _fill_element_value(element, model_type, value)
        except ValueError as exc:
            warning_log.append(f"{'.'.join(current_path) or '<unnamed>'}: {exc}")
            element.pop("value", None)

        nested = element.get("value")
        if model_type in COLLECTION_MODELS and isinstance(nested, list):
            fill_elements(nested, values, path=current_path, warnings=warning_log)


def apply_value_disclosures(
    elements: Iterable[dict[str, Any]],
    disclosures: dict[str, dict[str, Any]],
) -> None:
    for element in elements:
        if not isinstance(element, dict):
            continue

        disclosure = disclosures.get(element.get("idShort"))
        if disclosure:
            if "value" in disclosure and element.get("modelType") == "Property":
                value_type = element.get("valueType", "xs:string")
                element["value"] = coerce_value(disclosure["value"], value_type)

            qualifiers = [
                qualifier
                for qualifier in element.get("qualifiers", [])
                if qualifier.get("type") not in DISCLOSURE_TYPES
            ]
            qualifiers.extend(
                [
                    {
                        "type": "DppValueStatus",
                        "valueType": "xs:string",
                        "value": disclosure["status"],
                    },
                    {
                        "type": "DppValueStatusNote",
                        "valueType": "xs:string",
                        "value": disclosure["reason"],
                    },
                ]
            )
            element["qualifiers"] = qualifiers

        nested = element.get("value")
        if element.get("modelType") in COLLECTION_MODELS and isinstance(nested, list):
            apply_value_disclosures(nested, disclosures)


def normalize_elements(
    elements: list[dict[str, Any]], warnings: list[str] | None = None
) -> None:
    """Normalize known template constructs for AAS v3 instance compatibility."""
    warning_log = warnings if warnings is not None else []
    _make_sibling_ids_unique(elements, warning_log)

    for element in elements:
        if not isinstance(element, dict):
            continue
        _deduplicate_qualifiers(element, warning_log)
        _normalize_reference(element.get("semanticId"), warning_log)

        nested = element.get("value")
        if element.get("modelType") not in COLLECTION_MODELS or not isinstance(nested, list):
            continue

        if element["modelType"] == "SubmodelElementList":
            for child in nested:
                if isinstance(child, dict) and child.pop("idShort", None) is not None:
                    warning_log.append(
                        f"Removed idShort from direct child of list {element.get('idShort')!r}"
                    )
        normalize_elements(nested, warning_log)


def clear_unavailable_local_files(
    elements: Iterable[dict[str, Any]], asset_dir: Path
) -> list[str]:
    warnings: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue

        if element.get("modelType") == "File" and element.get("value"):
            value = str(element["value"])
            if not _is_remote_reference(value):
                local_path = asset_dir / value.lstrip("/")
                if not local_path.is_file():
                    element.pop("value", None)
                    warnings.append(
                        f"Cleared unavailable supplementary file {value!r} "
                        f"from {element.get('idShort')!r}"
                    )

        nested = element.get("value")
        if element.get("modelType") in COLLECTION_MODELS and isinstance(nested, list):
            warnings.extend(clear_unavailable_local_files(nested, asset_dir))
    return warnings


def iter_file_elements(
    elements: Iterable[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("modelType") == "File" and element.get("value"):
            yield element
        nested = element.get("value")
        if element.get("modelType") in COLLECTION_MODELS and isinstance(nested, list):
            yield from iter_file_elements(nested)


def _lookup_value(
    values: dict[str, Any], path: tuple[str, ...], id_short: str | None
) -> Any:
    path_key = ".".join(path)
    if path_key and path_key in values:
        return values[path_key]
    return values.get(id_short) if id_short else None


def _fill_element_value(
    element: dict[str, Any], model_type: str | None, value: Any
) -> None:
    if value == MISSING_MARKER:
        element.pop("value", None)
        return
    if value is None:
        return

    if model_type == "Property":
        coerced = coerce_value(value, element.get("valueType", "xs:string"))
        if coerced is not None:
            element["value"] = coerced
    elif model_type == "MultiLanguageProperty":
        element["value"] = [{"language": "en", "text": str(value)}]
    elif model_type == "File":
        text = str(value).strip()
        if _looks_like_file_reference(text):
            element["value"] = text
        else:
            raise ValueError(f"{text!r} is explanatory text, not a file reference")
    elif model_type == "Range":
        if isinstance(value, dict):
            element["min"] = str(value.get("min", ""))
            element["max"] = str(value.get("max", ""))
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            element["min"], element["max"] = map(str, value)


def _looks_like_file_reference(value: str) -> bool:
    if _is_remote_reference(value) or value.startswith("/"):
        return True
    return "." in Path(value).name


def _is_remote_reference(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https"}


def _deduplicate_qualifiers(
    element: dict[str, Any], warnings: list[str]
) -> None:
    qualifiers = element.get("qualifiers")
    if not isinstance(qualifiers, list):
        return

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for qualifier in qualifiers:
        qualifier_type = qualifier.get("type")
        if qualifier_type in seen:
            warnings.append(
                f"Removed duplicate qualifier {qualifier_type!r} "
                f"from {element.get('idShort')!r}"
            )
            continue
        if qualifier_type:
            seen.add(qualifier_type)
        unique.append(qualifier)
    element["qualifiers"] = unique


def _normalize_reference(reference: Any, warnings: list[str]) -> None:
    if not isinstance(reference, dict):
        return
    keys = reference.get("keys")
    if reference.get("type") != "ModelReference" or not isinstance(keys, list):
        return
    if not any(key.get("type") == "Identifiable" for key in keys):
        return

    reference["type"] = "ExternalReference"
    for key in keys:
        if key.get("type") == "Identifiable":
            key["type"] = "GlobalReference"
    warnings.append("Converted legacy Identifiable semantic reference to ExternalReference")


def _make_sibling_ids_unique(
    elements: list[dict[str, Any]], warnings: list[str]
) -> None:
    counts: dict[str, int] = {}
    for element in elements:
        if not isinstance(element, dict) or not element.get("idShort"):
            continue
        original = element["idShort"]
        counts[original] = counts.get(original, 0) + 1
        if counts[original] == 1:
            continue
        element["idShort"] = f"{original}__{counts[original]:02d}__"
        warnings.append(
            f"Renamed duplicate sibling idShort {original!r} "
            f"to {element['idShort']!r}"
        )
