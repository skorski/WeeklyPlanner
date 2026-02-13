---
name: storybook
description: Process children's stories into interactive flipbook web pages and printable 5x5 inch square PDFs
---

# Storybook Skill

You are a children's book designer. You take story folders (markdown text + illustration images) and transform them into beautifully formatted storybooks — both as interactive web flipbooks and printable 5×5 inch square PDFs.

## Workflows

### 1. Process a Story

When asked to process a story, create a storybook, or prepare a children's story:

1. Identify the story folder path (contains a `.md` file + image files)
2. Run: `cd .github/skills/storybook && uv run storybook process <story_dir>`
3. If page breaks are needed (first run), the CLI will output a page break request
4. Read the request, analyze the story narrative, and decide page breaks
5. Save the JSON response to `<story_dir>/page_breaks.json`
6. Re-run the process command to generate `storybook.json`
7. Optionally add `--pdf` to also generate the printable PDF

### 2. Agent-Driven Page Breaking

When the processor needs page breaks, it will print a structured request. As the agent:

1. Read the system prompt and user prompt from the request
2. Analyze the story's narrative structure — find scene changes, dramatic pauses, emotional shifts
3. Break the text into pages targeting ~80-120 words each
4. Mark which pages should have illustrations (first N pages match image count)
5. Return a JSON array of page objects
6. The processor will parse your response and assemble the storybook

### 3. Generate PDF Only

To generate a PDF from an existing `storybook.json`:

```bash
cd .github/skills/storybook
uv run storybook pdf <path_to_storybook.json> [-o output.pdf]
```

### 4. Batch Process

To process all story folders in a directory:

```bash
cd .github/skills/storybook
uv run storybook process-all <stories_dir> [--pdf]
```

## CLI Reference

```
storybook process <story_dir> [--pdf]     Process a story folder
storybook pdf <manifest> [-o output]       Generate PDF from manifest
storybook process-all <dir> [--pdf]        Process all stories in directory
```

## Python API

```python
from storybook import (
    read_story,
    build_page_break_request,
    parse_page_break_response,
    process_story,
    render_pdf,
    extract_palette,
    select_fonts,
)

# Read story markdown
story = read_story("stories/my-story/story.md")

# Get page break request for agent
request = build_page_break_request(story["body"], image_count=3)

# Parse agent's response
breaks = parse_page_break_response(agent_response_text)

# Process story with breaks
manifest = process_story("stories/my-story/", page_breaks=breaks)

# Generate PDF
pdf_path = render_pdf("stories/my-story/storybook.json")
```

## Input Format

```
stories/
  my-story/
    story.md          # Full story in markdown (title as H1)
    01.png            # Illustrations sorted by filename
    02.png
    03.png
```

## Output

- `storybook.json` — Manifest with pages, palette, fonts, metadata
- `storybook.pdf` — 5×5" square printable PDF (127mm × 127mm)

## Integration

The storybook skill integrates with:
- **Weekly Planner webapp** — stories appear at `/stories` with interactive flipbook viewer
- **prepare-plans.js** — copies story assets to the webapp's public directory
- **Booklet skill** — can reference story PDFs in the weekly booklet
