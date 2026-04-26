# Weekly Planner Section-Correctness Architecture Plan

Source session plan: `C:\Users\dancorbiani\.copilot\session-state\d94ba78c-92a6-40db-9e07-8fdbf071cf0c\plan.md`

## Problem statement

The current weekly-planner system has grown from a prompt-driven collection of skills into a multi-stage publishing pipeline, but the section contracts are distributed across skill instructions, renderer templates, and ad hoc merge logic. This makes it easy for a section to be generated but not assembled, assembled under the wrong field name, or rendered in HTML/PDF without validation catching the omission.

The new architecture should make sections first-class: every expected section must be declared, produced, canonicalized, assembled, rendered, and validated against the same source of truth. The implementation should also improve parallel orchestration, make weekly-read inputs more flexible, and enforce history-aware variety for recurring sections such as parenting nudges, Stoic reflections, principles essays, story character beats, and newsletter themes.

## Current-state review

### Current pipeline

The repository already documents a six-phase pipeline in `.github\skills\weekly-planner\SKILL.md`:

1. Gather context: user prompt, weather, school calendar, work calendar, favorites/history.
2. Research wave 1: recipes, albums, Linkwarden weekly read, Stoic guide, principles.
3. User checkpoint for dinner and album selection.
4. Research wave 2: dinner-designer, recipe-cards, parenting-coach, nutrition-coach, child-wisdom.
5. Review and assemble into `plan_data.json`.
6. Format to markdown, HTML, and PDF, then proofread.

The actual executable merge point is `.github\skills\weekly-planner\scripts\assemble_plan.py`. It normalizes weather, albums, engagements, and day-of-week fields, then conditionally merges optional artifacts through flags such as `--parenting`, `--newsletter`, `--stoic`, `--principles`, `--child-wisdom`, and `--recipe-cards`.

Rendering is split across:

- `.github\skills\weekly-planner\templates\weekly_plan.md.j2`
- `.github\skills\booklet\templates\booklet.html.j2`
- `.github\skills\booklet\templates\partials\print-*.j2`
- `webapp\src\views\WeekView.vue` and section components

Validation currently exists mainly in:

- `.github\skills\content-validator\SKILL.md`, which documents checks but has no executable validator script.
- `.github\skills\proofreader\scripts\proofread.py`, which validates rendered outputs but currently focuses on day-level dinner/album/tips/questions/recipes, page structure, overflow, markdown, and PDF text extraction.
- `.github\skills\print-formatter\SKILL.md`, which describes the intended print-optimized copy, but `.github\skills\weekly-planner\SKILL.md` explicitly says this is documentation-only today and `plan_data_print.json` is currently copied from `plan_data.json`.

### Required newsletter/booklet sections inferred from skills and templates

The planner needs to track these sections explicitly:

| Section ID | Current source fields | Current rendering surface |
|---|---|---|
| `cover` | `week_range`, `highlight`, `elsie_no_list` / aliases | print cover, screen cover |
| `week_at_a_glance` | `days[]` weather/calendar/dinner/album | markdown, print glance, webapp glance |
| `daily_plan` | `days[]` day intro, weather, events, dinner, album, activity | markdown, print daily pages, webapp day cards |
| `daily_recipe_cards` | `days[].recipe_card` | markdown, print day pages, webapp day cards |
| `daily_chef_tips` | `days[].dinner_elevation_tips` | markdown, print day pages, webapp day cards |
| `daily_conversation` | `days[].dinner_question`, `parenting_data.dinner_questions[]` | markdown, print day pages, webapp day cards |
| `daily_principles` | `principles_data.daily_entries[]` | markdown, print daily principles pages, webapp daily cards |
| `grocery_prep` | `grocery_list`, `prep_ahead` | markdown, webapp sections; print support currently incomplete |
| `family_parenting` | `parenting_data.weekly_theme`, `dinner_questions`, `nudges`, `connection_ritual`, `recommendation`, `parent_reflection` | markdown, print family pages, webapp parenting component |
| `stoic_guide` | `stoic_data.theme`, `anchor_quote`, `meditations`, `family_exercise`, `young_stoic`, `closing_thought` | markdown, print family pages, webapp stoic component |
| `weekly_read` | `newsletter_data.clusters`, `reflections`, `fun_section`, source articles | markdown, print newsletter pages, webapp newsletter component |
| `bedtime_story` | `child_wisdom` | markdown, print story pages, webapp story section |
| `nutrition` | `nutrition_summary`, `nutrition_data`, lunch/snack recommendations, nutrient primer | markdown, webapp nutrition; print mostly back/summary-oriented today |
| `notes_back_cover` | `notes`, generated metadata | markdown, screen notes, print back cover |

