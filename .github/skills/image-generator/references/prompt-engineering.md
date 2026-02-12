# Image Prompt Engineering

## Core Principles

1. **Subject first** — lead with what the image depicts
2. **Style second** — artistic medium, rendering technique
3. **Details third** — lighting, color palette, composition, mood
4. **Constraints last** — aspect ratio implications, negative space

## Descriptive but Delightful

The goal is prompts that are specific enough to produce quality images but leave room for the model to surprise. Avoid over-specifying every detail.

**Too vague:**
> A cat

**Too specific (no room for delight):**
> A tabby cat with green eyes sitting on a red velvet cushion in a Victorian parlor with ornate gold frames on the walls, a fireplace on the right, afternoon sunlight coming through lace curtains at 45 degrees

**Just right:**
> A cat lounging in an old-fashioned parlor, warm afternoon light, painted in the style of a Dutch Golden Age interior

## Creativity Levels

### Low (Predictable)
Include specific colors, exact composition, named art styles, precise lighting direction. The model has little freedom.

> A watercolor painting of a red cardinal perched on a snow-covered pine branch, soft winter morning light from the upper left, muted blue-gray background, loose brushstrokes with visible paper texture

### Medium (Balanced)
Specify style and mood, suggest colors via vocabulary, leave composition open.

> A cardinal in winter, watercolor style, soft cool palette, quiet morning atmosphere

### High (Surprising)
Give theme and emotional direction, let the model interpret freely.

> The stillness of a winter morning, a small burst of warmth in the cold, watercolor

## Vocabulary Integration

When a visual vocabulary is available, weave its attributes into the prompt naturally:

**Vocabulary:**
```json
{
  "colors": [{"hex": "#2C3E50", "name": "midnight blue"}, {"hex": "#E74C3C", "name": "warm vermillion"}],
  "art_styles": ["editorial illustration", "risograph print"],
  "textures": ["grain", "halftone dots"],
  "mood_descriptors": ["contemplative", "gently playful"]
}
```

**Resulting prompt:**
> An editorial illustration of a quiet harbor at dusk, midnight blue water with warm vermillion reflections from the lighthouse, risograph print texture with visible grain and halftone dots, contemplative mood with a gently playful sense of scale

## Common Pitfalls

- **Text in images** — DALL-E 3 struggles with text. Avoid prompts requiring specific words unless absolutely necessary.
- **Counting** — "exactly 5 birds" often produces 4 or 6. Use "a small flock" instead.
- **Faces/likeness** — never request specific real people. Use descriptions: "a person with kind eyes and silver hair."
- **Negative prompts** — "no trees" often produces trees. Reframe positively: "an open meadow" instead of "a field with no trees."
- **Overly long prompts** — diminishing returns past ~200 words. DALL-E 3 internally rewrites the prompt anyway.

## Children's Book Illustrations

For consistency across multiple illustrations in a story:
- Lock the art style and color palette in the vocabulary
- Reference the same character descriptions across prompts
- Use consistent lighting direction and time of day
- Specify the same medium: "colored pencil and watercolor on textured paper"

## Weekly Planner Cover Art

For covers that capture the week's theme:
- Extract the dominant theme from the plan's narrative
- Pull weather conditions for atmospheric cues
- Reference the week's cuisine for cultural visual elements
- Keep style consistent across weeks using a shared vocabulary
