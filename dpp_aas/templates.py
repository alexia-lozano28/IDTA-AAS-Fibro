import ast
import copy
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .values import coerce_value
from .workbook import (
    FieldRecord,
    MissingField,
    SheetData,
    TableRecord,
    is_empty,
    normalize_name,
)


COLLECTION_MODELS = {"SubmodelElementCollection", "SubmodelElementList"}
DISCLOSURE_TYPES = {"DppValueStatus", "DppValueStatusNote"}
PLACEHOLDER_NOTE = (
    "No actual value was supplied in the DPP workbook. This value comes from "
    "the workbook's Example Value column and is not authoritative product data."
)
UNSAFE_EXAMPLE_PREFIXES = (
    "see section",
    "list containing",
    "collection instance",
    "nested ",
    "subsection",
    "sub-collection",
    "sub-list",
)


@dataclass(frozen=True)
class _BindingContext:
    document_index: int | None = None


class _TemplateBinder:
    def __init__(self, sheet: SheetData) -> None:
        self.sheet = sheet
        self.warnings: list[str] = []
        self.missing: list[MissingField] = []

    def bind(self, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._bind_elements(
            elements, self.sheet.root_table, _BindingContext(), ()
        )

    def _bind_elements(
        self,
        elements: Iterable[dict[str, Any]],
        scope: TableRecord,
        context: _BindingContext,
        path: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        bound: list[dict[str, Any]] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            result = self._bind_element(
                copy.deepcopy(element), scope, context, path
            )
            if result is not None:
                bound.append(result)
        return bound

    def _bind_element(
        self,
        element: dict[str, Any],
        scope: TableRecord,
        context: _BindingContext,
        path: tuple[str, ...],
        record_override: FieldRecord | None = None,
    ) -> dict[str, Any] | None:
        model_type = element.get("modelType")
        id_short = element.get("idShort")
        current_path = path + ((id_short,) if id_short else ())
        record = record_override or self._field_for_element(scope, element)

        if model_type not in COLLECTION_MODELS:
            return self._bind_leaf(element, record, current_path)

        if record is not None and record.optional and not record.has_actual_value:
            return None

        if model_type == "SubmodelElementList":
            return self._bind_list(element, record, scope, context, current_path)

        child_scope = self._collection_scope(element, scope, context)
        nested = element.get("value")
        element["value"] = self._bind_elements(
            nested if isinstance(nested, list) else [],
            child_scope,
            context,
            current_path,
        )
        return element

    def _bind_list(
        self,
        element: dict[str, Any],
        record: FieldRecord | None,
        scope: TableRecord,
        context: _BindingContext,
        path: tuple[str, ...],
    ) -> dict[str, Any] | None:
        prototype_values = element.get("value")
        prototypes = prototype_values if isinstance(prototype_values, list) else []
        if not prototypes:
            element["value"] = []
            return element

        list_id = element.get("idShort", "")
        if self.sheet.name == "Handover Documentation" and list_id == "Documents":
            count = max(1, len(self.sheet.named_tables("DocumentId")))
            document_scope = self._first_named_table("Document") or scope
            element["value"] = [
                item
                for index in range(count)
                for item in self._bind_elements(
                    prototypes,
                    document_scope,
                    _BindingContext(document_index=index),
                    path,
                )
            ]
            return element

        item_tables = self._list_item_tables(element, prototypes[0])
        selected_tables = self._select_tables(item_tables, context)
        if selected_tables:
            items: list[dict[str, Any]] = []
            for item_scope in selected_tables:
                if not self._list_item_is_active(item_scope, list_id):
                    continue
                items.extend(
                    self._bind_elements(prototypes, item_scope, context, path)
                )
            element["value"] = items
            return element

        if self._is_primitive_list(prototypes):
            item_record = self._primitive_list_record(record, scope, list_id)
            values, used_example = self._primitive_values(item_record)
            if values is None:
                return None if record is None or record.optional else element

            items = []
            for value in values:
                item = self._bind_element(
                    copy.deepcopy(prototypes[0]),
                    scope,
                    context,
                    path,
                    record_override=_with_actual_value(item_record, value),
                )
                if item is not None:
                    if used_example:
                        _add_placeholder_qualifiers(item, PLACEHOLDER_NOTE)
                    items.append(item)
            element["value"] = items
            if used_example:
                _add_placeholder_qualifiers(element, PLACEHOLDER_NOTE)
            return element

        element["value"] = self._bind_elements(prototypes, scope, context, path)
        return element

    def _bind_leaf(
        self,
        element: dict[str, Any],
        record: FieldRecord | None,
        path: tuple[str, ...],
    ) -> dict[str, Any] | None:
        _clear_template_payload(element)
        if record is None:
            return None
        if record.has_actual_value:
            value = record.actual_value
            used_example = False
            if (
                isinstance(value, date)
                and element.get("modelType") == "Property"
                and "date" not in element.get("valueType", "").lower()
            ):
                self.warnings.append(
                    f"{'.'.join(path) or record.id_short}: workbook row "
                    f"{record.row_number} contains an Excel date for non-date "
                    f"datatype {element.get('valueType', 'xs:string')}"
                )
        elif record.optional:
            return None
        elif record.mandatory and _safe_example(record.example_value):
            value = _normalize_example(record.example_value)
            used_example = True
        else:
            self.missing.append(
                MissingField(
                    sheet_name=record.sheet_name,
                    table_name=record.table_name,
                    row_number=record.row_number,
                    id_short=record.id_short,
                    reason="no datatype-valid Example Value is available",
                )
            )
            return None

        try:
            if not _fill_element_value(element, value):
                self.warnings.append(
                    f"{'.'.join(path) or record.id_short}: "
                    f"cannot bind workbook values to {element.get('modelType')}"
                )
                return None
        except ValueError as exc:
            source = "example" if used_example else "actual"
            self.warnings.append(
                f"{'.'.join(path) or record.id_short}: invalid {source} value: {exc}"
            )
            if used_example:
                self.missing.append(
                    MissingField(
                        sheet_name=record.sheet_name,
                        table_name=record.table_name,
                        row_number=record.row_number,
                        id_short=record.id_short,
                        reason=f"Example Value is invalid for the template datatype: {exc}",
                    )
                )
            return None

        if used_example:
            _add_placeholder_qualifiers(element, PLACEHOLDER_NOTE)
        return element

    def _field_for_element(
        self, scope: TableRecord, element: dict[str, Any]
    ) -> FieldRecord | None:
        id_short = element.get("idShort")
        if id_short:
            return scope.field(id_short)
        if len(scope.fields) == 1:
            return scope.fields[0]
        return None

    def _collection_scope(
        self,
        element: dict[str, Any],
        fallback: TableRecord,
        context: _BindingContext,
    ) -> TableRecord:
        id_short = element.get("idShort")
        if not id_short:
            return fallback
        tables = self.sheet.named_tables(id_short)
        selected = self._select_tables(tables, context)
        return selected[0] if selected else fallback

    def _list_item_tables(
        self, element: dict[str, Any], prototype: dict[str, Any]
    ) -> tuple[TableRecord, ...]:
        names: list[str] = []
        prototype_id = prototype.get("idShort")
        list_id = element.get("idShort")
        if prototype_id:
            names.append(prototype_id)
        if list_id:
            names.extend([list_id, _singularize(list_id)])

        for name in names:
            tables = self.sheet.named_tables(name)
            if tables:
                return tables
        return ()

    def _select_tables(
        self, tables: tuple[TableRecord, ...], context: _BindingContext
    ) -> tuple[TableRecord, ...]:
        if context.document_index is not None and len(tables) > 1:
            index = context.document_index
            return (tables[index],) if index < len(tables) else ()
        return tables

    def _list_item_is_active(self, table: TableRecord, list_id: str) -> bool:
        marker = next(
            (
                field
                for field in table.fields
                if normalize_name(field.id_short) == normalize_name(list_id)
            ),
            None,
        )
        if marker is None or not marker.optional or marker.has_actual_value:
            return True
        return any(
            field.has_actual_value
            for field in table.fields
            if field is not marker
        )

    def _primitive_list_record(
        self,
        parent_record: FieldRecord | None,
        scope: TableRecord,
        list_id: str,
    ) -> FieldRecord | None:
        singular = _singularize(list_id)
        return scope.field(singular) or parent_record

    def _primitive_values(
        self, record: FieldRecord | None
    ) -> tuple[list[Any] | None, bool]:
        if record is None:
            return None, False
        if record.has_actual_value:
            raw_value = record.actual_value
            used_example = False
        elif record.optional:
            return None, False
        elif record.mandatory and _safe_example(record.example_value):
            raw_value = record.example_value
            used_example = True
        else:
            self.missing.append(
                MissingField(
                    sheet_name=record.sheet_name,
                    table_name=record.table_name,
                    row_number=record.row_number,
                    id_short=record.id_short,
                    reason="no datatype-valid Example Value is available",
                )
            )
            return None, False

        if isinstance(raw_value, str):
            try:
                parsed = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                parsed = raw_value
        else:
            parsed = raw_value
        return (list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]), used_example

    @staticmethod
    def _is_primitive_list(prototypes: list[dict[str, Any]]) -> bool:
        return len(prototypes) == 1 and prototypes[0].get("modelType") not in {
            "SubmodelElementCollection",
            "SubmodelElementList",
        }

    def _first_named_table(self, name: str) -> TableRecord | None:
        tables = self.sheet.named_tables(name)
        return tables[0] if tables else None


def instantiate_template(
    template_path: Path,
    sheet: SheetData,
    disclosures: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str], list[MissingField]]:
    with template_path.open(encoding="utf-8") as template_file:
        environment = json.load(template_file)

    submodels = environment.get("submodels", [])
    if not submodels:
        raise ValueError(f"Template has no submodels: {template_path}")

    binder = _TemplateBinder(sheet)
    elements = submodels[0].get("submodelElements", [])
    submodels[0]["submodelElements"] = binder.bind(elements)
    apply_value_disclosures(
        submodels[0]["submodelElements"], disclosures or {}
    )
    normalize_elements(submodels[0]["submodelElements"], binder.warnings)
    return environment, binder.warnings, binder.missing


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
            _add_placeholder_qualifiers(
                element,
                disclosure["reason"],
                status=disclosure.get("status", "Placeholder"),
            )

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


