"""Agent-driven page breaking — no API calls.

Prepares structured requests for an LLM/agent to decide where to break
a children's story into pages, and parses the response.
"""

import json
import math
import re
from pathlib import Path


def read_story(markdown_path: str | Path) -> dict:
    """Read a markdown file and extract title and body text.

    Args:
        markdown_path: Path to a .md file containing the story.

    Returns:
        Dict with title, body, word_count, and source_path.
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"Story file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")

    # Extract title from first H1
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            title = stripped.lstrip("# ").strip()
            body_start = i + 1
            break

    if title is None:
        # Use first non-empty line as title
        for i, line in enumerate(lines):
            if line.strip():
                title = line.strip()
                body_start = i + 1
                break

    if title is None:
        title = path.stem.replace("-", " ").replace("_", " ").title()

    body = "\n".join(lines[body_start:]).strip()
    # Strip markdown formatting for clean text
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)  # bold
    body = re.sub(r"\*(.+?)\*", r"\1", body)  # italic
    body = re.sub(r"!\[.*?\]\(.*?\)", "", body)  # images
    body = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", body)  # links
    body = re.sub(r"^#{1,6}\s+", "", body, flags=re.MULTILINE)  # headings

    word_count = len(body.split())

    return {
        "title": title,
        "body": body,
        "word_count": word_count,
        "source_path": str(path),
    }


def build_page_break_request(
    story_text: str,
    image_count: int,
    words_per_page: int = 80,
) -> dict:
    """Assemble a structured request for an LLM to decide page breaks.

    Args:
        story_text: The full story body text.
        image_count: Number of illustration images available.
        words_per_page: Target words per page (default 80).

    Returns:
        Dict with system_prompt, user_prompt, and guidelines.
    """
    word_count = len(story_text.split())
    min_pages = image_count + 1  # at least one text block per image + overflow
    estimated_pages = max(min_pages, math.ceil(word_count / words_per_page))

    system_prompt = (
        "You are a children's book editor. Your job is to take a story and break it into "
        "individual pages for a picture book. Each page should contain a natural chunk of "
        "the narrative — think of how a real children's book flows, with each page turn "
        "revealing the next moment of the story.\n\n"
        "Rules:\n"
        f"- There are {image_count} illustration(s) available. The first {image_count} pages "
        f"should be marked as having images (has_image: true).\n"
        f"- Target approximately {words_per_page} words per page (range: 40-120 words).\n"
        f"- Break at natural narrative moments: scene changes, dramatic pauses, emotional shifts, "
        f"moments of discovery, or dialogue transitions.\n"
        "- Each page should feel complete on its own but create anticipation for the next.\n"
        "- The last text block should feel like a satisfying conclusion.\n"
        "- Every word of the original story must appear in exactly one page — don't skip or add text.\n\n"
        "Respond with ONLY a JSON array — no markdown fences, no extra text. Each element:\n"
        '{ "page_number": N, "text": "exact story text for this page", '
        '"has_image": true/false, "narrative_note": "brief note about why you broke here" }'
    )

    user_prompt = (
        f"Break this story into pages.\n\n"
        f"Images available: {image_count}\n"
        f"Story word count: {word_count}\n"
        f"Target pages: {estimated_pages}\n\n"
        f"Story text:\n\n{story_text}"
    )

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "guidelines": [
            f"Break into approximately {estimated_pages} pages",
            f"First {image_count} pages get has_image: true",
            f"Target ~{words_per_page} words per page (40-120 range)",
            "Break at narrative moments, not mid-sentence",
            "Preserve every word of the original text",
        ],
        "image_count": image_count,
        "word_count": word_count,
        "estimated_pages": estimated_pages,
    }


def parse_page_break_response(response_text: str) -> list[dict]:
    """Parse an LLM's page break response into structured text blocks.

    Args:
        response_text: The raw text response from the LLM (expected JSON array).

    Returns:
        List of dicts with page_number, text, has_image, narrative_note.
    """
    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # Find JSON array in response
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start:end + 1]

    try:
        pages = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse page break response as JSON.\n"
            f"Expected a JSON array of page objects.\n"
            f"Parse error: {e}\n"
            f"Response (first 500 chars): {response_text[:500]}"
        ) from e

    if not isinstance(pages, list):
        raise ValueError(
            f"Expected a JSON array, got {type(pages).__name__}.\n"
            f"Response: {response_text[:500]}"
        )

    # Validate and normalize each page
    result = []
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            raise ValueError(f"Page {i + 1} is not a dict: {page}")

        result.append({
            "page_number": page.get("page_number", i + 1),
            "text": page.get("text", ""),
            "has_image": bool(page.get("has_image", False)),
            "narrative_note": page.get("narrative_note", ""),
        })

    return result

