import os
from pathlib import Path
from string import Template


def render_template(source: Path, destination: Path) -> None:
    rendered = Template(source.read_text(encoding="utf-8")).substitute(os.environ)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")


def main() -> int:
    source = Path(
        os.getenv(
            "UI_CONFIG_TEMPLATE",
            "/app/security/basyx-infra.yml.template",
        )
    )
    destination = Path(
        os.getenv("UI_CONFIG_OUTPUT", "/ui-config/basyx-infra.yml")
    )
    render_template(source, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
