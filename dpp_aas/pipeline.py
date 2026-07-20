from dataclasses import dataclass
from pathlib import Path

from .aasx import upload_aasx, write_aasx
from .config import (
    ASSET_DIRECTORY,
    DATA_DIRECTORY,
    DEFAULT_AASX_FILENAME,
    DPP_VALUE_DISCLOSURES,
    FINAL_ENVIRONMENT_FILENAME,
    GENERATED_DIRECTORY,
    INPUT_DIRECTORY,
    TEMPLATE_SPECS,
    TEMPLATE_DIRECTORY,
    WORKBOOK_FILENAME,
)
from .environment import build_environment, write_json
from .templates import clear_unavailable_local_files, instantiate_template
from .workbook import MissingField, read_workbook


@dataclass(frozen=True)
class GenerationResult:
    environment_path: Path
    aasx_path: Path | None
    product_uri: str
    generated_files: tuple[Path, ...]
    missing_mandatory: tuple[MissingField, ...]
    warnings: tuple[str, ...]
    upload_status: int | None = None


def run_pipeline(
    project_root: Path,
    *,
    workbook_path: Path | None = None,
    template_dir: Path | None = None,
    asset_dir: Path | None = None,
    output_dir: Path | None = None,
    aasx_path: Path | None = None,
    create_aasx: bool = True,
    upload_url: str | None = None,
) -> GenerationResult:
    project_root = project_root.resolve()
    data_root = project_root / DATA_DIRECTORY
    workbook_path = (
        workbook_path or data_root / INPUT_DIRECTORY / WORKBOOK_FILENAME
    ).resolve()
    template_dir = (template_dir or data_root / TEMPLATE_DIRECTORY).resolve()
    asset_dir = (asset_dir or data_root / ASSET_DIRECTORY).resolve()
    output_dir = (output_dir or data_root / GENERATED_DIRECTORY).resolve()

    required_sheets = (spec.sheet_name for spec in TEMPLATE_SPECS)
    workbook_data = read_workbook(workbook_path, required_sheets)

    generated: dict[str, dict] = {}
    generated_paths: list[Path] = []
    missing_mandatory: list[MissingField] = []
    warnings: list[str] = []
    for spec in TEMPLATE_SPECS:
        if spec.sheet_name not in workbook_data.sheets:
            warnings.append(f"Skipped missing worksheet {spec.sheet_name!r}")
            continue

        environment, template_warnings, template_missing = instantiate_template(
            template_dir / spec.template_filename,
            workbook_data.sheets[spec.sheet_name],
            DPP_VALUE_DISCLOSURES.get(spec.sheet_name),
        )
        missing_mandatory.extend(template_missing)
        warnings.extend(
            f"{spec.sheet_name}: {warning}" for warning in template_warnings
        )
        for submodel in environment.get("submodels", []):
            warnings.extend(
                f"{spec.sheet_name}: {warning}"
                for warning in clear_unavailable_local_files(
                    submodel.get("submodelElements", []), asset_dir
                )
            )

        output_path = output_dir / spec.output_filename
        write_json(output_path, environment)
        generated[spec.slug] = environment
        generated_paths.append(output_path)

    missing_outputs = {spec.slug for spec in TEMPLATE_SPECS} - generated.keys()
    if missing_outputs:
        raise ValueError(
            "Cannot build the final environment; missing generated submodels: "
            + ", ".join(sorted(missing_outputs))
        )

    final_environment, product_uri = build_environment(generated, TEMPLATE_SPECS)
    environment_path = output_dir / FINAL_ENVIRONMENT_FILENAME
    write_json(environment_path, final_environment)

    resolved_aasx_path: Path | None = None
    if create_aasx:
        resolved_aasx_path = (
            aasx_path.resolve()
            if aasx_path
            else output_dir / DEFAULT_AASX_FILENAME
        )
        write_aasx(environment_path, resolved_aasx_path, asset_dir)

    upload_status = None
    if upload_url:
        if resolved_aasx_path is None:
            raise ValueError("AASX generation must be enabled when uploading")
        upload_status = upload_aasx(resolved_aasx_path, upload_url).status_code
        

    return GenerationResult(
        environment_path=environment_path,
        aasx_path=resolved_aasx_path,
        product_uri=product_uri,
        generated_files=tuple(generated_paths),
        missing_mandatory=tuple(missing_mandatory),
        warnings=tuple(warnings),
        upload_status=upload_status,
    )