There should be no first-class `kitchen_pantry` section in the new architecture. Appetizers, salads, and beverages can remain plan support data and may render inline where useful, but they should not be a required newsletter/booklet section or drive section validation unless a future run explicitly enables a supporting-menu section.

### Historical-plan review and duplication risks

Existing `weekly_plans\*\plan_data.json` files show useful history and several schema drift issues:

- Parenting themes in recent plans include `What Makes a Place Feel Like Home`, `Planting Seeds (And Waiting for Them to Grow)`, `Every Door Is a Story`, `Seeing What's Really There`, and `The Art of the Remix`.
- Stoic themes include `The Measure of Enough`, `The Things That Are Up to Us`, `Which Port Are You Sailing Toward?`, `What Is Actually Happening`, `We Were Born to Work Together`, and `Stepping Into the Role`.
- Principles themes include `Know What You Are Optimizing For`, `Thinking in Bets: Judging Decisions by Process, Not Outcome`, `Definite Thinking`, `The Maturity of Trade-Offs`, and `Roots Before Branches`.
- Newsletter themes include AI/software-engineering clusters, collagen/creatine health clusters, housing/community/place themes, and repeated "agentic/AI infrastructure" motifs.
- Story outputs include recurring Chelsie/Mamma Karen/Mertle/Mr. Bugles beats and already contain anti-repeat guidance in the child-wisdom skill.

The strongest current failure example is `weekly_plans\2026-04-19\plan_data.json`: `parenting_data` has `conversation_starters` and `parenting_nudges`, but the renderers expect `dinner_questions` and `nudges`. As a result, the parenting theme can exist while conversation starters and nudges render as empty sections. The proofreader does not fail this because it does not require top-level parenting item counts.

Other drift examples:

