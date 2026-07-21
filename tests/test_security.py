import unittest
from pathlib import Path

from dpp_aas.security_gateway import (
    AuthenticationError,
    AuthorizationError,
    GatewayConfig,
    OidcAuthorizer,
    Role,
    is_public_read_request,
)


class OidcAuthorizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = OidcAuthorizer(
            "https://gateway.example/auth/realms/basyx",
            "https://keycloak.example/certs",
            "basyx-api",
        )

    def test_rejects_missing_credentials(self) -> None:
        with self.assertRaises(AuthenticationError):
            self.authorizer.authorize(None, "GET")

    def test_admin_can_read_and_write(self) -> None:
        for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
            self.assertEqual(
                Role.ADMIN,
                self.authorizer.authorize_claims(
                    {"realm_access": {"roles": ["admin"]}}, method
                ),
            )

    def test_client_is_strictly_read_only(self) -> None:
        for method in ("GET", "HEAD", "OPTIONS"):
            self.assertEqual(
                Role.CLIENT,
                self.authorizer.authorize_claims(
                    {"realm_access": {"roles": ["client"]}}, method
                ),
            )
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.assertRaises(AuthorizationError):
                self.authorizer.authorize_claims(
                    {"realm_access": {"roles": ["client"]}}, method
                )

    def test_rejects_unrecognized_roles(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.authorizer.role_from_claims({"realm_access": {"roles": []}})


class GatewayRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GatewayConfig(
            authorizer=OidcAuthorizer(
                "https://gateway.example/auth/realms/basyx",
                "https://keycloak.example/certs",
                "basyx-api",
            ),
            environment_upstream="http://environment:8081",
            aas_registry_upstream="http://aas-registry:8080",
            submodel_registry_upstream="http://sm-registry:8080",
            keycloak_upstream="http://keycloak:8080",
        )

    def test_routes_environment_and_registry_paths(self) -> None:
        self.assertEqual(
            "http://environment:8081/shells?limit=10",
            self.config.upstream_url("/shells?limit=10"),
        )
        self.assertEqual(
            "http://environment:8081/shells/aHR0cHM6Ly9leGFtcGxlLmNvbS9hYXM?level=deep",
            self.config.upstream_url(
                "/api/shells/aHR0cHM6Ly9leGFtcGxlLmNvbS9hYXM?level=deep"
            ),
        )
        self.assertEqual(
            "http://keycloak:8080/auth/realms/basyx/protocol/openid-connect/auth",
            self.config.upstream_url(
                "/auth/realms/basyx/protocol/openid-connect/auth"
            ),
        )

    def test_only_instance_level_reads_are_public(self) -> None:
        shell = "/api/shells/aHR0cHM6Ly9leGFtcGxlLmNvbS9hYXM"
        descriptor = "/registry/aas/shell-descriptors/aHR0cHM6Ly9leGFtcGxlLmNvbS9hYXM"
        for method in ("GET", "HEAD", "OPTIONS"):
            self.assertTrue(is_public_read_request(method, shell))
            self.assertTrue(is_public_read_request(method, descriptor))
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertFalse(is_public_read_request(method, shell))
        self.assertFalse(is_public_read_request("GET", "/api/shells"))
        self.assertFalse(is_public_read_request("GET", shell + "/submodels"))
        self.assertFalse(is_public_read_request("GET", "/api/shells/%2Fsubmodels"))
        self.assertFalse(is_public_read_request("GET", "/api/shells/not.base64url"))
        self.assertEqual(
            "http://aas-registry:8080/shell-descriptors",
            self.config.upstream_url("/registry/aas/shell-descriptors"),
        )
        self.assertEqual(
            "http://sm-registry:8080/submodel-descriptors",
            self.config.upstream_url(
                "/registry/submodels/submodel-descriptors"
            ),
        )


class DeploymentConfigurationTests(unittest.TestCase):
    def test_aas_descriptors_use_browser_reachable_gateway(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        properties = (
            project_root / "config/aas-environment/application.properties"
        ).read_text(encoding="utf-8")
        compose = (project_root / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn(
            "basyx.externalurl=${BASYX_EXTERNAL_URL:https://localhost:8443}",
            properties,
        )
        self.assertIn(
            "BASYX_EXTERNAL_URL: ${PUBLIC_AAS_BASE_URL:-https://localhost:8443}/api",
            compose,
        )


if __name__ == "__main__":
    unittest.main()
