"""Image modification: editing, style transfer, and variations."""

import json
from pathlib import Path

from openai import APIError, AuthenticationError, APIConnectionError

from .client import get_client, get_chat_deployment, get_image_deployment, handle_api_error
from .utils import (
    base64_to_bytes,
    image_to_base64,
    image_to_data_uri,
    load_image,
    save_image,
    validate_size,
)


def _validate_image_path(image_path: str | Path, param_name: str = "image") -> Path:
    """Validate that an image file exists and is readable."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Image file not found: {path}\n"
            f"Provide a valid path to an existing image file for --{param_name}."
        )
    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {path}\n"
            f"--{param_name} must point to an image file, not a directory."
        )
    supported = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    if path.suffix.lower() not in supported:
        raise ValueError(
            f"Unsupported image format: '{path.suffix}' for file {path}\n"
            f"Supported formats: {', '.join(sorted(supported))}"
        )
    return path


def _call_chat_with_image(client, deployment: str, content: list, operation: str):
    """Make a chat completion call with image output and handle errors."""
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": content}],
            modalities=["text", "image"],
            max_tokens=4096,
        )
    except (AuthenticationError, APIConnectionError, APIError) as e:
        raise handle_api_error(e, f"{operation} (deployment: {deployment})") from e

    return _extract_image_from_chat_response(response, operation)


def edit_image(
    image_path: str | Path,
    prompt: str,
    mask_path: str | Path | None = None,
    size: str = "1024x1024",
    quality: str = "standard",
    output_path: str | Path | None = None,
    output_format: str = "png",
) -> bytes:
    """Edit an image by sending it with instructions to GPT-4o.

    Args:
        image_path: Path to the source image.
        prompt: Editing instruction (e.g., "Change the sky to sunset colors").
        mask_path: Optional mask image (white = edit region).
        size: Output size.
        quality: "standard" or "hd".
        output_path: Optional file path to save the result.
        output_format: "png" or "webp".

    Returns:
        Raw image bytes.

    Raises:
        FileNotFoundError: When the image or mask file doesn't exist.
        ValueError: For invalid parameters or unsupported image formats.
        ImageGenAuthError: When Azure rejects the credentials.
        ImageGenAPIError: When the API call fails.
    """
    _validate_image_path(image_path, "image")
    if mask_path:
        _validate_image_path(mask_path, "mask")
    if not prompt or not prompt.strip():
        raise ValueError("Editing prompt cannot be empty. Describe what to change in the image.")

    client = get_client()
    deployment = get_chat_deployment()
    data_uri = image_to_data_uri(image_path)

    content = [
        {"type": "text", "text": f"Edit this image: {prompt}"},
        {"type": "image_url", "image_url": {"url": data_uri}},
    ]

    if mask_path:
        mask_uri = image_to_data_uri(mask_path)
        content.insert(1, {
            "type": "text",
            "text": "The following mask indicates the region to edit (white = edit area):"
        })
        content.insert(2, {"type": "image_url", "image_url": {"url": mask_uri}})

    image_data = _call_chat_with_image(client, deployment, content, "image editing")

    if output_path:
        save_image(image_data, output_path, fmt=output_format)

    return image_data


def transfer_style(
    image_path: str | Path,
    style_prompt: str | None = None,
    vocabulary: dict | None = None,
    output_path: str | Path | None = None,
    output_format: str = "png",
) -> bytes:
    """Re-render an image in a different artistic style.

    Args:
        image_path: Path to the source image.
        style_prompt: Description of the target style.
        vocabulary: Optional visual vocabulary to derive style from.
        output_path: Optional file path to save the result.
        output_format: "png" or "webp".

    Returns:
        Raw image bytes.

    Raises:
        FileNotFoundError: When the image file doesn't exist.
        ValueError: When neither style_prompt nor vocabulary is provided.
        ImageGenAuthError: When Azure rejects the credentials.
        ImageGenAPIError: When the API call fails.
    """
    _validate_image_path(image_path, "image")

    style_parts = []
    if style_prompt:
        style_parts.append(style_prompt)
    if vocabulary:
        if vocabulary.get("art_styles"):
            style_parts.append(f"Art style: {', '.join(vocabulary['art_styles'][:3])}")
        if vocabulary.get("colors"):
            color_names = [c.get("name", c.get("hex")) for c in vocabulary["colors"][:5]]
            style_parts.append(f"Color palette: {', '.join(color_names)}")
        if vocabulary.get("textures"):
            style_parts.append(f"Textures: {', '.join(vocabulary['textures'][:3])}")
        if vocabulary.get("mood_descriptors"):
            style_parts.append(f"Mood: {', '.join(vocabulary['mood_descriptors'][:3])}")

    if not style_parts:
        raise ValueError(
            "No style specified for transfer. Provide at least one of:\n"
            "  --style 'watercolor, muted tones'  (a text description)\n"
            "  --vocabulary vocab.json             (a visual vocabulary file)"
        )

    style_description = ". ".join(style_parts)

    client = get_client()
    deployment = get_chat_deployment()
    data_uri = image_to_data_uri(image_path)

    content = [
        {
            "type": "text",
            "text": (
                f"Re-render this image in the following style, keeping the same "
                f"subject and composition: {style_description}"
            ),
        },
        {"type": "image_url", "image_url": {"url": data_uri}},
    ]

    image_data = _call_chat_with_image(client, deployment, content, "style transfer")

    if output_path:
        save_image(image_data, output_path, fmt=output_format)

    return image_data


def create_variations(
    image_path: str | Path,
    n: int = 1,
    variation_prompt: str | None = None,
    output_path: str | Path | None = None,
    output_format: str = "png",
) -> list[bytes]:
    """Generate variations of an existing image.

    Args:
        image_path: Path to the source image.
        n: Number of variations to generate (1-10).
        variation_prompt: Optional guidance for how variations should differ.
        output_path: Optional directory to save variations.
        output_format: "png" or "webp".

    Returns:
        List of raw image bytes, one per variation.

    Raises:
        FileNotFoundError: When the image file doesn't exist.
        ValueError: For invalid parameters.
        ImageGenAuthError: When Azure rejects the credentials.
        ImageGenAPIError: When the API call fails.
    """
    _validate_image_path(image_path, "image")
    if n < 1 or n > 10:
        raise ValueError(f"Variation count must be 1-10, got {n}.")

    client = get_client()
    deployment = get_chat_deployment()
    data_uri = image_to_data_uri(image_path)

    base_instruction = (
        "Create a variation of this image. Keep the same general subject and mood "
        "but introduce subtle differences in composition, lighting, or detail."
    )
    if variation_prompt:
        base_instruction += f" Specifically: {variation_prompt}"

    results = []
    for i in range(n):
        content = [
            {"type": "text", "text": base_instruction},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]

        image_data = _call_chat_with_image(
            client, deployment, content, f"variation {i + 1}/{n}"
        )
        results.append(image_data)

        if output_path:
            out_dir = Path(output_path)
            out_dir.mkdir(parents=True, exist_ok=True)
            save_image(image_data, out_dir / f"variation_{i + 1}.{output_format}",
                       fmt=output_format)

    return results


def _extract_image_from_chat_response(response, operation: str) -> bytes:
    """Extract image bytes from a chat completion response with image output."""
    if not response.choices:
        raise RuntimeError(
            f"No response choices returned during {operation}.\n"
            f"The model returned an empty response. This may indicate a content filter "
            f"silently blocked the output."
        )

    message = response.choices[0].message

    # Check finish_reason for content filtering
    finish_reason = getattr(response.choices[0], "finish_reason", None)
    if finish_reason == "content_filter":
        raise RuntimeError(
            f"Content filter blocked the output during {operation}.\n"
            f"The model generated a response but it was filtered by Azure's content safety.\n"
            f"Modify the prompt to avoid content that may trigger safety filters."
        )

    # Check for image content in the response
    if hasattr(message, "content") and isinstance(message.content, list):
        for part in message.content:
            if hasattr(part, "type") and part.type == "image":
                if hasattr(part, "image") and hasattr(part.image, "data"):
                    return base64_to_bytes(part.image.data)

    # If we got text but no image, include it in the error
    text_content = ""
    if hasattr(message, "content"):
        if isinstance(message.content, str):
            text_content = message.content
        elif isinstance(message.content, list):
            text_parts = [p.text for p in message.content
                          if hasattr(p, "type") and p.type == "text" and hasattr(p, "text")]
            text_content = " ".join(text_parts)

    raise RuntimeError(
        f"No image found in model response during {operation}.\n"
        f"The model responded with text but did not generate an image.\n"
        f"Possible causes:\n"
        f"  - The deployment '{get_chat_deployment()}' may not support image output\n"
        f"  - The model may need 'modalities: [\"text\", \"image\"]' support enabled\n"
        f"  - The prompt may have been interpreted as a text-only request\n"
        + (f"Model's text response: {text_content[:500]}" if text_content else "")
    )
