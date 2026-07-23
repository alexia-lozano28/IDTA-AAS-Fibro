import argparse
import json
import os
import ssl
import string
from dataclasses import dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar
from urllib.parse import urlsplit

import requests
import jwt
from jwt import PyJWKClient


READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
BASE64URL_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-_")
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)
ACCESS_CONTROL_HEADERS = frozenset(
    {
        "access-control-allow-credentials",
        "access-control-allow-headers",
        "access-control-allow-methods",
        "access-control-allow-origin",
        "access-control-expose-headers",
        "access-control-max-age",
    }
)


class Role(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class OidcAuthorizer:
    """Validates Keycloak-issued access tokens and maps realm roles."""

    def __init__(self, issuer: str, jwks_url: str, audience: str) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=300)

    def authorize(self, token: str | None, method: str) -> Role:
        role = self.authenticate(token)
        return self.authorize_role(role, method)

    @staticmethod
    def authorize_role(role: Role, method: str) -> Role:
        if role is Role.CLIENT and method.upper() not in READ_METHODS:
            raise AuthorizationError("The client role has read-only access")
        return role

    def authorize_claims(self, claims: dict[str, object], method: str) -> Role:
        return self.authorize_role(self.role_from_claims(claims), method)

    def authenticate(self, token: str | None) -> Role:
        if not token:
            raise AuthenticationError("A bearer access token is required")
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("The access token is invalid") from exc
        return self.role_from_claims(claims)

    @staticmethod
    def role_from_claims(claims: dict[str, object]) -> Role:
        realm_access = claims.get("realm_access", {})
        roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
        if Role.ADMIN.value in roles:
            return Role.ADMIN
        if Role.CLIENT.value in roles:
            return Role.CLIENT
        raise AuthorizationError("The access token has no recognized role")


@dataclass(frozen=True)
class GatewayConfig:
    authorizer: OidcAuthorizer
    environment_upstream: str
    aas_registry_upstream: str
    submodel_registry_upstream: str
    keycloak_upstream: str
    import_upstream: str
    timeout: float = 60

    def upstream_url(self, request_path: str) -> str:
        parsed = urlsplit(request_path)
        if parsed.path == "/auth" or parsed.path.startswith("/auth/"):
            return self.keycloak_upstream.rstrip("/") + request_path
        if parsed.path == "/api/admin/import":
            return self.import_upstream.rstrip("/") + request_path
        routes = (
            ("/registry/aas", self.aas_registry_upstream),
            ("/registry/submodels", self.submodel_registry_upstream),
        )
        for prefix, upstream in routes:
            if request_path == prefix or request_path.startswith(prefix + "/"):
                suffix = request_path[len(prefix) :] or "/"
                return upstream.rstrip("/") + suffix
        advertised_repository_prefixes = (
            "/api/shells",
            "/api/submodels",
            "/api/concept-descriptions",
        )
        if any(
            parsed.path == prefix or parsed.path.startswith(prefix + "/")
            for prefix in advertised_repository_prefixes
        ):
            return self.environment_upstream.rstrip("/") + request_path[4:]
        return self.environment_upstream.rstrip("/") + request_path


def is_public_read_request(method: str, request_path: str) -> bool:
    """Return true only for the curated public shell-instance route."""
    if method.upper() not in READ_METHODS:
        return False
    path = urlsplit(request_path).path
    public_prefixes = ("/api/shells/",)
    for prefix in public_prefixes:
        identifier = path[len(prefix) :] if path.startswith(prefix) else ""
        if identifier and all(character in BASE64URL_CHARACTERS for character in identifier):
            return True
    return False


