import unittest

from scripts.test_distributed_aas import (
    client_credentials_token,
    encode_identifier,
    shell_endpoint,
)
from unittest.mock import MagicMock, patch


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

    @patch("scripts.test_distributed_aas.urlopen")
    def test_requests_a_client_credentials_token(self, urlopen: MagicMock) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{"access_token":"machine-token"}'
        urlopen.return_value = response

        self.assertEqual(
            "machine-token",
            client_credentials_token(
                "https://issuer.example/token",
                "aas-read-client",
                "secret",
                insecure=False,
            ),
        )
        request = urlopen.call_args.args[0]
        self.assertIn(b"grant_type=client_credentials", request.data)
        self.assertIn(b"client_id=aas-read-client", request.data)


if __name__ == "__main__":
    unittest.main()
