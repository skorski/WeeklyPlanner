"""Visual vocabulary builder — analyze a mood board to extract style attributes."""

import json
from pathlib import Path

from openai import APIError, AuthenticationError, APIConnectionError

from .client import get_client, get_chat_deployment, handle_api_error
from .utils import image_to_data_uri


_ANALYSIS_PROMPT = (
    "Analyze this image and extract its visual properties. Return a JSON object with:\n"
    '- "colors": array of {"hex": "#RRGGBB", "name": "descriptive name"} for the 3-5 dominant colors\n'
    '- "art_styles": array of strings describing the artistic style/medium\n'
    '- "textures": array of strings describing visible textures\n'
    '- "composition_rules": array of strings describing the composition approach\n'
    '- "mood_descriptors": array of strings describing the emotional tone\n\n'
    "Return ONLY valid JSON, no markdown fences or extra text."
)


def _analyze_single_image(image_path: Path) -> dict:
    """Analyze a single image using Azure OpenAI vision."""
    client = get_client()
    deployment = get_chat_deployment()

    try:
        data_uri = image_to_data_uri(image_path)
    except Exception as e:
        raise ValueError(
            f"Failed to read image '{image_path.name}': {e}\n"
            f"Ensure the file is a valid image (PNG, JPG, WebP, GIF) and not corrupted."
        ) from e

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _ANALYSIS_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }],
            max_tokens=1000,
        )
    except (AuthenticationError, APIConnectionError, APIError) as e:
        raise handle_api_error(
            e, f"vision analysis of '{image_path.name}' (deployment: {deployment})"
        ) from e

    if not response.choices:
        raise RuntimeError(
            f"Vision API returned no response for '{image_path.name}'.\n"
            f"The model may have been blocked by content filters."
        )

    text = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Vision model returned invalid JSON when analyzing '{image_path.name}'.\n"
            f"This sometimes happens when the model includes extra text in its response.\n"
            f"Raw response (first 500 chars): {text[:500]}\n"
            f"JSON parse error: {e}"
        ) from e


def _merge_analyses(analyses: list[dict]) -> dict:
    """Merge multiple image analyses into a unified vocabulary."""
    all_colors = []
    all_styles = set()
    all_textures = set()
    all_composition = set()
    all_mood = set()

    for a in analyses:
        all_colors.extend(a.get("colors", []))
        all_styles.update(a.get("art_styles", []))
        all_textures.update(a.get("textures", []))
        all_composition.update(a.get("composition_rules", []))
        all_mood.update(a.get("mood_descriptors", []))

    # Deduplicate colors by hex
    seen_hex = set()
    unique_colors = []
    for c in all_colors:
        h = c.get("hex", "").upper()
        if h and h not in seen_hex:
            seen_hex.add(h)
            unique_colors.append(c)

    return {
        "colors": unique_colors[:12],
        "art_styles": sorted(all_styles),
        "textures": sorted(all_textures),
        "composition_rules": sorted(all_composition),
        "mood_descriptors": sorted(all_mood),
    }


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def build_vocabulary(
    image_dir: str | Path,
    output_path: str | Path | None = None,
    name: str = "Custom Vocabulary",
    description: str = "",
) -> dict:
    """Analyze a directory of mood-board images and produce a visual vocabulary.

    Args:
        image_dir: Directory containing mood-board images.
        output_path: Optional path to write the vocabulary JSON.
        name: Name for the vocabulary.
        description: Optional description.

    Returns:
        Dict with the complete visual vocabulary.
    """
    image_dir = Path(image_dir)
    if not image_dir.exists():
        raise FileNotFoundError(
            f"Mood board directory not found: {image_dir}\n"
            f"Provide a path to a directory containing mood-board images."
        )
    if not image_dir.is_dir():
        raise NotADirectoryError(
            f"Path is not a directory: {image_dir}\n"
            f"--image-dir must point to a directory of images, not a single file."
        )

    images = [f for f in image_dir.iterdir()
              if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS]

    if not images:
        found_files = [f.name for f in image_dir.iterdir() if f.is_file()][:10]
        raise FileNotFoundError(
            f"No supported images found in {image_dir}\n"
            f"Supported formats: {', '.join(sorted(_IMAGE_EXTENSIONS))}\n"
            + (f"Files found: {', '.join(found_files)}" if found_files else "Directory is empty.")
        )

    analyses = []
    errors = []
    for img_path in images:
        try:
            analysis = _analyze_single_image(img_path)
            analyses.append(analysis)
        except Exception as e:
            errors.append(f"  - {img_path.name}: {e}")

    if not analyses:
        raise RuntimeError(
            f"Failed to analyze any of the {len(images)} images in {image_dir}.\n"
            f"Errors:\n" + "\n".join(errors)
        )

    vocabulary = _merge_analyses(analyses)
    vocabulary["name"] = name
    vocabulary["description"] = description
    vocabulary["source_images"] = [img.name for img in images]

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(vocabulary, indent=2), encoding="utf-8")

    return vocabulary
