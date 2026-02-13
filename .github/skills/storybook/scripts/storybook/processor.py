"""Story processor — reads a story folder and assembles a storybook manifest."""

import json
from pathlib import Path

from . import page_breaker, palette, utils


def process_story(story_dir: str | Path, page_breaks: list[dict] | None = None) -> dict:
    """Process a story folder into a storybook manifest.

    Args:
        story_dir: Path to story folder containing .md + images.
        page_breaks: Pre-computed page breaks from the agent.
            If None, returns a partial result with a page_break_request
            the caller must fulfill.

    Returns:
        Dict with the full storybook manifest (if page_breaks provided),
        or a dict with needs_page_breaks=True and the request to send to an agent.
    """
    story_dir = utils.validate_story_dir(story_dir)

    # Read story
    md_path = utils.find_story_file(story_dir)
    story = page_breaker.read_story(md_path)

    # Find images
    images = utils.find_images(story_dir)
    image_names = [img.name for img in images]

    if page_breaks is None:
        # Build request for agent
        request = page_breaker.build_page_break_request(
            story_text=story["body"],
            image_count=len(images),
        )
        return {
            "needs_page_breaks": True,
            "title": story["title"],
            "image_count": len(images),
            "word_count": story["word_count"],
            "page_break_request": request,
        }

    # Extract palette and fonts
    colors = palette.extract_palette(story_dir)
    fonts = palette.select_fonts(story["body"])

    # Assemble pages
    pages = _build_pages(story["title"], page_breaks, image_names)

    slug = utils.slugify(story["title"])

    manifest = {
        "title": story["title"],
        "slug": slug,
        "pages": pages,
        "palette": colors,
        "fonts": {
            "heading": fonts["heading"],
            "body": fonts["body"],
        },
        "tone": fonts["tone"],
        "page_count": len(pages),
        "word_count": story["word_count"],
        "image_count": len(images),
    }

    # Write manifest
    out_path = story_dir / "storybook.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return manifest


def _build_pages(title: str, page_breaks: list[dict], image_names: list[str]) -> list[dict]:
    """Assemble the page list from text blocks and images."""
    pages = []

    # Cover page — use first image if available
    cover = {"type": "cover", "title": title}
    if image_names:
        cover["image"] = image_names[0]
    pages.append(cover)

    # Content pages from agent's text blocks
    # Start after cover image (if one was used)
    image_idx = 1 if image_names else 0
    for block in page_breaks:
        if block.get("has_image") and image_idx < len(image_names):
            pages.append({
                "type": "spread",
                "image": image_names[image_idx],
                "text": block["text"],
                "narrative_note": block.get("narrative_note", ""),
            })
            image_idx += 1
        else:
            pages.append({
                "type": "text",
                "text": block["text"],
                "narrative_note": block.get("narrative_note", ""),
            })

    # End page
    pages.append({"type": "end"})

    return pages
