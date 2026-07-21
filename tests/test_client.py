import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from dpp_aas.client import AASClient


class AASClientTests(unittest.TestCase):
    def test_get_uses_gateway_url_token_and_certificate(self) -> None:
        response = Mock()
        response.json.return_value = {"result": [{"idShort": "Example"}]}

        with patch("dpp_aas.client.requests.Session.request", return_value=response) as request:
            client = AASClient(
                "https://localhost:8443/",
                access_token="token",
                verify=Path("gateway.crt"),
            )
            result = client.get_shells()

        self.assertEqual({"result": [{"idShort": "Example"}]}, result)
        self.assertEqual("Bearer token", client.session.headers["Authorization"])
        request.assert_called_once_with(
            "GET",
            "https://localhost:8443/shells",
            timeout=30,
            verify="gateway.crt",
        )
        response.raise_for_status.assert_called_once_with()

    def test_upload_posts_aasx_to_gateway(self) -> None:
        response = Mock(status_code=201)
        with tempfile.TemporaryDirectory() as temporary_directory:
            aasx_path = Path(temporary_directory) / "example.aasx"
            aasx_path.write_bytes(b"package")

            with patch(
                "dpp_aas.client.requests.Session.request", return_value=response
            ) as request:
                result = AASClient(
                    "https://localhost:8443",
                    access_token="token",
                ).upload_aasx(aasx_path)

        self.assertIs(response, result)
        self.assertEqual("POST", request.call_args.args[0])
        self.assertEqual(
            "https://localhost:8443/upload", request.call_args.args[1]
        )
        uploaded_file = request.call_args.kwargs["files"]["file"]
        self.assertEqual("example.aasx", uploaded_file[0])
        self.assertEqual("application/octet-stream", uploaded_file[2])
        response.raise_for_status.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
