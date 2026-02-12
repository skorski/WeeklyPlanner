"""CLI entry points for image_gen — registered as 'image-gen' in pyproject.toml."""

import argparse
import json
import sys
from pathlib import Path


def _load_vocab(path: str | None) -> dict | None:
    if not path:
        return None
    from .prompt_refiner import load_vocabulary
    return load_vocabulary(path)


def cmd_generate(args):
    from .generate import generate_image
    vocab = _load_vocab(args.vocabulary)
    data = generate_image(
        prompt=args.prompt,
        vocabulary=vocab,
        quality=args.quality,
        size=args.size,
        style=args.style,
        output_path=args.output,
        output_format=args.format,
    )
    if not args.output:
        sys.stdout.buffer.write(data)
    else:
        print(f"Saved to {args.output}", file=sys.stderr)


def cmd_edit(args):
    from .modify import edit_image
    data = edit_image(
        image_path=args.image,
        prompt=args.prompt,
        mask_path=args.mask,
        quality=args.quality,
        output_path=args.output,
        output_format=args.format,
    )
    if not args.output:
        sys.stdout.buffer.write(data)
    else:
        print(f"Saved to {args.output}", file=sys.stderr)


def cmd_style_transfer(args):
    from .modify import transfer_style
    vocab = _load_vocab(args.vocabulary)
    data = transfer_style(
        image_path=args.image,
        style_prompt=args.style,
        vocabulary=vocab,
        output_path=args.output,
        output_format=args.format,
    )
    if not args.output:
        sys.stdout.buffer.write(data)
    else:
        print(f"Saved to {args.output}", file=sys.stderr)


def cmd_variations(args):
    from .modify import create_variations
    results = create_variations(
        image_path=args.image,
        n=args.count,
        variation_prompt=args.prompt,
        output_path=args.output,
        output_format=args.format,
    )
    if not args.output:
        print(f"Generated {len(results)} variation(s)", file=sys.stderr)
    else:
        print(f"Saved {len(results)} variation(s) to {args.output}", file=sys.stderr)


def cmd_vocabulary(args):
    from .vocabulary import build_vocabulary
    vocab = build_vocabulary(
        image_dir=args.image_dir,
        output_path=args.output,
        name=args.name,
        description=args.description or "",
    )
    if not args.output:
        print(json.dumps(vocab, indent=2))
    else:
        print(f"Vocabulary saved to {args.output}", file=sys.stderr)


def cmd_refine(args):
    from .prompt_refiner import (
        load_context,
        build_refinement_request,
        load_vocabulary,
    )
    vocab = _load_vocab(args.vocabulary)
    context = load_context(args.context) if args.context else None
    request = build_refinement_request(
        raw_prompt=args.prompt,
        vocabulary=vocab,
        context=context,
        creativity_level=args.creativity,
    )
    print(json.dumps(request, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="image-gen",
        description="Azure OpenAI image generation and modification toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
    p_gen = subparsers.add_parser("generate", help="Generate an image from a text prompt")
    p_gen.add_argument("--prompt", "-p", required=True, help="Text description of the image")
    p_gen.add_argument("--vocabulary", "-v", help="Path to visual vocabulary JSON")
    p_gen.add_argument("--quality", "-q", default="standard", choices=["standard", "hd"])
    p_gen.add_argument("--size", "-s", default="1024x1024",
                       choices=["1024x1024", "1024x1792", "1792x1024"])
    p_gen.add_argument("--style", default="natural", choices=["natural", "vivid"])
    p_gen.add_argument("--format", "-f", default="png", choices=["png", "webp"])
    p_gen.add_argument("--output", "-o", help="Output file path")
    p_gen.set_defaults(func=cmd_generate)

    # --- edit ---
    p_edit = subparsers.add_parser("edit", help="Edit/inpaint an existing image")
    p_edit.add_argument("--image", "-i", required=True, help="Path to source image")
    p_edit.add_argument("--prompt", "-p", required=True, help="Editing instruction")
    p_edit.add_argument("--mask", "-m", help="Path to mask image (white = edit region)")
    p_edit.add_argument("--quality", "-q", default="standard", choices=["standard", "hd"])
    p_edit.add_argument("--format", "-f", default="png", choices=["png", "webp"])
    p_edit.add_argument("--output", "-o", help="Output file path")
    p_edit.set_defaults(func=cmd_edit)

    # --- style-transfer ---
    p_style = subparsers.add_parser("style-transfer", help="Re-render an image in a new style")
    p_style.add_argument("--image", "-i", required=True, help="Path to source image")
    p_style.add_argument("--style", "-s", help="Style description")
    p_style.add_argument("--vocabulary", "-v", help="Path to visual vocabulary JSON")
    p_style.add_argument("--format", "-f", default="png", choices=["png", "webp"])
    p_style.add_argument("--output", "-o", help="Output file path")
    p_style.set_defaults(func=cmd_style_transfer)

    # --- variations ---
    p_var = subparsers.add_parser("variations", help="Generate variations of an image")
    p_var.add_argument("--image", "-i", required=True, help="Path to source image")
    p_var.add_argument("--count", "-n", type=int, default=1, help="Number of variations")
    p_var.add_argument("--prompt", "-p", help="Guidance for how variations should differ")
    p_var.add_argument("--format", "-f", default="png", choices=["png", "webp"])
    p_var.add_argument("--output", "-o", help="Output directory for variations")
    p_var.set_defaults(func=cmd_variations)

    # --- vocabulary ---
    p_vocab = subparsers.add_parser("vocabulary", help="Build a visual vocabulary from images")
    p_vocab.add_argument("--image-dir", "-d", required=True, help="Directory of mood-board images")
    p_vocab.add_argument("--name", default="Custom Vocabulary", help="Name for the vocabulary")
    p_vocab.add_argument("--description", help="Optional description")
    p_vocab.add_argument("--output", "-o", help="Output JSON file path")
    p_vocab.set_defaults(func=cmd_vocabulary)

    # --- refine ---
    p_refine = subparsers.add_parser("refine", help="Prepare a prompt refinement request")
    p_refine.add_argument("--prompt", "-p", required=True, help="Raw image prompt to refine")
    p_refine.add_argument("--vocabulary", "-v", help="Path to visual vocabulary JSON")
    p_refine.add_argument("--context", "-c", help="Path to markdown file for context")
    p_refine.add_argument("--creativity", default="medium",
                          choices=["low", "medium", "high"],
                          help="Creativity level for refinement")
    p_refine.set_defaults(func=cmd_refine)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        _print_error(e)
        sys.exit(1)


def _print_error(error: Exception):
    """Print a structured error message to stderr."""
    # Import error types here to avoid circular imports at module level
    from .client import ImageGenConfigError, ImageGenAuthError, ImageGenAPIError

    error_type = type(error).__name__
    prefix = "Error"

    if isinstance(error, ImageGenConfigError):
        prefix = "Configuration Error"
    elif isinstance(error, ImageGenAuthError):
        prefix = "Authentication Error"
    elif isinstance(error, ImageGenAPIError):
        prefix = "API Error"
    elif isinstance(error, FileNotFoundError):
        prefix = "File Not Found"
    elif isinstance(error, NotADirectoryError):
        prefix = "Invalid Path"
    elif isinstance(error, ValueError):
        prefix = "Invalid Input"
    elif isinstance(error, PermissionError):
        prefix = "Permission Denied"

    print(f"\n[{prefix}] {error}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
