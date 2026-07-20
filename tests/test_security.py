import unittest

from dpp_aas.security_gateway import (
    AuthenticationError,
    AuthorizationError,
    GatewayConfig,
    OidcAuthorizer,
    Role,
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
            "http://keycloak:8080/auth/realms/basyx/protocol/openid-connect/auth",
            self.config.upstream_url(
                "/auth/realms/basyx/protocol/openid-connect/auth"
            ),
        )
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


if __name__ == "__main__":
    unittest.main()