- Older plans include aliases such as `newsletter`, `parenting`, `nutrition`, `stoic_guide`, and `principles_guide` alongside or instead of the canonical `*_data` fields.
- `plan_data_print.json` for the latest plan is identical to `plan_data.json`, confirming that print formatting is not actually programmatic yet.
- No `validation-report.json` files exist under `weekly_plans\`, despite the content-validator documentation describing them.
- `print-days.j2` and related docs disagree about page spread shape: comments/docs mention four pages per day in some places, while the current print template renders three daily pages and uses page-number formulas that assume three pages.
- `proofread.py` uses half-letter-oriented constants while `render_booklet.py` renders A5 pages. Print validation should use the actual target page model consistently.

## Proposed architecture

### 1. Make `section_registry` the source of truth

Add a machine-readable section registry under the planner skill, for example:

`.github\skills\weekly-planner\contracts\section_registry.yaml`

Each section entry should define:

- `id`: stable section identifier such as `family_parenting`.
- `title`: human-facing title used by templates and reports.
- `producer`: source skill or script.
- `source_artifacts`: files that must exist before assembly.
- `source_paths`: canonical JSON paths in `plan_data.json`.
- `aliases`: legacy or drifted field names that can be canonicalized.
- `required`: `always`, `conditional`, or `optional`.
- `conditions`: when a conditional section must appear, such as `newsletter_data.total_articles > 0` or explicit user-provided weekly-read URLs.
- `render_targets`: markdown, screen HTML, print HTML, PDF, webapp.
- `render_selectors`: expected `data-section-id` or CSS selectors.
- `item_counts`: required counts, such as 7 daily principles, 7 dinner questions, 3 parenting nudges, 3-7 Stoic meditations.
- `print_fit_policy`: bounded/unbounded page behavior, `max_pages`, text fields that may be trimmed, and human-authored print instructions.
- `dedupe_policy`: history lookback window and fields to compare.

This registry should drive assembly validation, template instrumentation, proofreader checks, webapp navigation expectations, and report output. The goal is that adding or renaming a section requires changing one contract, not five disconnected files.

The YAML entries can be intentionally rich. The contract should use structured fields for anything the validator must enforce, plus an `instructions` block for long guidance to the formatter/editor. Example:

```yaml
- id: weekly_read
  title: The Weekly Read
  required: conditional
  conditions:
    any:
      - path: newsletter_data.clusters
        min_count: 1
      - path: run_request.weekly_read.urls
        min_count: 1
      - path: run_request.weekly_read.required_topics
        min_count: 1
  source_paths:
    - newsletter_data.clusters
    - newsletter_data.reflections
    - newsletter_data.fun_section
  render_targets: [markdown, screen_html, print_html, pdf, webapp]
  print_fit_policy:
    bounded: true
    max_pages: 4
    trim_order:
      - newsletter_data.clusters[].synthesis
      - newsletter_data.reflections
      - newsletter_data.fun_section.content
    instructions: |
      Keep every user-requested article represented. Shorten synthesis prose
      before removing article one-liners. Never remove the fun section unless
      the user explicitly disables it.
```

`max_pages` should be validated after render, not just during data validation. If a section exceeds its page budget, the print formatter should either trim according to policy or stop with a targeted error.

### 2. Add canonical data models and alias normalization

Add a small contract library under `.github\skills\weekly-planner\contracts\`:

- `models.py`: Pydantic or dataclass models for `PlanData`, `Day`, `ParentingData`, `StoicData`, `PrinciplesData`, `NewsletterData`, `NutritionData`, and `ChildWisdom`.
- `canonicalize.py`: maps historical aliases and drifted fields to canonical names.
- `schema_export.py`: exports JSON Schema for editor/tooling use.
- `section_manifest.py`: builds a per-plan `section_manifest`.

Canonicalization should happen immediately after reading any artifact and before validation. Initial alias mappings should include:

- `parenting_data.conversation_starters` -> `parenting_data.dinner_questions`
- `parenting_data.parenting_nudges` -> `parenting_data.nudges`
- top-level `parenting` -> `parenting_data`
- top-level `newsletter` -> `newsletter_data`
- top-level `stoic_guide` -> `stoic_data`
- top-level `principles_guide` -> `principles_data`
- older `story_data` or `story` -> `child_wisdom` when shape matches
- `elsie_no_go` -> `elsie_no_list`
- nutrition aliases such as `nutrition`, `lunch_recommendations`, and `snack_recommendations` into the canonical nutrition structure

Canonicalization must be explicit and reported. If a field is moved or renamed, record it in `section_manifest.aliases_applied[]`. If a field cannot be safely normalized, fail validation rather than silently rendering blank content.

### 3. Generate a `section_manifest` for every plan

Every assembled `plan_data.json` should include or sit beside a generated manifest:

`weekly_plans\<YYYY-MM-DD>\section_manifest.json`

Suggested structure:

```json
{
  "schema_version": "1.0",
  "week_range": "April 19 - 25, 2026",
  "sections": [
    {
      "id": "family_parenting",
      "required": true,
      "producer": "parenting-coach",
      "source_artifact": "parenting.json",
      "canonical_paths": [
        "parenting_data.weekly_theme",
        "parenting_data.dinner_questions",
        "parenting_data.nudges"
      ],
      "status": "pass",
      "counts": {
        "dinner_questions": 7,
        "nudges": 3
      },
      "aliases_applied": [
        "parenting_data.conversation_starters -> parenting_data.dinner_questions"
      ]
    }
  ]
}
```

The manifest should make omissions visible before rendering. A section can only be absent when the registry says it is optional or its condition is false.

### 4. Replace optional assembler flags with required section-aware assembly

Keep `assemble_plan.py` as the merge point, but evolve it into a section-aware assembler:

- Load the section registry.
- Load all known artifacts from the week folder automatically unless explicitly overridden.
- Canonicalize each artifact before merge.
- Require all sections declared as required for that run.
- Fail with actionable errors when a required artifact, required field, or expected count is missing.
- Emit `section_manifest.json`, `validation-report.json`, and a concise stderr summary.

The CLI should support:

```powershell
python .github\skills\weekly-planner\scripts\assemble_plan.py `
  weekly_plans\<YYYY-MM-DD>\days.json `
  --week-dir weekly_plans\<YYYY-MM-DD> `
  --require-sections all `
  --section-registry .github\skills\weekly-planner\contracts\section_registry.yaml
