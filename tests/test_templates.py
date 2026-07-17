import unittest

from dpp_aas.templates import fill_elements, normalize_elements


class TemplateTests(unittest.TestCase):
    def test_fills_elements_below_unnamed_list_items(self) -> None:
        elements = [
            {
                "idShort": "Items",
                "modelType": "SubmodelElementList",
                "value": [
                    {
                        "modelType": "SubmodelElementCollection",
                        "value": [
                            {
                                "idShort": "Amount",
                                "modelType": "Property",
                                "valueType": "xs:decimal",
                            }
                        ],
                    }
                ],
            }
        ]

        fill_elements(elements, {"Amount": 2.5})

        self.assertEqual("2.5", elements[0]["value"][0]["value"][0]["value"])

    def test_normalizes_known_aas_v3_template_conflicts(self) -> None:
        elements = [
            {
                "idShort": "Items",
                "modelType": "SubmodelElementList",
                "value": [
                    {
                        "idShort": "Item",
                        "modelType": "SubmodelElementCollection",
                        "value": [],
                    }
                ],
            },
            {
                "idShort": "Legacy",
                "modelType": "Property",
                "semanticId": {
                    "type": "ModelReference",
                    "keys": [{"type": "Identifiable", "value": "urn:test"}],
                },
                "qualifiers": [
                    {"type": "Example", "valueType": "xs:string", "value": "a"},
                    {"type": "Example", "valueType": "xs:string", "value": "b"},
                ],
            },
        ]

        normalize_elements(elements)

        self.assertNotIn("idShort", elements[0]["value"][0])
        self.assertEqual(1, len(elements[1]["qualifiers"]))
        self.assertEqual("ExternalReference", elements[1]["semanticId"]["type"])
        self.assertEqual(
            "GlobalReference", elements[1]["semanticId"]["keys"][0]["type"]
        )


if __name__ == "__main__":
    unittest.main()
