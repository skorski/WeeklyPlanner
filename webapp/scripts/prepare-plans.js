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
