import unittest

from scripts.test_distributed_aas import encode_identifier, shell_endpoint


class DistributedAasTestScriptTests(unittest.TestCase):
    def test_encodes_the_real_aas_id_as_unpadded_base64url(self) -> None:
        self.assertEqual(
            "aHR0cHM6Ly93d3cuZmlicm9ydC5jb20vZG93bmxvYWRzP3Byb2R1Y3Q9MjUvYWFz",
            encode_identifier("https://www.fibrort.com/downloads?product=25/aas"),
        )

    def test_extracts_protocol_information_href(self) -> None:
        self.assertEqual(
            "https://aas.example/api/shells/encoded",
            shell_endpoint(
                {
                    "endpoints": [
                        {
                            "protocolInformation": {
                                "href": "https://aas.example/api/shells/encoded"
                            }
                        }
                    ]
                }
            ),
        )

    def test_rejects_a_descriptor_without_an_endpoint(self) -> None:
        with self.assertRaises(ValueError):
            shell_endpoint({"endpoints": []})


if __name__ == "__main__":
    unittest.main()
