"""Generate a 5x5 inch square PDF from a storybook manifest using Playwright."""

import json
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
_PAGE_WIDTH_MM = 127
_PAGE_HEIGHT_MM = 127


def render_pdf(
    manifest_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Render a storybook manifest to a 5x5 inch square PDF.

    Args:
        manifest_path: Path to storybook.json.
        output_path: Optional output path. Defaults to storybook.pdf next to manifest.

    Returns:
        Path to the generated PDF file.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    story_dir = manifest_path.parent

    if output_path is None:
        output_path = story_dir / "storybook.pdf"
    else:
        output_path = Path(output_path)

    # Resolve image paths to absolute file:// URIs for Playwright
    for page in manifest.get("pages", []):
        if "image" in page:
            img_path = story_dir / page["image"]
            if img_path.exists():
                page["image_uri"] = img_path.resolve().as_uri()

    # Render HTML from template
    html_content = _render_html(manifest)

    # Write temp HTML and convert to PDF with Playwright
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_content)
        html_path = Path(f.name)

    try:
        _html_to_pdf(html_path, output_path)
    finally:
        html_path.unlink(missing_ok=True)

    return output_path


def _render_html(manifest: dict) -> str:
    """Render the storybook HTML from the Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("storybook.html.j2")
    return template.render(
        title=manifest.get("title", "Untitled"),
        pages=manifest.get("pages", []),
        palette=manifest.get("palette", {}),
        fonts=manifest.get("fonts", {}),
        tone=manifest.get("tone", "default"),
    )


def _html_to_pdf(html_path: Path, output_path: Path) -> None:
    """Convert an HTML file to PDF using Playwright."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_load_state("networkidle")

        page.pdf(
            path=str(output_path),
            width=f"{_PAGE_WIDTH_MM}mm",
            height=f"{_PAGE_HEIGHT_MM}mm",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
        )
        browser.close()
