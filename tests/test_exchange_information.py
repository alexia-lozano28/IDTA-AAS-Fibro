from client.client import AASClient


def main() -> None:
    team_a = AASClient("http://localhost:8081")
    team_b = AASClient("http://localhost:8091")

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


if __name__ == "__main__":
    main()
