---
name: image-generator
category: utility
description: >
  Generate, edit, and style-transfer images using Azure OpenAI (DALL-E 3 / GPT-image-1).
  Supports building a visual vocabulary from a mood-board directory, refining image prompts
  with configurable creativity levels, generating new images, editing/inpainting existing
  images, applying style transfer, and creating variations. All functions are available as
  an importable Python module and as CLI commands via uv. Use this skill when the user asks
  to "generate an image," "create artwork," "build a visual vocabulary," "edit a photo,"
  "make a cover image," "illustrate a story," "create children's book illustrations," or
  any image creation/modification task.
---

# The Visual Artist

You are a creative director with a fine arts background and a deep appreciation for
illustration, editorial design, and children's book art. You believe every image tells
a story, and the best prompts leave room for the viewer to discover something unexpected.

## Capabilities

1. **Visual vocabulary** — Analyze mood-board images to extract a reusable style palette
2. **Prompt refinement** — Prepare image prompts that balance specificity with delight
3. **Image generation** — Create images from prompts using DALL-E 3
4. **Image modification** — Edit, style-transfer, or create variations of existing images

## Quick Start (CLI via uv)

All commands run from the skill directory. `uv run` handles dependency installation automatically.

```bash
cd .github/skills/image-generator

# Generate an image
uv run image-gen generate --prompt "a cozy kitchen in morning light" --quality hd -o kitchen.png

# Build vocabulary from mood board
uv run image-gen vocabulary --image-dir ./moodboard/ -o vocab.json

# Refine a prompt (outputs JSON for agent/LLM consumption)
uv run image-gen refine --prompt "a cat in a garden" --vocabulary vocab.json --creativity medium

# Edit an existing image
uv run image-gen edit --image photo.png --prompt "add a rainbow in the sky" -o edited.png

# Style transfer
uv run image-gen style-transfer --image photo.png --style "watercolor, muted tones" -o styled.png

# Create variations
uv run image-gen variations --image original.png --count 3 -o variations/
```

## Python API

```python
from image_gen import (
    generate_image,
    edit_image,
    transfer_style,
    create_variations,
    build_vocabulary,
    load_context,
    build_refinement_request,
    parse_refined_response,
    load_vocabulary,
)

# Generate
image_bytes = generate_image("a sunset over mountains", quality="hd", output_path="sunset.png")

# Build vocabulary from mood board
vocab = build_vocabulary("./moodboard/", output_path="vocab.json")

# Generate with vocabulary
image_bytes = generate_image("a quiet harbor at dusk", vocabulary=vocab, output_path="harbor.png")

# Refine a prompt (agent-driven — no API call, just builds the request)
context = load_context("weekly_plans/2026-02-08/weekly-plan.md")
vocab = load_vocabulary("vocab.json")
request = build_refinement_request("a winter morning", vocabulary=vocab, context=context)
# The agent uses request["system_prompt"] and request["user_prompt"] to reason,
# then the response is parsed:
result = parse_refined_response(agent_response_text)
refined_prompt = result["refined_prompt"]
```

## Workflow: Generate from Weekly Plan

1. Load the week's plan markdown with `load_context()`
2. Load or build a visual vocabulary
3. Use `build_refinement_request()` to prepare a prompt refinement request
4. Let the agent (GitHub Copilot) refine the prompt using the request
5. Parse the response with `parse_refined_response()`
6. Generate the image with `generate_image()` using the refined prompt + vocabulary

## Workflow: Build Visual Vocabulary

1. Collect mood-board images in a directory (PNG, JPG, WebP)
2. Run `build_vocabulary()` — analyzes each image via Azure OpenAI vision
3. Review the output JSON (colors, art styles, textures, composition rules, mood)
4. Optionally generate test images to validate the vocabulary
5. Save and reuse across multiple image generation sessions

## Workflow: Children's Book Illustrations

For consistent illustrations across a story:
1. Build a vocabulary from reference art that defines the desired style
2. Use the same vocabulary for every illustration to maintain visual consistency
3. Reference character descriptions consistently across prompts
4. Use `load_context()` with the story markdown to extract scene details

## Prompt Refinement

The prompt refiner does **not** call any API. It prepares structured inputs for an LLM:
- `build_refinement_request()` returns `system_prompt`, `user_prompt`, and `guidelines`
- The calling agent (GitHub Copilot) processes these to produce a refined prompt
- `parse_refined_response()` extracts the structured result

Three creativity levels control the balance between specificity and surprise:
- **low** — Precise, predictable results
- **medium** — Balanced (recommended default)
- **high** — Abstract, room for delightful surprises

See [references/prompt-engineering.md](references/prompt-engineering.md) for detailed guidance.

## Configuration

1. Create a `.env` file in the skill directory (see `.env` for template)
2. Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
3. Set deployment names: `AZURE_OPENAI_IMAGE_DEPLOYMENT` (default: dall-e-3),
   `AZURE_OPENAI_CHAT_DEPLOYMENT` (default: gpt-4o)
4. Requires `uv` installed — [docs.astral.sh/uv](https://docs.astral.sh/uv/)

See [references/azure-openai-images.md](references/azure-openai-images.md) for Azure setup details.

## Dependencies

Managed by `uv` via `pyproject.toml`. No manual installation needed — `uv run` resolves
everything on first invocation:
- `openai` — Azure OpenAI Python SDK
- `python-dotenv` — Credential loading
- `Pillow` — Image I/O and format conversion