class SecurityGatewayHandler(BaseHTTPRequestHandler):
    config: ClassVar[GatewayConfig]
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._handle_request()

    def do_HEAD(self) -> None:
        self._handle_request()

    def do_POST(self) -> None:
        self._handle_request()

    def do_PUT(self) -> None:
        self._handle_request()

    def do_PATCH(self) -> None:
        self._handle_request()

    def do_DELETE(self) -> None:
        self._handle_request()

    def do_OPTIONS(self) -> None:
        self._send_cors_preflight()

    def _handle_request(self) -> None:
        parsed = urlsplit(self.path)
        if (
            parsed.path == "/gateway/health"
            and self.command in {"GET", "HEAD"}
        ):
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/auth" or parsed.path.startswith("/auth/"):
            self._proxy_request(None)
            return

        if is_public_read_request(self.command, self.path):
            self._proxy_request(None)
            return

        try:
            role = self.config.authorizer.authorize(
                _request_credential(self.headers), self.command
            )
        except AuthenticationError as exc:
            self._discard_request_body()
            self._send_json(
                401,
                {"error": "unauthorized", "message": str(exc)},
                extra_headers={"WWW-Authenticate": "Bearer"},
            )
            return
        except AuthorizationError as exc:
            self._discard_request_body()
            self._send_json(
                403, {"error": "forbidden", "message": str(exc)}
            )
            return

        self._proxy_request(role)

    def _proxy_request(self, role: Role | None) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request_headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower()
            not in HOP_BY_HOP_HEADERS
            | {"host", "content-length"}
        }
        request_headers["X-Forwarded-Proto"] = "https"
        request_headers["X-Forwarded-Host"] = self.headers.get("Host", "localhost")
        if role:
            request_headers["X-Authenticated-Role"] = role.value
        upstream = self.config.upstream_url(self.path)

        try:
            response = requests.request(
                self.command,
                upstream,
                headers=request_headers,
                data=body or None,
                timeout=self.config.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            self._send_json(
                502,
                {"error": "bad_gateway", "message": str(exc)},
            )
            return

        response_body = response.content
        self.send_response(response.status_code)
        for name, value in response.headers.items():
            if name.lower() not in HOP_BY_HOP_HEADERS | {
                "content-encoding",
                "content-length",
                "vary",
            } | ACCESS_CONTROL_HEADERS:
                self.send_header(name, value)
        self.send_header("Content-Length", str(len(response_body)))
        self._send_cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response_body)
        response.close()

    def _send_cors_preflight(self) -> None:
        self._discard_request_body()
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(
        self,
        status: int,
        payload: dict[str, str],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self._send_cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _discard_request_body(self) -> None:
        content_length = self.headers.get("Content-Length")
        if content_length and content_length.isdigit():
            self.rfile.read(int(content_length))

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization,Content-Type",
        )

    def log_message(self, format_string: str, *args: object) -> None:
        print(
            f"{self.address_string()} {self.command} {self.path} "
            + format_string % args,
            flush=True,
        )


def create_server(
    host: str,
    port: int,
    config: GatewayConfig,
    cert_file: str,
    key_file: str,
) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredSecurityGatewayHandler",
        (SecurityGatewayHandler,),
        {"config": config},
    )
    server = ThreadingHTTPServer((host, port), handler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
    tls_context.load_cert_chain(cert_file, key_file)
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TLS and RBAC gateway for BaSyx")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8443, type=int)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args(argv)

    config = GatewayConfig(
        authorizer=OidcAuthorizer(
            issuer=_required_environment("OIDC_ISSUER"),
            jwks_url=_required_environment("OIDC_JWKS_URL"),
            audience=_required_environment("OIDC_AUDIENCE"),
        ),
        environment_upstream=os.getenv(
            "AAS_ENVIRONMENT_UPSTREAM", "http://aas-environment:8081"
        ),
        aas_registry_upstream=os.getenv(
            "AAS_REGISTRY_UPSTREAM", "http://aas-registry:8080"
        ),
        submodel_registry_upstream=os.getenv(
            "SUBMODEL_REGISTRY_UPSTREAM", "http://submodel-registry:8080"
        ),
        keycloak_upstream=os.getenv("KEYCLOAK_UPSTREAM", "http://keycloak:8080"),
        import_upstream=os.getenv("IMPORT_UPSTREAM", "http://import-api:8000"),
        timeout=float(os.getenv("GATEWAY_UPSTREAM_TIMEOUT", "180")),
    )
    server = create_server(args.host, args.port, config, args.cert, args.key)
    print(f"Security gateway listening on https://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _request_credential(headers: object) -> str | None:
    authorization = headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()
    return None


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
