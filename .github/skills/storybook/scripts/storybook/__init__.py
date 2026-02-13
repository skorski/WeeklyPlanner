"""Children's storybook processor — page breaking, palette extraction, and PDF generation."""

from .page_breaker import read_story, build_page_break_request, parse_page_break_response
from .palette import extract_palette, select_fonts
from .processor import process_story
from .pdf_renderer import render_pdf
from .utils import slugify, find_images, find_story_file, validate_story_dir

__all__ = [
    "read_story",
    "build_page_break_request",
    "parse_page_break_response",
    "extract_palette",
    "select_fonts",
    "process_story",
    "render_pdf",
    "slugify",
    "find_images",
    "find_story_file",
    "validate_story_dir",
]
