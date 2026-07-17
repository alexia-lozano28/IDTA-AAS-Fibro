import argparse
import sys
from pathlib import Path

from .config import DEFAULT_UPLOAD_URL, find_project_root
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate JSON and AASX artifacts from the FIBROTOR DPP workbook."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Repository root containing the structured data directory.",
    )
    parser.add_argument("--workbook", type=Path, help="Override the workbook path.")
    parser.add_argument(
        "--template-dir", type=Path, help="Override the template directory."
    )
    parser.add_argument(
        "--asset-dir", type=Path, help="Override the supplementary asset directory."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated artifacts (defaults to data/generated).",
    )
    parser.add_argument(
        "--aasx",
        type=Path,
        help="Override the generated AASX path.",
    )
    parser.add_argument(
        "--no-aasx",
        action="store_true",
        help="Generate JSON only.",
    )
    parser.add_argument(
        "--upload",
        nargs="?",
        const=DEFAULT_UPLOAD_URL,
        metavar="URL",
        help=f"Upload the AASX after generation (default URL: {DEFAULT_UPLOAD_URL}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project_root = (args.project_root or find_project_root()).resolve()
        result = run_pipeline(
            project_root,
            workbook_path=args.workbook,
            template_dir=args.template_dir,
            asset_dir=args.asset_dir,
            output_dir=args.output_dir,
            aasx_path=args.aasx,
            create_aasx=not args.no_aasx,
            upload_url=args.upload,
        )
    except Exception as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Generated environment: {result.environment_path}")
    if result.aasx_path:
        print(f"Generated AASX: {result.aasx_path}")
    print(f"Product URI: {result.product_uri}")

    if result.missing_mandatory:
        print(f"Missing mandatory workbook values: {len(result.missing_mandatory)}")
        for missing in result.missing_mandatory:
            print(f"  - {missing}")
    if result.warnings:
        print(f"Normalization warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning}")
    if result.upload_status is not None:
        print(f"Upload completed with HTTP {result.upload_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
