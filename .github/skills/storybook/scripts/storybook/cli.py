"""CLI entry points for the storybook skill.

Usage:
    uv run storybook process <story_dir> [--pdf]
    uv run storybook pdf <manifest_path> [-o output]
    uv run storybook process-all <stories_dir> [--pdf]
"""

import argparse
import json
import sys
from pathlib import Path

from . import page_breaker, processor, pdf_renderer, utils


def _print_error(label: str, message: str) -> None:
    print(f"\n[{label}] {message}", file=sys.stderr)


def cmd_process(args) -> None:
    """Process a story folder into a storybook manifest."""
    story_dir = Path(args.story_dir)

    try:
        utils.validate_story_dir(story_dir)
    except (FileNotFoundError, NotADirectoryError) as e:
        _print_error("Invalid Input", str(e))
        sys.exit(1)

    # Check for pre-existing page breaks
    breaks_path = story_dir / "page_breaks.json"
    page_breaks = None

    if breaks_path.exists():
        try:
            page_breaks = json.loads(breaks_path.read_text(encoding="utf-8"))
            print(f"Using existing page breaks from {breaks_path}")
        except json.JSONDecodeError as e:
            _print_error("Invalid Input", f"Could not parse {breaks_path}: {e}")
            sys.exit(1)

    result = processor.process_story(story_dir, page_breaks=page_breaks)

    if result.get("needs_page_breaks"):
        # Print the request for the agent
        req = result["page_break_request"]
        print("\n" + "=" * 60)
        print("PAGE BREAK REQUEST — Send this to an LLM/agent")
        print("=" * 60)
        print(f"\nTitle: {result['title']}")
        print(f"Images: {result['image_count']}, Words: {result['word_count']}")
        print(f"\n--- System Prompt ---\n{req['system_prompt']}")
        print(f"\n--- User Prompt ---\n{req['user_prompt']}")
        print("\n" + "=" * 60)
        print(f"\nSave the agent's JSON response to: {breaks_path}")
        print(f"Then re-run: uv run storybook process {story_dir}")
        return

    print(f"\nStorybook manifest generated: {story_dir / 'storybook.json'}")
    print(f"  Title: {result['title']}")
    print(f"  Pages: {result['page_count']}, Images: {result['image_count']}")
    print(f"  Palette: {result['palette']}")
    print(f"  Fonts: {result['fonts']} (tone: {result['tone']})")

    if args.pdf:
        try:
            pdf_path = pdf_renderer.render_pdf(story_dir / "storybook.json")
            print(f"  PDF: {pdf_path}")
        except Exception as e:
            _print_error("PDF Error", str(e))
            sys.exit(1)


def cmd_pdf(args) -> None:
    """Generate a PDF from an existing storybook manifest."""
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        _print_error("File Not Found", f"Manifest not found: {manifest_path}")
        sys.exit(1)

    output = args.output
    try:
        pdf_path = pdf_renderer.render_pdf(manifest_path, output)
        print(f"PDF generated: {pdf_path}")
    except Exception as e:
        _print_error("PDF Error", str(e))
        sys.exit(1)


def cmd_process_all(args) -> None:
    """Process all story folders in a directory."""
    stories_dir = Path(args.stories_dir)
    if not stories_dir.is_dir():
        _print_error("Invalid Input", f"Not a directory: {stories_dir}")
        sys.exit(1)

    subdirs = sorted(d for d in stories_dir.iterdir() if d.is_dir())
    if not subdirs:
        print(f"No story folders found in {stories_dir}")
        return

    processed = 0
    for d in subdirs:
        try:
            md_file = utils.find_story_file(d)
        except FileNotFoundError:
            continue

        print(f"\nProcessing: {d.name}")
        breaks_path = d / "page_breaks.json"
        page_breaks = None
        if breaks_path.exists():
            try:
                page_breaks = json.loads(breaks_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"  Skipping — invalid page_breaks.json")
                continue

        result = processor.process_story(d, page_breaks=page_breaks)
        if result.get("needs_page_breaks"):
            print(f"  Needs page breaks — run agent and save to {breaks_path}")
            continue

        print(f"  Done: {result['page_count']} pages")
        processed += 1

        if args.pdf:
            try:
                pdf_path = pdf_renderer.render_pdf(d / "storybook.json")
                print(f"  PDF: {pdf_path}")
            except Exception as e:
                print(f"  PDF failed: {e}")

    print(f"\nProcessed {processed}/{len(subdirs)} stories")


def main():
    parser = argparse.ArgumentParser(
        prog="storybook",
        description="Children's storybook processor — page breaking, palette, and PDF",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # process
    p_proc = sub.add_parser("process", help="Process a story folder into storybook.json")
    p_proc.add_argument("story_dir", help="Path to story folder (contains .md + images)")
    p_proc.add_argument("--pdf", action="store_true", help="Also generate PDF")
    p_proc.set_defaults(func=cmd_process)

    # pdf
    p_pdf = sub.add_parser("pdf", help="Generate PDF from storybook.json")
    p_pdf.add_argument("manifest", help="Path to storybook.json")
    p_pdf.add_argument("-o", "--output", help="Output PDF path")
    p_pdf.set_defaults(func=cmd_pdf)

    # process-all
    p_all = sub.add_parser("process-all", help="Process all story folders in a directory")
    p_all.add_argument("stories_dir", help="Path to directory containing story folders")
    p_all.add_argument("--pdf", action="store_true", help="Also generate PDFs")
    p_all.set_defaults(func=cmd_process_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
