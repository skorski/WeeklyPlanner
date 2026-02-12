"""Prompt refinement — agent-driven, no external API calls.

Prepares structured requests for an LLM/agent to refine image prompts,
and parses the responses. The actual reasoning is handled by the caller
(e.g., GitHub Copilot or any other LLM).
"""

import json
import re
from pathlib import Path


def load_context(markdown_path: str | Path) -> dict:
    """Read a markdown file and extract structured context for prompt refinement.

    Extracts themes, moods, key elements, and constraints from markdown
    content such as weekly plans, story outlines, or theme descriptions.

    Args:
        markdown_path: Path to a .md file.

    Returns:
        Dict with keys: raw_text, title, headings, themes, elements.
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Extract title (first H1)
    title = None
    headings = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and title is None:
            title = stripped.lstrip("# ").strip()
        elif stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading_text = stripped.lstrip("# ").strip()
            headings.append({"level": level, "text": heading_text})

    return {
        "raw_text": text,
        "title": title,
        "headings": headings,
        "source_path": str(path),
    }


def load_vocabulary(vocabulary_path: str | Path) -> dict:
    """Load a visual vocabulary JSON file.

    Args:
        vocabulary_path: Path to a vocabulary .json file.

    Returns:
        Dict with vocabulary data (colors, art_styles, textures, etc.).
    """
    path = Path(vocabulary_path)
    if not path.exists():
        raise FileNotFoundError(f"Vocabulary file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# --- Creativity level configurations ---

_CREATIVITY_CONFIGS = {
    "low": {
        "description": "Very descriptive and predictable",
        "guidelines": [
            "Specify exact colors by name (e.g., 'cadmium yellow', 'cerulean blue')",
            "Name the precise art style or artist reference",
            "Describe lighting direction and intensity explicitly",
            "Include composition details (rule of thirds, centered, etc.)",
            "Mention specific textures and materials",
            "The result should closely match what someone imagines when reading the prompt",
        ],
    },
    "medium": {
        "description": "Balanced — descriptive enough for quality, vague enough for surprise",
        "guidelines": [
            "Specify the general color palette or mood rather than exact colors",
            "Name the art style broadly (e.g., 'watercolor' not 'wet-on-wet Sargent-style watercolor')",
            "Suggest atmosphere rather than exact lighting",
            "Leave composition open — describe the scene, not the framing",
            "The result should feel familiar but contain delightful unexpected details",
        ],
    },
    "high": {
        "description": "Abstract and surprising — maximum creative freedom",
        "guidelines": [
            "Focus on emotion and atmosphere rather than concrete details",
            "Use metaphorical or poetic language",
            "Avoid naming specific art styles — describe the feeling instead",
            "Leave colors, composition, and lighting entirely to interpretation",
            "The result should surprise and delight — the viewer discovers the image rather than predicting it",
        ],
    },
}


def build_refinement_request(
    raw_prompt: str,
    vocabulary: dict | None = None,
    context: dict | None = None,
    creativity_level: str = "medium",
) -> dict:
    """Assemble a structured request for an LLM to refine an image prompt.

    Args:
        raw_prompt: The user's original image prompt.
        vocabulary: Optional visual vocabulary dict (from load_vocabulary or build_vocabulary).
        context: Optional context dict (from load_context).
        creativity_level: "low", "medium", or "high".

    Returns:
        Dict with system_prompt, user_prompt, and guidelines for the LLM.
    """
    if creativity_level not in _CREATIVITY_CONFIGS:
        raise ValueError(f"Invalid creativity_level '{creativity_level}'. Use: low, medium, high")

    config = _CREATIVITY_CONFIGS[creativity_level]

    system_prompt = (
        "You are an expert image prompt engineer. Your job is to refine a raw image "
        "prompt into one that will produce a beautiful, high-quality image when sent to "
        "an AI image generation model (DALL-E 3 or GPT-image-1).\n\n"
        f"Creativity level: {creativity_level} — {config['description']}.\n\n"
        "Guidelines:\n" + "\n".join(f"- {g}" for g in config["guidelines"]) + "\n\n"
        "Respond in this exact format:\n"
        "REFINED_PROMPT: <your refined prompt here>\n"
        "EXPLANATION: <brief explanation of what you changed and why>\n"
        "VOCABULARY_APPLIED: <comma-separated list of vocabulary elements you incorporated, or 'none'>"
    )

    user_parts = [f"Raw prompt: {raw_prompt}"]

    if vocabulary:
        vocab_summary = []
        if "colors" in vocabulary:
            color_names = [c.get("name", c.get("hex", "")) for c in vocabulary["colors"]]
            vocab_summary.append(f"Colors: {', '.join(color_names)}")
        if "art_styles" in vocabulary:
            vocab_summary.append(f"Art styles: {', '.join(vocabulary['art_styles'])}")
        if "textures" in vocabulary:
            vocab_summary.append(f"Textures: {', '.join(vocabulary['textures'])}")
        if "mood_descriptors" in vocabulary:
            vocab_summary.append(f"Mood: {', '.join(vocabulary['mood_descriptors'])}")
        if "composition_rules" in vocabulary:
            vocab_summary.append(f"Composition: {', '.join(vocabulary['composition_rules'])}")
        user_parts.append("\nVisual vocabulary:\n" + "\n".join(vocab_summary))

    if context:
        context_parts = []
        if context.get("title"):
            context_parts.append(f"Source: {context['title']}")
        if context.get("headings"):
            heading_texts = [h["text"] for h in context["headings"][:10]]
            context_parts.append(f"Key sections: {', '.join(heading_texts)}")
        # Include a trimmed version of raw text for theme extraction
        if context.get("raw_text"):
            trimmed = context["raw_text"][:2000]
            context_parts.append(f"\nContext excerpt:\n{trimmed}")
        user_parts.append("\nMarkdown context:\n" + "\n".join(context_parts))

    return {
        "system_prompt": system_prompt,
        "user_prompt": "\n".join(user_parts),
        "guidelines": config["guidelines"],
        "creativity_level": creativity_level,
    }


def parse_refined_response(response_text: str) -> dict:
    """Parse an LLM's refinement response into structured output.

    Args:
        response_text: The raw text response from the LLM.

    Returns:
        Dict with refined_prompt, explanation, and vocabulary_applied.
    """
    result = {
        "refined_prompt": "",
        "explanation": "",
        "vocabulary_applied": [],
    }

    # Parse REFINED_PROMPT
    match = re.search(r"REFINED_PROMPT:\s*(.+?)(?=\nEXPLANATION:|\Z)", response_text, re.DOTALL)
    if match:
        result["refined_prompt"] = match.group(1).strip()

    # Parse EXPLANATION
    match = re.search(r"EXPLANATION:\s*(.+?)(?=\nVOCABULARY_APPLIED:|\Z)", response_text, re.DOTALL)
    if match:
        result["explanation"] = match.group(1).strip()

    # Parse VOCABULARY_APPLIED
    match = re.search(r"VOCABULARY_APPLIED:\s*(.+)", response_text)
    if match:
        raw = match.group(1).strip()
        if raw.lower() != "none":
            result["vocabulary_applied"] = [v.strip() for v in raw.split(",") if v.strip()]

    # Fallback: if no structured format found, treat entire response as the refined prompt
    if not result["refined_prompt"]:
        result["refined_prompt"] = response_text.strip()

    return result
