import json
import tempfile
import unittest
from pathlib import Path

from basyx.aas import model
from basyx.aas.adapter import json as aas_json

from dpp_aas.config import find_project_root
from dpp_aas.pipeline import run_pipeline


class PipelineIntegrationTests(unittest.TestCase):
    def test_real_workbook_generates_parseable_five_submodel_environment(self) -> None:
        project_root = find_project_root(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = run_pipeline(
                project_root,
                output_dir=Path(temporary_directory),
                create_aasx=False,
            )

            with result.environment_path.open(encoding="utf-8") as environment_file:
                object_store = aas_json.read_aas_json_file(environment_file)

            self.assertEqual(
                1,
                sum(
                    isinstance(item, model.AssetAdministrationShell)
                    for item in object_store
                ),
            )
            self.assertEqual(
                5, sum(isinstance(item, model.Submodel) for item in object_store)
            )

            carbon_path = Path(temporary_directory) / "output_carbon_footprint.json"
            with carbon_path.open(encoding="utf-8") as carbon_file:
                carbon = json.load(carbon_file)
            pcf_value = _find_element(
                carbon["submodels"][0]["submodelElements"], "PcfCO2eq"
            )
            self.assertEqual("0.0", pcf_value["value"])
            self.assertTrue(
                any(
                    qualifier.get("type") == "DppValueStatus"
                    and qualifier.get("value") == "Placeholder"
                    for qualifier in pcf_value["qualifiers"]
                )
            )

            digital = _read_output(
                Path(temporary_directory), "output_digital_nameplate.json"
            )
            digital_elements = digital["submodels"][0]["submodelElements"]
            self.assertNotIn(
                "ManufacturerProductRoot",
                {element.get("idShort") for element in digital_elements},
            )
            technical = _read_output(
                Path(temporary_directory), "output_technical_data.json"
            )
            valid_date = _find_element(
                technical["submodels"][0]["submodelElements"], "ValidDate"
            )
            self.assertEqual("2026-12-31", valid_date["value"])
            self.assertTrue(_is_placeholder(valid_date))

            carbon_elements = carbon["submodels"][0]["submodelElements"]
            self.assertNotIn(
                "ProductOrSectorSpecificCarbonFootprints",
                {element.get("idShort") for element in carbon_elements},
            )
            calculation_method = _find_element(
                carbon_elements, "PcfCalculationMethods"
            )["value"][0]
            self.assertEqual(
                "Not yet calculated – methodology to be confirmed before final DPP release.",
                calculation_method["value"],
            )

            handover = _read_output(
                Path(temporary_directory), "output_handover_documentation.json"
            )
            documents = _find_element(
                handover["submodels"][0]["submodelElements"], "Documents"
            )["value"]
            self.assertEqual(2, len(documents))
            self.assertEqual(
                [
                    "FIBROTOR_Datenblatt_EM_15_gb.pdf",
                    "FIBROTOR EM/ER.15 – CAD-Daten",
                ],
                [
                    _find_element(document["value"], "DocumentIdentifier")["value"]
                    for document in documents
                ],
            )

            maintenance = _read_output(
                Path(temporary_directory), "output_maintenance_instructions.json"
            )
            self.assertRaises(
                LookupError,
                _find_element,
                maintenance["submodels"][0]["submodelElements"],
                "Company",
            )
            self.assertFalse(result.missing_mandatory)
            self.assertTrue(
                any(
                    "workbook row 33 contains an Excel date" in warning
                    for warning in result.warnings
                )
            )


def _find_element(elements: list[dict], id_short: str) -> dict:
    for element in elements:
        if element.get("idShort") == id_short:
            return element
        nested = element.get("value")
        if isinstance(nested, list):
            try:
                return _find_element(nested, id_short)
            except LookupError:
                pass
    raise LookupError(id_short)


def _read_output(directory: Path, filename: str) -> dict:
    with (directory / filename).open(encoding="utf-8") as output_file:
        return json.load(output_file)


def _is_placeholder(element: dict) -> bool:
    return any(
        qualifier.get("type") == "DppValueStatus"
        and qualifier.get("value") == "Placeholder"
        for qualifier in element.get("qualifiers", [])
    )


if __name__ == "__main__":
    unittest.main()
