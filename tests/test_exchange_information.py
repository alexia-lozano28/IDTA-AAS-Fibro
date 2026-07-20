import os
from pathlib import Path

from client.client import AASClient


def main() -> None:
    certificate = Path("security/certs/gateway.crt")
    team_a = AASClient(
        "https://localhost:8443",
        access_token=_required_environment("TEAM_A_CLIENT_ACCESS_TOKEN"),
        verify=certificate,
    )
    team_b = AASClient(
        "https://localhost:9443",
        access_token=_required_environment("TEAM_B_ADMIN_ACCESS_TOKEN"),
        verify=Path("security/certs-team-b/gateway.crt"),
    )

    resources = (
        ("Shell", team_a.get_shells(), team_b.create_shell),
        ("Submodel", team_a.get_submodels(), team_b.create_submodel),
        (
            "ConceptDescription",
            team_a.get_concept_descriptions(),
            team_b.create_concept_description,
        ),
    )
    for resource_name, response, create in resources:
        for item in response.get("result", []):
            try:
                create(item)
                print(f"{resource_name} created: {item['idShort']}")
            except Exception as exc:
                print(
                    f"Error creating {resource_name} {item['idShort']}: {exc}"
                )

    print("\nSync completed.")


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


if __name__ == "__main__":
    main()
