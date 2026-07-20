from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORKBOOK_FILENAME = "DPP_FIBROTOR_ER15_V2.xlsx"
FINAL_ENVIRONMENT_FILENAME = "final_basyx_aas_environment.json"
DEFAULT_AASX_FILENAME = "finaltemplate.aasx"
DEFAULT_UPLOAD_URL = "https://localhost:8443/upload"
DATA_DIRECTORY = "data"
INPUT_DIRECTORY = "input"
TEMPLATE_DIRECTORY = "templates"
ASSET_DIRECTORY = "assets"
GENERATED_DIRECTORY = "generated"


@dataclass(frozen=True)
class TemplateSpec:
    sheet_name: str
    template_filename: str
    output_filename: str
    slug: str
    instance_id_short: str


TEMPLATE_SPECS = (
    TemplateSpec(
        sheet_name="Digital Nameplate",
        template_filename="IDTA 02006-3-0-1_Template_Digital Nameplate.json",
        output_filename="output_digital_nameplate.json",
        slug="digital-nameplate",
        instance_id_short="DigitalNameplate",
    ),
    TemplateSpec(
        sheet_name="Handover Documentation",
        template_filename="IDTA 02004-2-0_Template_HandoverDocumentation.json",
        output_filename="output_handover_documentation.json",
        slug="handover-documentation",
        instance_id_short="HandoverDocumentation",
    ),
    TemplateSpec(
        sheet_name="Technical Data",
        template_filename="IDTA 02003_Template_TechnicalData.json",
        output_filename="output_technical_data.json",
        slug="technical-data",
        instance_id_short="TechnicalData",
    ),
    TemplateSpec(
        sheet_name="Carbon Footprint",
        template_filename="IDTA 02023 _Template_CarbonFootprint.json",
        output_filename="output_carbon_footprint.json",
        slug="carbon-footprint",
        instance_id_short="CarbonFootprint",
    ),
    TemplateSpec(
        sheet_name="Maintenance Instructions",
        template_filename="IDTA_02018_Template_MaintenanceInstructions.json",
        output_filename="output_maintenance_instructions.json",
        slug="maintenance-instructions",
        instance_id_short="MaintenanceInstructions",
    ),
)

ENVIRONMENT_ORDER = (
    "carbon-footprint",
    "technical-data",
    "digital-nameplate",
    "handover-documentation",
    "maintenance-instructions",
)

DPP_VALUE_DISCLOSURES: dict[str, dict[str, dict[str, Any]]] = {
    "Carbon Footprint": {
        "ProductCarbonFootprints": {
            "status": "Placeholder",
            "reason": (
                "Product Carbon Footprint is not calculated for this product; "
                "values are prototype placeholders and are not authoritative DPP data."
            ),
        },
        "PcfCO2eq": {
            "value": 0.0,
            "status": "Placeholder",
            "reason": (
                "This CO2-equivalent value is a placeholder until a verified "
                "PCF calculation is available."
            ),
        },
    },
}


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for root in (current, *current.parents):
        workbook = root / DATA_DIRECTORY / INPUT_DIRECTORY / WORKBOOK_FILENAME
        if workbook.is_file():
            return root
    raise FileNotFoundError(
        f"Could not find data/input/{WORKBOOK_FILENAME!r} relative to {current}"
    )
