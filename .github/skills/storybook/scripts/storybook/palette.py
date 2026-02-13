"""Color palette extraction from images and font selection by story tone."""

import colorsys
import math
from pathlib import Path

from PIL import Image


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def _extract_colors_from_image(image_path: Path, n_colors: int = 8) -> list[tuple]:
    """Extract dominant colors from a single image using quantization."""
    img = Image.open(image_path).convert("RGB")
    # Resize for speed
    img.thumbnail((200, 200))
    quantized = img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    palette_data = quantized.getpalette()
    pixel_counts = sorted(quantized.getcolors(), key=lambda x: -x[0])

    colors = []
    for count, idx in pixel_counts:
        r = palette_data[idx * 3]
        g = palette_data[idx * 3 + 1]
        b = palette_data[idx * 3 + 2]
        colors.append({"r": r, "g": g, "b": b, "count": count})
    return colors


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _luminance(r: int, g: int, b: int) -> float:
    """Relative luminance per WCAG 2.0."""
    def linearize(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(c1: dict, c2: dict) -> float:
    l1 = _luminance(c1["r"], c1["g"], c1["b"])
    l2 = _luminance(c2["r"], c2["g"], c2["b"])
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _saturation(r: int, g: int, b: int) -> float:
    _, s, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return s


def extract_palette(image_dir: str | Path) -> dict:
    """Extract a color palette from all images in a directory.

    Returns dict with bg, text, accent, secondary as hex strings.
    """
    image_dir = Path(image_dir)
    images = sorted(
        f for f in image_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
    )
    if not images:
        # Fallback palette
        return {
            "bg": "#FFF8F0", "text": "#2C2C2C",
            "accent": "#E07A5F", "secondary": "#81B29A",
        }

    all_colors = []
    for img_path in images:
        try:
            all_colors.extend(_extract_colors_from_image(img_path))
        except Exception:
            continue

    if not all_colors:
        return {
            "bg": "#FFF8F0", "text": "#2C2C2C",
            "accent": "#E07A5F", "secondary": "#81B29A",
        }

    # Sort by luminance
    sorted_by_lum = sorted(all_colors, key=lambda c: _luminance(c["r"], c["g"], c["b"]))

    # Background: lightest color (but not pure white)
    bg = sorted_by_lum[-1]
    # Make it even lighter for readability
    bg_r = min(255, bg["r"] + (255 - bg["r"]) // 2)
    bg_g = min(255, bg["g"] + (255 - bg["g"]) // 2)
    bg_b = min(255, bg["b"] + (255 - bg["b"]) // 2)
    bg_color = {"r": bg_r, "g": bg_g, "b": bg_b}

    # Text: darkest color
    text_color = sorted_by_lum[0]

    # Enforce WCAG AA contrast (4.5:1) — darken text if needed
    while _contrast_ratio(bg_color, text_color) < 4.5 and _luminance(text_color["r"], text_color["g"], text_color["b"]) > 0.01:
        text_color = {
            "r": max(0, text_color["r"] - 15),
            "g": max(0, text_color["g"] - 15),
            "b": max(0, text_color["b"] - 15),
        }

    # Accent: most saturated color
    sorted_by_sat = sorted(all_colors, key=lambda c: _saturation(c["r"], c["g"], c["b"]), reverse=True)
    accent_color = sorted_by_sat[0]

    # Secondary: second most common midtone
    midtones = [c for c in sorted_by_lum[len(sorted_by_lum) // 4 : 3 * len(sorted_by_lum) // 4]]
    secondary_color = midtones[0] if midtones else sorted_by_lum[len(sorted_by_lum) // 2]

    return {
        "bg": _rgb_to_hex(bg_color["r"], bg_color["g"], bg_color["b"]),
        "text": _rgb_to_hex(text_color["r"], text_color["g"], text_color["b"]),
        "accent": _rgb_to_hex(accent_color["r"], accent_color["g"], accent_color["b"]),
        "secondary": _rgb_to_hex(secondary_color["r"], secondary_color["g"], secondary_color["b"]),
    }


# --- Font selection by story tone ---

_TONE_FONTS = {
    "whimsical": {
        "heading": "Baloo 2",
        "body": "Nunito",
        "keywords": ["adventure", "magic", "magical", "silly", "wonder", "whimsical",
                      "fairy", "dragon", "enchanted", "sparkle", "giggle", "flying"],
    },
    "warm": {
        "heading": "Playfair Display",
        "body": "Source Sans 3",
        "keywords": ["cozy", "warm", "gentle", "kind", "love", "hug", "home",
                      "blanket", "soup", "friend", "comfort", "snuggle"],
    },
    "mystery": {
        "heading": "Crimson Text",
        "body": "Inter",
        "keywords": ["mystery", "shadow", "dark", "secret", "hidden", "clue",
                      "detective", "puzzle", "strange", "curious", "whisper"],
    },
    "nature": {
        "heading": "Bitter",
        "body": "Lato",
        "keywords": ["forest", "river", "garden", "animal", "tree", "flower",
                      "bird", "ocean", "mountain", "leaf", "rain", "sun"],
    },
}

_DEFAULT_FONTS = {"heading": "Literata", "body": "Nunito Sans"}


def select_fonts(story_text: str) -> dict:
    """Select heading and body fonts based on story text tone.

    Returns dict with heading, body, and detected tone.
    """
    text_lower = story_text.lower()
    scores = {}
    for tone, config in _TONE_FONTS.items():
        score = sum(1 for kw in config["keywords"] if kw in text_lower)
        scores[tone] = score

    best_tone = max(scores, key=scores.get)
    if scores[best_tone] == 0:
        return {**_DEFAULT_FONTS, "tone": "default"}

    config = _TONE_FONTS[best_tone]
    return {
        "heading": config["heading"],
        "body": config["body"],
        "tone": best_tone,
    }