```

Manual flags can remain for advanced reruns, but the default planner path should no longer allow accidental omission of `--recipe-cards`, `--parenting`, `--principles`, or similar critical sections.

### 5. Implement executable validation gates

Add `.github\skills\content-validator\scripts\validate_content.py` or place the implementation under weekly-planner contracts and invoke it from the content-validator skill.

Validation should run in three modes:

1. `artifact`: validate individual researcher outputs before assembly.
2. `assembled`: validate canonical `plan_data.json` and `section_manifest.json`.
3. `rendered`: validate markdown, HTML, and PDF against the manifest.

Data validation should check:

- Exactly 7 days and Sunday-through-Saturday ordering.
- Every day has dinner, album, weather, calendar shape, recipe card, chef tips, and conversation question unless explicitly waived.
- Parenting has a theme, exactly 7 dinner questions, 3+ nudges, recommendation or connection ritual, and parent reflection.
- Stoic has theme, anchor quote, 3-7 meditations, family exercise, young-stoic prompt, and no recent theme/category repetition.
- Principles has theme, anchor quote, exactly 7 daily entries, each with valid essay structure.
- Weekly read has clusters when articles or user-requested topics exist; every requested URL has a source record and a downstream article reference or a documented fetch failure.
- Nutrition has summary plus lunch/snack recommendations and nutrient-primer content when requested.
- Story has title, story text, discussion prompt, character list if available, and anti-repeat checks against recent stories.

Rendered validation should check:

- Every expected section from the manifest appears in markdown, screen HTML, print HTML, and PDF when applicable.
- Required item counts render, not merely exist in JSON.
- Parent/nudge/story/stoic/newsletter sections are checked directly, not inferred from day-level stats.
- Missing optional sections are reported as skipped with the registry condition that made them optional.

### 6. Instrument templates for reliable render validation

Update booklet and markdown templates to include stable markers:

- Print HTML pages: `data-section-id`, `data-section-instance`, and `data-source-path`.
- Repeated items: `data-item-id` based on canonical JSON path or a stable content hash.
- Bounded pages: `data-fit="bounded"` and optional `data-fit-policy`.

Example:

```html
<div class="page page-parenting"
     data-section-id="family_parenting"
     data-section-instance="nudges-1"
     data-fit="bounded">
