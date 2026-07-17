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


if __name__ == "__main__":
    unittest.main()
