"""Image generation utilities: I/O, format conversion, validation."""

import base64
import io
from pathlib import Path

from PIL import Image


VALID_SIZES = {"1024x1024", "1024x1792", "1792x1024"}
VALID_FORMATS = {"png", "webp", "jpeg"}
MAX_INPUT_SIZE_BYTES = 20 * 1024 * 1024  # 20MB


def load_image(path: str | Path) -> Image.Image:
    """Load an image from disk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}\n"
            f"Check that the file path is correct and the file exists."
        )
    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {path}\n"
            f"Expected an image file, not a directory."
        )
    file_size = path.stat().st_size
    if file_size > MAX_INPUT_SIZE_BYTES:
        raise ValueError(
            f"Image exceeds 20MB size limit: {path} ({file_size / 1024 / 1024:.1f}MB).\n"
            f"Resize or compress the image before processing."
        )
    if file_size == 0:
        raise ValueError(
            f"Image file is empty (0 bytes): {path}\n"
            f"The file may be corrupted or incomplete."
        )
    try:
        return Image.open(path)
    except Exception as e:
        raise ValueError(
            f"Failed to open image: {path}\n"
            f"The file may be corrupted or not a valid image format.\n"
            f"Detail: {e}"
        ) from e


def save_image(data: bytes, output_path: str | Path, fmt: str = "png") -> Path:
    """Save image bytes to disk in the specified format."""
    fmt = fmt.lower()
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Unsupported output format '{fmt}'. Supported: {', '.join(sorted(VALID_FORMATS))}")
    output_path = Path(output_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(
            f"Cannot create output directory: {output_path.parent}\n"
            f"Check file system permissions.\n"
            f"Detail: {e}"
        ) from e

    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise ValueError(
            f"Cannot decode image data for saving. The image bytes may be corrupted.\n"
            f"Detail: {e}"
        ) from e

    save_kwargs = {}
    if fmt == "webp":
        save_kwargs["quality"] = 95
    elif fmt == "png":
        save_kwargs["optimize"] = True

    try:
        img.save(output_path, format=fmt.upper(), **save_kwargs)
    except PermissionError as e:
        raise PermissionError(
            f"Cannot write to: {output_path}\n"
            f"Check file system permissions.\n"
            f"Detail: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to save image to {output_path} as {fmt.upper()}.\n"
            f"Detail: {e}"
        ) from e

    return output_path


def image_to_base64(path: str | Path) -> str:
    """Read an image file and return its base64-encoded content."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}\n"
            f"Check that the file path is correct."
        )
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except PermissionError as e:
        raise PermissionError(
            f"Cannot read image file: {path}\n"
            f"Check file system permissions.\n"
            f"Detail: {e}"
        ) from e


def base64_to_bytes(b64_string: str) -> bytes:
    """Decode a base64 string to raw bytes."""
    return base64.b64decode(b64_string)


def image_to_data_uri(path: str | Path) -> str:
    """Convert an image file to a data URI for API requests."""
    path = Path(path)
    suffix = path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(suffix, "image/png")
    b64 = image_to_base64(path)
    return f"data:{mime};base64,{b64}"


def validate_size(size: str) -> str:
    """Validate and return an image size string."""
    if size not in VALID_SIZES:
        raise ValueError(f"Invalid size '{size}'. Use: {VALID_SIZES}")
    return size


def resize_for_api(path: str | Path, max_dimension: int = 4096) -> bytes:
    """Resize an image if it exceeds API dimension limits. Returns PNG bytes."""
    img = load_image(path)
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_format_from_path(path: str | Path) -> str:
    """Infer image format from file extension."""
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in ("jpg", "jpeg"):
        return "jpeg"
    if suffix in VALID_FORMATS:
        return suffix
    return "png"
