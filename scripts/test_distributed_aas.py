#!/usr/bin/env python3
"""Resolve one AAS through its Registry descriptor and fetch the shell."""

import argparse
import base64
import json
import ssl
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen


def encode_identifier(identifier: str) -> str:
    return base64.urlsafe_b64encode(identifier.encode("utf-8")).decode("ascii").rstrip("=")


def get_json(url: str, *, insecure: bool, access_token: str | None = None) -> dict:
    context = ssl._create_unverified_context() if insecure else None
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(url, headers=headers)
    with urlopen(request, context=context, timeout=30) as response:
        return json.load(response)


def client_credentials_token(
    token_url: str, client_id: str, client_secret: str, *, insecure: bool
) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("ascii")
    context = ssl._create_unverified_context() if insecure else None
    request = Request(
        token_url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, context=context, timeout=30) as response:
        payload = json.load(response)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Token response contains no access_token")
    return token


def shell_endpoint(descriptor: dict) -> str:
    for endpoint in descriptor.get("endpoints", []):
        protocol = endpoint.get("protocolInformation", {})
        href = protocol.get("href")
        if isinstance(href, str) and href:
            return href
    raise ValueError("Registry descriptor contains no usable shell endpoint")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry_url", help="Registry shell-descriptor collection URL")
    parser.add_argument("aas_id", help="Unencoded Asset Administration Shell ID")
    parser.add_argument("--output", type=Path, help="Save the full shell JSON here")
    parser.add_argument("--insecure", action="store_true", help="Accept a local self-signed TLS certificate")
    parser.add_argument("--token-url", help="OIDC token endpoint for client-credentials authentication")
    parser.add_argument("--client-id", default="aas-read-client")
    parser.add_argument("--client-secret", help="Confidential client secret")
    args = parser.parse_args()

    if not args.token_url or not args.client_secret:
        parser.error("--token-url and --client-secret are required for Registry access")

    access_token = client_credentials_token(
        args.token_url,
        args.client_id,
        args.client_secret,
        insecure=args.insecure,
    )

    encoded_id = encode_identifier(args.aas_id)
    descriptor_url = f"{args.registry_url.rstrip('/')}/{encoded_id}"
    descriptor = get_json(descriptor_url, insecure=args.insecure, access_token=access_token)
    endpoint = shell_endpoint(descriptor)
    shell = get_json(endpoint, insecure=args.insecure, access_token=access_token)

    print(f"AAS ID: {shell.get('id', args.aas_id)}")
    print(f"idShort: {shell.get('idShort', '(not set)')}")
    print(f"Descriptor: {descriptor_url}")
    print(f"Shell endpoint: {endpoint}")
    print(f"Submodel references: {len(shell.get('submodels', []))}")
    if args.output:
        args.output.write_text(json.dumps(shell, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