def _fill_element_value(element: dict[str, Any], value: Any) -> bool:
    model_type = element.get("modelType")
    if model_type == "Property":
        coerced = coerce_value(value, element.get("valueType", "xs:string"))
        if coerced is not None:
            element["value"] = coerced
        return True
    if model_type == "MultiLanguageProperty":
        element["value"] = [{"language": "en", "text": str(value)}]
        return True
    if model_type == "File":
        text = str(value).strip().strip('"')
        if not _looks_like_file_reference(text):
            raise ValueError(f"{text!r} is explanatory text, not a file reference")
        element["value"] = text
        return True
    if model_type == "Range":
        if isinstance(value, dict):
            element["min"] = str(value.get("min", ""))
            element["max"] = str(value.get("max", ""))
            return True
        if isinstance(value, (list, tuple)) and len(value) == 2:
            element["min"], element["max"] = map(str, value)
            return True
        raise ValueError(f"{value!r} is not a min/max range")
    return False


def _safe_example(value: Any) -> bool:
    if is_empty(value):
        return False
    if not isinstance(value, str):
        return True
    normalized = value.strip().strip('"').lower()
    return not normalized.startswith(UNSAFE_EXAMPLE_PREFIXES)


def _normalize_example(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        return stripped[1:-1]
    return value


def _clear_template_payload(element: dict[str, Any]) -> None:
    element.pop("value", None)
    element.pop("min", None)
    element.pop("max", None)


def _add_placeholder_qualifiers(
    element: dict[str, Any], reason: str, *, status: str = "Placeholder"
) -> None:
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
                "value": status,
            },
            {
                "type": "DppValueStatusNote",
                "valueType": "xs:string",
                "value": reason,
            },
        ]
    )
    element["qualifiers"] = qualifiers


def _with_actual_value(record: FieldRecord | None, value: Any) -> FieldRecord:
    if record is None:
        raise ValueError("A primitive list value has no workbook field record")
    return FieldRecord(
        sheet_name=record.sheet_name,
        table_name=record.table_name,
        row_number=record.row_number,
        id_short=record.id_short,
        obligation=record.obligation,
        field_type=record.field_type,
        example_value=record.example_value,
        actual_value=value,
    )


def _singularize(value: str) -> str:
    if value.endswith("ies"):
        return value[:-3] + "y"
    if value.endswith("s"):
        return value[:-1]
    return value


def _looks_like_file_reference(value: str) -> bool:
    if _is_remote_reference(value) or value.startswith("/"):
        return True
    suffix = Path(value).suffix
    return bool(suffix and len(suffix) > 1 and "\n" not in value)


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
