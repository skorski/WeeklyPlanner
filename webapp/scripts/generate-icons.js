/**
 * Generate PWA icons from favicon.svg.
 * Outputs 180x180 (apple-touch), 192x192, and 512x512 PNGs to public/icons/.
 */

import sharp from 'sharp'
import { mkdirSync } from 'fs'
import { join, dirname, resolve } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const INPUT = resolve(__dirname, '..', 'public', 'favicon.svg')
const OUT_DIR = resolve(__dirname, '..', 'public', 'icons')

mkdirSync(OUT_DIR, { recursive: true })

const sizes = [
  { size: 180, name: 'apple-touch-icon-180x180.png' },
  { size: 192, name: 'pwa-192x192.png' },
  { size: 512, name: 'pwa-512x512.png' },
  { size: 512, name: 'maskable-512x512.png', maskable: true },
]

for (const { size, name, maskable } of sizes) {
  const pipeline = sharp(INPUT).resize(size, size)

  if (maskable) {
    // Maskable icons need a safe zone — add 20% padding with background fill
    const inner = Math.round(size * 0.8)
    const padding = Math.round(size * 0.1)
    const innerBuf = await sharp(INPUT).resize(inner, inner).png().toBuffer()
    await sharp({
      create: { width: size, height: size, channels: 4, background: '#F9F8F6' },
    })
      .composite([{ input: innerBuf, left: padding, top: padding }])
      .png()
      .toFile(join(OUT_DIR, name))
  } else {
    await pipeline.png().toFile(join(OUT_DIR, name))
  }

  console.log(`  ✓ ${name} (${size}×${size})`)
}

console.log('\nIcons generated successfully.')
