from client.client import AASClient

# Origin server  (Team A)
team_a = AASClient("http://localhost:8081")

# Destination server (Team B)
team_b = AASClient("http://localhost:8091")


# Resources origin
shells = team_a.get_shells()
submodels = team_a.get_submodels()
concept_descriptions = team_a.get_concept_descriptions()


# Copy AAS
for shell in shells.get("result", []):
    try:
        team_b.create_shell(shell)
        print(f"✓ Shell created: {shell['idShort']}")
    except Exception as e:
        print(f"✗ Error creating Shell {shell['idShort']}: {e}")


# Copy Submodels
for submodel in submodels.get("result", []):
    try:
        team_b.create_submodel(submodel)
        print(f"✓ Submodel created: {submodel['idShort']}")
    except Exception as e:
        print(f"✗ Error creating Submodel {submodel['idShort']}: {e}")


# Copy ConceptDescriptions
for cd in concept_descriptions.get("result", []):
    try:
        team_b.create_concept_description(cd)
        print(f"✓ ConceptDescription created: {cd['idShort']}")
    except Exception as e:
        print(f"✗ Error creating ConceptDescription {cd['idShort']}: {e}")


print("\nSync completed.")