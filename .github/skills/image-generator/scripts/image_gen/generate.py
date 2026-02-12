"""Image generation using Azure OpenAI (DALL-E 3 / GPT-image-1)."""

import json
from pathlib import Path

from openai import APIError, AuthenticationError, APIConnectionError

from .client import get_client, get_image_deployment, handle_api_error
from .utils import base64_to_bytes, save_image, validate_size


def _apply_vocabulary(prompt: str, vocabulary: dict) -> str:
    """Weave visual vocabulary attributes into a prompt."""
    parts = [prompt]

    if vocabulary.get("art_styles"):
        parts.append(f"Style: {', '.join(vocabulary['art_styles'][:3])}")
    if vocabulary.get("colors"):
        color_names = [c.get("name", c.get("hex")) for c in vocabulary["colors"][:5]]
        parts.append(f"Color palette: {', '.join(color_names)}")
    if vocabulary.get("textures"):
        parts.append(f"Texture: {', '.join(vocabulary['textures'][:3])}")
    if vocabulary.get("mood_descriptors"):
        parts.append(f"Mood: {', '.join(vocabulary['mood_descriptors'][:3])}")

    return ". ".join(parts)


def generate_image(
    prompt: str,
    vocabulary: dict | None = None,
    quality: str = "standard",
    size: str = "1024x1024",
    style: str = "natural",
    output_path: str | Path | None = None,
    output_format: str = "png",
) -> bytes:
    """Generate an image from a text prompt.

    Args:
        prompt: Text description of the desired image.
        vocabulary: Optional visual vocabulary dict to apply.
        quality: "standard" or "hd".
        size: "1024x1024", "1024x1792", or "1792x1024".
        style: "natural" or "vivid".
        output_path: Optional file path to save the image.
        output_format: "png" or "webp".

    Returns:
        Raw image bytes.

    Raises:
        ValueError: For invalid parameters (quality, size, format).
        ImageGenConfigError: When Azure credentials are missing or invalid.
        ImageGenAuthError: When Azure rejects the credentials.
        ImageGenAPIError: When the API call fails (rate limit, content policy, etc.).
    """
    validate_size(size)
    if quality not in ("standard", "hd"):
        raise ValueError(f"Invalid quality '{quality}'. Use: standard, hd")
    if style not in ("natural", "vivid"):
        raise ValueError(f"Invalid style '{style}'. Use: natural, vivid")
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty. Provide a text description of the desired image.")

    final_prompt = _apply_vocabulary(prompt, vocabulary) if vocabulary else prompt

    client = get_client()
    deployment = get_image_deployment()

    try:
        response = client.images.generate(
            model=deployment,
            prompt=final_prompt,
            size=size,
            quality=quality,
            style=style,
            response_format="b64_json",
            n=1,
        )
    except (AuthenticationError, APIConnectionError, APIError) as e:
        raise handle_api_error(e, f"image generation (deployment: {deployment})") from e

    if not response.data:
        raise RuntimeError(
            f"Image generation returned no results for deployment '{deployment}'.\n"
            f"The API responded successfully but the data array is empty.\n"
            f"This may indicate a content filter silently blocked the image."
        )

    b64 = getattr(response.data[0], "b64_json", None)
    if not b64:
        revised = getattr(response.data[0], "revised_prompt", "")
        raise RuntimeError(
            f"Image generation response missing image data (b64_json is empty).\n"
            f"Revised prompt was: {revised}\n"
            f"This may indicate the model could not produce an image for this prompt."
        )

    image_data = base64_to_bytes(b64)

    if output_path:
        save_image(image_data, output_path, fmt=output_format)

    return image_data
