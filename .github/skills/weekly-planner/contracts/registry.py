from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY_PATH = Path(__file__).with_name("section_registry.yaml")


def load_yaml_or_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            f"PyYAML is required to read {path}. Install pyyaml or use JSON."
        ) from exc
    payload = yaml.safe_load(text)
    return payload or {}


def load_section_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path else DEFAULT_REGISTRY_PATH
    registry = load_yaml_or_json(registry_path)
    registry.setdefault("schema_version", "1.0")
    registry.setdefault("sections", [])
    return registry


def split_path(path: str) -> list[str]:
    return [part for part in path.split(".") if part]


def resolve_path(data: Any, path: str) -> list[Any]:
    """Resolve a small JSONPath-like dotted path.

    Supports list expansion with ``[]`` suffix, for example:
    ``days[].recipe_card.nonna_says``.
    """
    values = [data]
    for token in split_path(path):
        expand = token.endswith("[]")
        key = token[:-2] if expand else token
        next_values: list[Any] = []
        for value in values:
            if isinstance(value, dict):
                child = value.get(key)
                if expand:
                    if isinstance(child, list):
                        next_values.extend(child)
                    elif child is not None:
                        next_values.append(child)
                elif child is not None:
                    next_values.append(child)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        child = item.get(key)
                        if expand and isinstance(child, list):
                            next_values.extend(child)
                        elif child is not None:
                            next_values.append(child)
        values = next_values
        if not values:
            break
    return values


def value_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1 if value.strip() else 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 1


def path_count(data: Any, path: str) -> int:
    values = resolve_path(data, path)
    if not values:
        return 0
    if len(values) == 1:
        return value_count(values[0])
    return sum(value_count(v) for v in values)


def has_path_value(data: Any, path: str) -> bool:
    return path_count(data, path) > 0


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip().lower())

