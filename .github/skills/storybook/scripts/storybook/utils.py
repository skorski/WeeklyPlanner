"""Helpers for image I/O, slug generation, and path validation."""

import re
from pathlib import Path

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def find_images(directory: str | Path) -> list[Path]:
    """Find and sort image files in a directory by filename."""
    d = Path(directory)
    if not d.is_dir():
        raise FileNotFoundError(f"Image directory not found: {d}")
    images = sorted(
        f for f in d.iterdir()
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
    )
    return images


def find_story_file(directory: str | Path) -> Path:
    """Find the first .md file in a directory."""
    d = Path(directory)
    md_files = sorted(f for f in d.iterdir() if f.is_file() and f.suffix.lower() == ".md")
    if not md_files:
        raise FileNotFoundError(f"No .md story file found in {d}")
    return md_files[0]


def validate_story_dir(directory: str | Path) -> Path:
    """Validate that a directory is a valid story folder."""
    d = Path(directory)
    if not d.exists():
        raise FileNotFoundError(f"Story directory not found: {d}")
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {d}")
    # Must have at least a markdown file
    find_story_file(d)
    return d
