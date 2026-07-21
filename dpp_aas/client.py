from pathlib import Path
from typing import Any

import requests


class AASClient:
    """Client for the secured BaSyx AAS environment API."""

    def __init__(
        self,
        base_url: str,
        *,
        access_token: str,
        verify: bool | str | Path = True,
        timeout: float = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify = str(verify) if isinstance(verify, Path) else verify
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
        )

    def get_shells(self) -> dict[str, Any]:
        return self._json("GET", "/shells")

    def get_submodels(self) -> dict[str, Any]:
        return self._json("GET", "/submodels")

    def get_concept_descriptions(self) -> dict[str, Any]:
        return self._json("GET", "/concept-descriptions")

    def get_shell(self, shell_id: str) -> dict[str, Any]:
        return self._json("GET", f"/shells/{shell_id}")

    def create_shell(self, shell: dict[str, Any]) -> requests.Response:
        return self._request("POST", "/shells", json=shell)

    def create_submodel(self, submodel: dict[str, Any]) -> requests.Response:
        return self._request("POST", "/submodels", json=submodel)

    def create_concept_description(
        self, concept_description: dict[str, Any]
    ) -> requests.Response:
        return self._request(
            "POST", "/concept-descriptions", json=concept_description
        )

    def update_property(
        self, submodel_id: str, property_id: str, value: Any
    ) -> requests.Response:
        return self._request(
            "PUT",
            f"/submodels/{submodel_id}/submodel-elements/{property_id}",
            json={"value": value},
        )

    def upload_aasx(self, aasx_path: Path) -> requests.Response:
        with aasx_path.open("rb") as aasx_file:
            return self._request(
                "POST",
                "/upload",
                files={
                    "file": (
                        aasx_path.name,
                        aasx_file,
                        "application/octet-stream",
                    )
                },
            )

    def _json(self, method: str, path: str) -> dict[str, Any]:
        return self._request(method, path).json()

    def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> requests.Response:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            verify=self.verify,
            **kwargs,
        )
        response.raise_for_status()
        return response