```

The proofreader should query these markers instead of relying on brittle text and CSS class heuristics. Text extraction remains useful for PDF validation, but HTML markers should be the primary source of structure truth.

### 7. Align print rendering and validation around one page model

Normalize print page assumptions:

- Decide whether daily print layout is three pages or four pages per day.
- Update `.github\skills\weekly-planner\SKILL.md`, `.github\skills\booklet\SKILL.md`, `print-days.j2`, page-number formulas, and proofreader expected structure to match.
- Use A5 dimensions consistently in `render_booklet.py`, CSS, and `proofread.py`.
- Replace hard-coded page counts with registry-derived expectations.

Add a real print-fit program:

`.github\skills\print-formatter\scripts\format_print.py`

It should:

1. Copy `plan_data.json` to `plan_data_print.json`.
2. Render/check all bounded sections, not just day pages.
3. Apply deterministic trims according to registry print policies.
4. Use Copilot SDK or final-editor only for natural-language rewrites where deterministic trimming would damage voice.
5. Re-render until all bounded pages fit or emit a failure with exact section/page/field guidance.
6. Emit `print-format-report.json`.

### 8. Refine and harmonize print styling across page types

The print booklet needs a deliberate print design system, not a collection of page-specific styles. Pages such as the bedtime story currently feel visually disconnected from the rest of the booklet. The new architecture should include a print styling pass that makes all page types feel like one publication while still allowing section-specific personality.

Add a print style contract, for example:

`.github\skills\booklet\contracts\print_style.yaml`

This contract should define:

- Typography scale for section dividers, page headers, body text, captions, blockquotes, prompts, and metadata.
- Shared page geometry: A5 dimensions, margins, safe area, baseline rhythm, and folio placement.
- Common components: section divider, page header, page folio, callout box, source line, quote block, prompt box, list item, and compact card.
- Page archetypes: cover, glance, daily, daily-principles, support, parenting, Stoic, weekly-read, bedtime-story, and back cover.
- Allowed section-specific overrides, such as story prose having slightly more generous leading while still using the same header/folio/margin system.
- Print CSS token names and forbidden one-off inline styles.

Implementation changes:

- Audit `.github\skills\booklet\templates\styles\print.css` and all print partials for duplicated, inline, or one-off styling.
- Move recurring patterns into Jinja macros and semantic CSS classes.
- Bring bedtime story pages into the same visual system: consistent page header, folio, margins, title scale, prompt styling, divider treatment, and source/metadata conventions.
- Add a style lint/validation mode that checks rendered print HTML for required classes/tokens and flags inline styles in print partials unless explicitly allowlisted.
- Add Playwright screenshot capture for representative page archetypes so visual regressions can be reviewed quickly in VS Code.
- Store style validation output in `print-style-report.json`.

The goal is not to make every page identical. The goal is a consistent publication system: readers should recognize each section as part of the same booklet even when the content type changes from meal plan to parenting note to bedtime story.

### 9. Add a history service for dedupe and continuity

Add:

`.github\skills\weekly-planner\scripts\collect_history.py`

It should scan prior plans and produce:

`weekly_plans\<YYYY-MM-DD>\history_snapshot.json`

The snapshot should include:

- Dinners, cuisines, proteins, and album titles/artists from the last 4 weeks.
- Parenting themes, dinner questions, nudges, recommendations, and connection rituals from the last 4-8 weeks.
- Stoic themes, categories, anchor quotes, meditations, and young-stoic prompts from the last 8 weeks.
- Principles themes, primary thinkers, categories, source quotes, and daily titles from the last 8 weeks.
- Newsletter cluster themes, article URLs, article titles, and fun-section topics from the last 4-8 weeks.
- Child-wisdom story titles, characters, repeated phrase n-grams, puppet traits, and lessons from the last 4 weeks.

The orchestrator should pass this snapshot into every relevant skill prompt. Validators should also enforce non-repetition with clear exceptions when the user explicitly asks for a repeat.

For parenting nudges and daily Stoic/principles content, implement both exact-match and near-match checks:

- Exact title/question/string match.
- Normalized phrase match.
- Similarity threshold for short prompts and nudge titles.
- Category rotation checks for Stoic categories and principles categories.

### 10. Expand Weekly Read ingestion beyond Linkwarden

Replace the Linkwarden-only fetch path with a source-ingestion layer:

`.github\skills\linkwarden\scripts\fetch_reading_sources.py`

Inputs should support:

```json
{
  "linkwarden_days": 7,
  "urls": [
    "https://substack.com/home/post/...",
    "https://newsletter.pragmaticengineer.com/p/..."
  ],
  "rss_feeds": [
    "https://example.com/feed"
  ],
  "required_topics": [
    "collagen peptides, Fortibone, creatine combinations"
  ],
  "include_linkwarden": true
}
```

Outputs:

- `reading_sources.json`: raw and normalized article/source records.
- `reading_ingestion_report.json`: success/failure per URL/feed, word count, extraction method, and reason for any skipped source.

Adapters:

- Linkwarden recent clips, preserving current behavior.
- Direct URLs, including Substack/Pragmatic Engineer-style pages where accessible.
- RSS/Atom feeds, with item filtering by week range or user selection.
- User-supplied topics that trigger web research and become source records.

Important constraint: the scraper should not bypass paywalls or authentication. If a source is inaccessible, record the failure and let the user provide text or rely on Linkwarden archives.

The newsletter validator should enforce:

- Every user-provided URL appears in `reading_sources.json`.
- Every successfully extracted source appears in one cluster or a documented "not used" list.
- Every `required_topic` is covered by at least one cluster or a clearly named supplemental section.
- Repeated newsletter themes from recent plans are avoided unless the new sources demand continuity.

### 11. Use a Python CLI with the Copilot SDK as the primary orchestrator

There is no architectural reason to keep running the weekly plan as a single prompt-first workflow. The better target is a Python CLI that reads `masterPrompt.md` as an input document, calls models through the Copilot SDK, runs deterministic scripts between model calls, and manages user stage gates.

The Copilot SDK is a good fit because it exposes Copilot CLI's agent runtime programmatically, supports Python and TypeScript, can create multiple sessions, supports custom tools, and can load skills. It is currently public preview, so the deterministic contract/validation layer should remain independent of the SDK.

Recommended choice: Python.

Rationale:

- Existing planner scripts and renderers are Python.
- Existing Playwright/PDF validation code is Python.
- The orchestrator can use `asyncio.gather` for parallel skill sessions.
- Pydantic or dataclasses fit the schema/canonicalization layer naturally.
- The TypeScript code in this repo is primarily the webapp, not the planning pipeline.

Add:

`.github\skills\weekly-planner\scripts\orchestrate_week.py`

Example usage:

```powershell
python .github\skills\weekly-planner\scripts\orchestrate_week.py `
  --prompt masterPrompt.md `
  --week-start 2026-04-26 `
  --interactive
```

