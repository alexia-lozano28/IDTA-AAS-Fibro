#!/usr/bin/env python3
"""Resolve one AAS through its Registry descriptor and fetch the shell."""

import argparse
import base64
import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen


def encode_identifier(identifier: str) -> str:
    return base64.urlsafe_b64encode(identifier.encode("utf-8")).decode("ascii").rstrip("=")


def get_json(url: str, *, insecure: bool) -> dict:
    context = ssl._create_unverified_context() if insecure else None
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, context=context, timeout=30) as response:
        return json.load(response)


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
    args = parser.parse_args()

    encoded_id = encode_identifier(args.aas_id)
    descriptor_url = f"{args.registry_url.rstrip('/')}/{encoded_id}"
    descriptor = get_json(descriptor_url, insecure=args.insecure)
    endpoint = shell_endpoint(descriptor)
    shell = get_json(endpoint, insecure=args.insecure)

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
