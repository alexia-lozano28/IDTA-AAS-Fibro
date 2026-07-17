from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .values import MISSING_MARKER


HEADER_LABEL = "Element Name (idShort)"
VALUE_LABEL = "Actual Value"
OBLIGATION_LABEL = "Obligation"


@dataclass(frozen=True)
class MissingField:
    sheet_name: str
    id_short: str

    def __str__(self) -> str:
        return f"{self.sheet_name} -> {self.id_short}"


@dataclass(frozen=True)
class WorkbookData:
    sheets: dict[str, dict[str, Any]]
    missing_mandatory: tuple[MissingField, ...]


def read_workbook(path: Path, sheet_names: Iterable[str]) -> WorkbookData:
    workbook = load_workbook(path, data_only=True, read_only=True)
    missing: list[MissingField] = []
    sheets: dict[str, dict[str, Any]] = {}

    for sheet_name in sheet_names:
        if sheet_name not in workbook.sheetnames:
            continue
        sheets[sheet_name] = extract_sheet_values(workbook[sheet_name], missing)

    workbook.close()
    return WorkbookData(sheets=sheets, missing_mandatory=tuple(missing))


def extract_sheet_values(
    sheet: Worksheet, missing: list[MissingField] | None = None
) -> dict[str, Any]:
    missing_log = missing if missing is not None else []
    rows = list(sheet.iter_rows(values_only=True))
    values: dict[str, Any] = {}
    row_index = 0

    while row_index < len(rows):
        row = rows[row_index]
        key_index = _column_index(row, HEADER_LABEL, contains=True)
        if key_index is None:
            row_index += 1
            continue

        value_index = _column_index(row, VALUE_LABEL)
        obligation_index = _column_index(row, OBLIGATION_LABEL)
        row_index += 1

        while row_index < len(rows):
            data_row = rows[row_index]
            if key_index >= len(data_row) or _is_empty(data_row[key_index]):
                break

            id_short = str(data_row[key_index]).strip()
            value = _cell(data_row, value_index)
            obligation = _cell(data_row, obligation_index)
            value = value.strip() if isinstance(value, str) else value

            if _is_empty(value):
                if _is_mandatory(obligation):
                    values[id_short] = MISSING_MARKER
                    missing_log.append(MissingField(sheet.title, id_short))
                else:
                    values[id_short] = None
            else:
                values[id_short] = value
            row_index += 1

    return values


def _column_index(
    row: tuple[Any, ...], label: str, *, contains: bool = False
) -> int | None:
    for index, cell in enumerate(row):
        if cell is None:
            continue
        text = str(cell).strip()
        if (contains and label in text) or (not contains and text == label):
            return index
    return None


def _cell(row: tuple[Any, ...], index: int | None) -> Any:
    return row[index] if index is not None and index < len(row) else None


def _is_empty(value: Any) -> bool:
    return value is None or str(value).strip() in {"", "N/A"}


def _is_mandatory(value: Any) -> bool:
    return value is not None and str(value).strip().lower().startswith("mandatory")