The orchestrator should:

- Parse `masterPrompt.md` or a structured `week_request.json`.
- Create a durable `run_manifest.json` with phases, artifacts, section expectations, and status.
- Start one Copilot SDK session per skill in each parallel wave.
- Load the relevant `SKILL.md` content as instructions for each session.
- Provide custom tools for safe artifact writes, history lookup, URL ingestion, validation, and render checks.
- Restrict tool permissions by skill where possible.
- Collect outputs into the week folder with checksums.
- Run validation after each skill, retry the same skill with precise fix instructions, and cap retries.
- Stop at the existing user checkpoints.
- Resume from the last successful artifact when rerun.

Stage gates should be first-class CLI states, not comments in a prompt. The CLI should prompt the user when it needs selection, approval, suggestions, or help resolving validation failures. At minimum:

- `input_review`: confirm parsed dates, commitments, food constraints, Elsie's no-go list, weekly-read URLs/RSS feeds, and required topics.
- `dinner_album_selection`: present recipe and album candidates, accept manual selections or "pick for me" instructions.
- `section_validation_failure`: show failed section checks and ask whether to retry the producing skill, edit an artifact, disable an optional section, or stop.
- `markdown_review`: present or open the markdown draft and accept change requests before rendering.
- `print_review`: report over-budget sections, page counts, and trimming decisions before final PDF generation when the policy requires user approval.
- `final_qa`: summarize rendered-section validation and require user acknowledgement if warnings remain.

