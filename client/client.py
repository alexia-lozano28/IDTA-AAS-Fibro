import requests
import json
class AASClient_2:

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def upload_aasx(self, aasx_path):

        with open(aasx_path, "rb") as file:

            files = {
                "file": (
                    aasx_path.split("/")[-1],
                    file,
                    "application/octet-stream"
                )
            }

            response = requests.post(
                f"{self.base_url}/upload",
                files=files
            )

        response.raise_for_status()

        return response

    def get_shells(self):

        response = requests.get(
            f"{self.base_url}/shells"
        )

        response.raise_for_status()

        return response.json()

    def get_submodels(self):

        response = requests.get(
            f"{self.base_url}/submodels"
        )

        response.raise_for_status()

        return response.json()
    def get_shell(self, shell_id):

        response = requests.get(
            f"{self.base_url}/shells/{shell_id}"
        )

        response.raise_for_status()

        return response.json()

    def update_property(self,
                    submodel_id,
                    property_id,
                    value):

        url = (
            f"{self.base_url}/submodels/"
            f"{submodel_id}"
            f"/submodel-elements/"
            f"{property_id}"
        )

        response = requests.put(
            url,
            json={
                "value": value
            }
        )

        response.raise_for_status()

        return response
    
    def create_submodel(self, submodel):
        print("Creating submodel:")
        print(json.dumps(submodel, indent=2))
        response = requests.post(
            f"{self.base_url}/submodels",
            json=submodel
        )

        response.raise_for_status()

        return response
            
    def create_asset(self, asset_info):
        response = requests.post(
                self.base_url + "/upload",
                files={
                    "file": (
                        asset_info,
                        "application/octet-stream",
                    )
                },
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        return response

import requests


class AASClient:

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    # ---------- GET ----------

    def get_shells(self):
        return requests.get(f"{self.base_url}/shells").json()

    def get_submodels(self):
        return requests.get(f"{self.base_url}/submodels").json()

    def get_concept_descriptions(self):
        return requests.get(f"{self.base_url}/concept-descriptions").json()

    # ---------- POST ----------

    def create_shell(self, shell):
        r = requests.post(
            f"{self.base_url}/shells",
            json=shell,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r

    def create_submodel(self, submodel):
        r = requests.post(
            f"{self.base_url}/submodels",
            json=submodel,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r

    def create_concept_description(self, concept_description):
        r = requests.post(
            f"{self.base_url}/concept-descriptions",
            json=concept_description,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r