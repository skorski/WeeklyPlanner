/**
 * Prebuild script: scans weekly_plans/ for plan_data.json files,
 * copies them + PDFs into public/plans/ for the Vue app to consume.
 * Also generates a manifest (plans-index.json) listing all available weeks.
 */

import { readdirSync, existsSync, copyFileSync, writeFileSync, mkdirSync, readFileSync } from 'fs'
import { join, resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..', '..')
const PLANS_SRC = join(ROOT, 'weekly_plans')
const PLANS_DEST = join(__dirname, '..', 'public', 'plans')
const STORIES_SRC = join(ROOT, 'stories')
const STORIES_DEST = join(__dirname, '..', 'public', 'stories')

// Ensure output directory exists
mkdirSync(PLANS_DEST, { recursive: true })

const weeks = []

if (!existsSync(PLANS_SRC)) {
  console.log('No weekly_plans/ directory found. Creating empty manifest.')
  writeFileSync(join(PLANS_DEST, 'index.json'), JSON.stringify([], null, 2))
  process.exit(0)
}

const folders = readdirSync(PLANS_SRC, { withFileTypes: true })
  .filter(d => d.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(d.name))
  .sort((a, b) => b.name.localeCompare(a.name)) // newest first

for (const folder of folders) {
  const weekDir = join(PLANS_SRC, folder.name)
  const planFile = join(weekDir, 'plan_data.json')

  if (!existsSync(planFile)) {
    console.log(`  Skipping ${folder.name} — no plan_data.json`)
    continue
  }

  // Create destination directory
  const destDir = join(PLANS_DEST, folder.name)
  mkdirSync(destDir, { recursive: true })

  // Copy plan_data.json
  copyFileSync(planFile, join(destDir, 'plan_data.json'))

  // Copy PDF if it exists
  const pdfFile = join(weekDir, 'weekly-plan.pdf')
  const hasPdf = existsSync(pdfFile)
  if (hasPdf) {
    copyFileSync(pdfFile, join(destDir, 'weekly-plan.pdf'))
  }

  // Read plan data for the manifest
  const planData = JSON.parse(readFileSync(planFile, 'utf-8'))
  const days = planData.days || []

  // Extract summary info for the homepage
  const dinners = days.map(d => d.dinner).filter(Boolean)
  const highlight = planData.highlight || ''

  weeks.push({
    date: folder.name,
    weekRange: planData.week_range || folder.name,
    highlight,
    dinners,
    hasPdf,
    generatedAt: planData.generated_at || '',
  })

  console.log(`  ✓ ${folder.name}: ${days.length} days, PDF: ${hasPdf ? 'yes' : 'no'}`)
}

// Write manifest
writeFileSync(join(PLANS_DEST, 'index.json'), JSON.stringify(weeks, null, 2))
console.log(`\nManifest written: ${weeks.length} week(s)`)

// ── Stories ──────────────────────────────────────────────────
mkdirSync(STORIES_DEST, { recursive: true })
const stories = []

if (existsSync(STORIES_SRC)) {
  const storyFolders = readdirSync(STORIES_SRC, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .sort((a, b) => a.name.localeCompare(b.name))

  for (const folder of storyFolders) {
    const srcDir = join(STORIES_SRC, folder.name)
    const manifestFile = join(srcDir, 'storybook.json')

    if (!existsSync(manifestFile)) continue

    const manifest = JSON.parse(readFileSync(manifestFile, 'utf-8'))
    const slug = manifest.slug || folder.name
    const destDir = join(STORIES_DEST, slug)
    mkdirSync(destDir, { recursive: true })

    // Copy storybook.json
    copyFileSync(manifestFile, join(destDir, 'storybook.json'))

    // Copy images
    const imgExts = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']
    const files = readdirSync(srcDir, { withFileTypes: true })
      .filter(f => f.isFile() && imgExts.some(ext => f.name.toLowerCase().endsWith(ext)))

    for (const f of files) {
      copyFileSync(join(srcDir, f.name), join(destDir, f.name))
    }

    // Copy PDF if exists
    const pdfFile = join(srcDir, 'storybook.pdf')
    const hasPdf = existsSync(pdfFile)
    if (hasPdf) {
      copyFileSync(pdfFile, join(destDir, 'storybook.pdf'))
    }

    // Find cover image
    const coverPage = (manifest.pages || []).find(p => p.image)
    const coverImage = coverPage ? coverPage.image : null

    stories.push({
      slug,
      title: manifest.title || folder.name,
      coverImage,
      pageCount: manifest.page_count || 0,
      tone: manifest.tone || 'default',
      hasPdf,
    })

    console.log(`  ✓ story: ${slug} (${manifest.page_count || '?'} pages)`)
  }
}

writeFileSync(join(STORIES_DEST, 'index.json'), JSON.stringify(stories, null, 2))
console.log(`Stories manifest: ${stories.length} story(ies)`)