Implementation detail: the Python CLI can handle terminal prompts directly and can also wire Copilot SDK `on_user_input_request` into the same gate mechanism when an agent asks for clarification mid-run. Each gate response should be stored in `run_manifest.json` so the workflow can resume without asking the same question again.

Parallel waves:

- Wave 1: weather, school calendar, reading ingestion/newsletter, recipes, albums, Stoic guide, principles, history snapshot.
- Wave 2: dinner-designer, recipe-cards, parenting-coach, nutrition-coach, child-wisdom after dinner/album selection.
- Validation and rendering remain sequential gates because they depend on all artifacts.

Keep a no-SDK fallback path:

- All validators, canonicalizers, assembly, render, and proofread scripts should work without the SDK.
- If SDK authentication or preview changes block agent orchestration, the user can still run individual skills manually and pass artifacts through the deterministic pipeline.

### 12. Improve webapp consistency

The webapp already consumes canonical fields such as `parenting_data`, `stoic_data`, and `newsletter_data`. After adding the section registry:

- Generate a small `sections` array in `plan_data.json` or `section_manifest.json` for the webapp.
- Use it to drive the slide-out menu rather than duplicating conditional logic in `WeekView.vue`.
- Display validation/section status in development mode or hidden diagnostics.
- Ensure nutrition lunch/snack details and weekly-read source URLs can be surfaced if available.

### 13. Documentation and skill updates

Update skill docs after the contract implementation:

- Weekly-planner: point to section registry, required artifacts, SDK orchestrator, and checkpoint/resume behavior.
- Content-validator: replace documentation-only workflow with the actual script CLI.
- Print-formatter: replace copy-only guidance with `format_print.py`.
- Linkwarden/weekly-reader: document direct URL, RSS, Substack, and topic ingestion.
- Parenting, Stoic, Principles, Child-wisdom: require `history_snapshot.json` review and reference concrete dedupe fields.
- Booklet and proofreader: document `data-section-id` markers and manifest-driven validation.

## Implementation phases

### Phase A: Contracts and discovery foundation

Create the section registry, canonical models, alias normalizer, history snapshot script, and schema/manifest generation. Run the new validator against existing plan data to document baseline failures without changing rendered output.

Deliverables:

- `contracts\section_registry.yaml`
- `contracts\models.py`
- `contracts\canonicalize.py`
- `contracts\section_manifest.py`
- `scripts\collect_history.py`
- baseline validation reports for recent plans

### Phase B: Section-aware assembly and data validation

Update `assemble_plan.py` to load artifacts automatically, canonicalize aliases, enforce required sections, and emit `section_manifest.json` and `validation-report.json`.

Deliverables:

- required-section assembly mode
- artifact and assembled-data validation CLI
- canonical fixes for known drift such as parenting `conversation_starters` and `parenting_nudges`
- tests/fixtures for historical schema variants

### Phase C: Print style harmonization, template instrumentation, and render validation

Harmonize print styling, add section markers to markdown/HTML templates, align page-count/page-size assumptions, and extend `proofread.py` to compare rendered outputs against the manifest.

Deliverables:

- `print_style.yaml`
- shared print CSS tokens, page archetype classes, and Jinja macros
- bedtime story pages restyled to match the booklet system
- `print-style-report.json`
- `data-section-id` and item markers in print/screen templates
- manifest-driven structure checks
- top-level section completeness checks for parenting, Stoic, principles, weekly read, story, nutrition, grocery/prep, and notes
- PDF text checks for section sentinel text and item counts

### Phase D: Weekly Read source ingestion

