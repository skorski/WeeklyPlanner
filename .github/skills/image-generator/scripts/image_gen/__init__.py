"""image_gen — Azure OpenAI image generation, modification, and prompt refinement.

Public API:
    generate_image       — Generate an image from a text prompt
    edit_image           — Edit/inpaint an existing image
    transfer_style       — Re-render an image in a different style
    create_variations    — Generate variations of an existing image
    build_vocabulary     — Analyze a mood board to extract a visual vocabulary
    load_context         — Read a markdown file for prompt context
    build_refinement_request — Assemble a prompt refinement request for an LLM
    parse_refined_response   — Parse an LLM's refinement response
    load_vocabulary      — Load a visual vocabulary JSON file
"""

from .generate import generate_image
from .modify import edit_image, transfer_style, create_variations
from .vocabulary import build_vocabulary
from .prompt_refiner import (
    load_context,
    load_vocabulary,
    build_refinement_request,
    parse_refined_response,
)
from .client import ImageGenConfigError, ImageGenAuthError, ImageGenAPIError

__all__ = [
    "generate_image",
    "edit_image",
    "transfer_style",
    "create_variations",
    "build_vocabulary",
    "load_context",
    "load_vocabulary",
    "build_refinement_request",
    "parse_refined_response",
    "ImageGenConfigError",
    "ImageGenAuthError",
    "ImageGenAPIError",
]
