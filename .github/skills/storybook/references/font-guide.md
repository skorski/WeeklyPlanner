# Font Selection Guide

The storybook skill automatically selects fonts based on the detected tone of the story text. Tone detection uses keyword matching against the story body.

## Tone → Font Mapping

| Tone | Keywords | Heading Font | Body Font |
|------|----------|-------------|-----------|
| **Whimsical/Playful** | adventure, magic, fairy, dragon, sparkle, giggle, flying, silly, wonder | Baloo 2 | Nunito |
| **Warm/Cozy** | cozy, warm, gentle, kind, love, hug, home, blanket, friend, comfort | Playfair Display | Source Sans 3 |
| **Mystery/Dramatic** | mystery, shadow, dark, secret, hidden, clue, detective, puzzle, whisper | Crimson Text | Inter |
| **Nature/Outdoors** | forest, river, garden, animal, tree, flower, bird, ocean, mountain, rain | Bitter | Lato |
| **Default** | (no strong keyword matches) | Literata | Nunito Sans |

## How It Works

1. The story body text is scanned for keywords in each category
2. The category with the most keyword matches wins
3. If no category scores above zero, the default pairing is used
4. All fonts are loaded from Google Fonts via `@import` in the HTML template

## Color Palette

Colors are extracted from the story's illustration images:

- **Background**: Lightest dominant color (lightened further for readability)
- **Text**: Darkest color with WCAG AA contrast enforcement (4.5:1 minimum)
- **Accent**: Most saturated color (for titles, decorations)
- **Secondary**: Midtone color (for subtle elements)