Introduce flexible reading-source ingestion for Linkwarden, direct URLs, RSS/Atom feeds, and explicit research topics. Update newsletter generation and validation contracts.

Deliverables:

- `fetch_reading_sources.py`
- `reading_sources.json`
- `reading_ingestion_report.json`
- newsletter validator rules for requested URLs/topics
- updated weekly-read skill instructions

### Phase E: Programmatic print formatting

Implement real `plan_data_print.json` generation and print-fit validation for all bounded sections. Replace the copy-only workflow.

Deliverables:

- `format_print.py`
- `print-format-report.json`
- overflow fixes based on section registry policies
- consistent A5 page constants across renderer/proofreader

### Phase F: Python Copilot SDK CLI orchestrator

Add the Python CLI orchestrator after deterministic contracts are in place. Use the SDK for model-backed skill execution and retry loops, while the Python CLI owns stages, user gates, artifacts, validation, and resume behavior.

Deliverables:

- `orchestrate_week.py`
- CLI options for `--prompt`, `--week-start`, `--week-dir`, `--interactive`, `--resume`, and `--from-stage`
- `run_manifest.json`
- parallel Wave 1 and Wave 2 execution
- persisted stage-gate prompts and user responses
- skill-scoped prompts/tools
- artifact-level validation and retry loop
- checkpoint/resume behavior

### Phase G: Webapp and documentation alignment

Drive webapp section navigation from the manifest and update all skill docs so future weekly plans use the same section contract.

Deliverables:

- manifest-aware webapp navigation
- optional diagnostics for missing/skipped sections
- updated `README.md`, relevant `SKILL.md` files, and usage examples

## Acceptance criteria

- A generated weekly plan cannot pass assembly if a required section is missing, uses an unsupported alias, or has the wrong item count.
- The latest known parenting drift shape (`conversation_starters` / `parenting_nudges`) is canonicalized or fails with a clear error; it must not silently render empty.
- Every rendered markdown, HTML, and PDF output can be validated against `section_manifest.json`.
- Print styling is consistent across page archetypes, including bedtime story pages, and style validation catches unapproved inline/one-off print styles.
- Print validation checks all bounded sections, not only day pages.
- `plan_data_print.json` differs from `plan_data.json` only when required for print fit, and the differences are reported.
- User-provided weekly-read URLs and RSS feeds are ingested, tracked, and either included in the newsletter or reported with a reason they could not be used.
- Parenting nudges, Stoic themes/meditations, principles themes, newsletter clusters, and story beats consult prior plans before generation and fail validation on avoidable repetition.
- The Python Copilot SDK CLI can run independent skill waves in parallel while preserving durable artifacts, interactive stage gates, and deterministic validation gates.

## Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Copilot SDK public-preview API changes | Keep deterministic scripts and stage-gate state independent; isolate SDK usage in `orchestrate_week.py`. |
| Schema changes break old plans | Canonicalizer supports legacy aliases and reports migrations; tests use historical fixtures. |
| Render validation becomes brittle | Prefer explicit `data-section-id` markers over text heuristics. |
| PDF text extraction misses styled content | Validate print HTML structure first, then use PDF extraction for sentinel text and page count. |
| Scraping Substack/RSS content is inconsistent | Track extraction status per source; do not bypass paywalls; allow user-supplied text. |
| More validation slows creative iteration | Run fast artifact/data checks before rendering; reserve Playwright/PDF checks for post-render gates. |

## Open decisions for implementation

- Confirm the exact CLI gate behavior for non-interactive runs, such as whether `--yes` is allowed to skip optional approvals but never skip validation failures.
- Decide whether the daily print layout should be standardized as three pages per day or restored to the documented four-page spread.
- Decide which sections are always required versus conditionally required when source content exists. The plan assumes parenting, Stoic, principles, weekly read, nutrition, and story are required in the full weekly-planner workflow unless explicitly disabled by the run request.
