<template>
  <div class="viewer-container" :style="paletteVars">
    <div class="viewer-header">
      <router-link to="/stories" class="back-link">← Stories</router-link>
      <h1 v-if="storybook">{{ storybook.title }}</h1>
    </div>

    <div v-if="loading" class="loading">Loading story…</div>

    <div v-else-if="error" class="error-state">
      <h2>Story not found</h2>
      <p>{{ error }}</p>
      <router-link to="/stories" class="text-link">Back to Stories</router-link>
    </div>

    <template v-else-if="storybook">
      <div class="flipbook-wrapper">
        <div ref="flipbookEl" class="flipbook">
          <div
            v-for="(page, idx) in displayPages"
            :key="idx"
            class="flipbook-page"
            :class="`page-${page.type}`"
          >
            <!-- Cover -->
            <template v-if="page.type === 'cover'">
              <img
                v-if="page.image"
                :src="`/stories/${slug}/${page.image}`"
                class="cover-image"
                :alt="page.title"
              />
              <div class="cover-title">{{ page.title || storybook.title }}</div>
            </template>

            <!-- Image (left side of spread) -->
            <template v-else-if="page.type === 'image'">
              <img
                :src="`/stories/${slug}/${page.image}`"
                class="spread-image"
                alt="Illustration"
              />
            </template>

            <!-- Text (right side of spread, or text-only) -->
            <template v-else-if="page.type === 'text'">
              <div class="text-content">
                <p>{{ page.text }}</p>
              </div>
            </template>

            <!-- End -->
            <template v-else-if="page.type === 'end'">
              <div class="end-content">
                <div class="end-decoration">✿</div>
                <div class="end-text">The End</div>
                <div class="end-flourish">• • •</div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="nav-bar">
        <button @click="prevPage" :disabled="currentPage <= 0" class="nav-btn">← Prev</button>
        <span class="page-indicator">{{ currentPage + 1 }} / {{ totalPages }}</span>
        <button @click="nextPage" :disabled="currentPage >= totalPages - 1" class="nav-btn">Next →</button>
      </div>

      <!-- Download -->
      <div v-if="storybook.hasPdf !== false" class="download-bar">
        <a :href="`/stories/${slug}/storybook.pdf`" target="_blank" class="download-link">
          📄 Download PDF
        </a>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { PageFlip } from 'page-flip'

const route = useRoute()
const slug = route.params.slug

const storybook = ref(null)
const loading = ref(true)
const error = ref(null)
const flipbookEl = ref(null)
const currentPage = ref(0)
let pageFlipInstance = null

const paletteVars = computed(() => {
  if (!storybook.value?.palette) return {}
  const p = storybook.value.palette
  return {
    '--story-bg': p.bg,
    '--story-text': p.text,
    '--story-accent': p.accent,
    '--story-secondary': p.secondary,
  }
})

// Expand spreads into individual pages for the flipbook
const displayPages = computed(() => {
  if (!storybook.value?.pages) return []
  const pages = []
  for (const page of storybook.value.pages) {
    if (page.type === 'spread') {
      // Image page (left)
      pages.push({ type: 'image', image: page.image })
      // Text page (right)
      pages.push({ type: 'text', text: page.text })
    } else {
      pages.push(page)
    }
  }
  return pages
})

const totalPages = computed(() => displayPages.value.length)

function prevPage() {
  if (pageFlipInstance) {
    pageFlipInstance.flipPrev()
  }
}

function nextPage() {
  if (pageFlipInstance) {
    pageFlipInstance.flipNext()
  }
}

onMounted(async () => {
  try {
    const res = await fetch(`/stories/${slug}/storybook.json`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    storybook.value = await res.json()
  } catch (e) {
    error.value = `Could not load story: ${e.message}`
    loading.value = false
    return
  }

  loading.value = false

  await nextTick()

  // Initialize page-flip
  if (flipbookEl.value && displayPages.value.length > 0) {
    try {
      pageFlipInstance = new PageFlip(flipbookEl.value, {
        width: 400,
        height: 400,
        size: 'stretch',
        showCover: true,
        mobileScrollSupport: true,
        useMouseEvents: true,
        swipeDistance: 30,
        flippingTime: 800,
        maxShadowOpacity: 0.3,
      })

      const children = flipbookEl.value.querySelectorAll('.flipbook-page')
      pageFlipInstance.loadFromHTML(children)

      pageFlipInstance.on('flip', (e) => {
        currentPage.value = e.data
      })
    } catch (e) {
      console.error('PageFlip init error:', e)
    }
  }
})

onBeforeUnmount(() => {
  if (pageFlipInstance) {
    pageFlipInstance.destroy()
    pageFlipInstance = null
  }
})
</script>

<style scoped>
.viewer-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}

.viewer-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.viewer-header h1 {
  font-size: 1.6rem;
  margin: 0.5rem 0 0;
}

.back-link {
  color: #666;
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: #333;
}

.flipbook-wrapper {
  display: flex;
  justify-content: center;
  margin: 1rem 0;
}

.flipbook {
  width: 800px;
  max-width: 100%;
  height: 400px;
}

.flipbook-page {
  background: var(--story-bg, #FFF8F0);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* Cover */
.page-cover {
  flex-direction: column;
  text-align: center;
  padding: 1.5rem;
}

.cover-image {
  max-width: 70%;
  max-height: 60%;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.cover-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--story-text, #2C2C2C);
  line-height: 1.3;
}

/* Image spread page */
.page-image {
  padding: 0.75rem;
}

.page-image .spread-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

/* Text page */
.page-text {
  padding: 2rem;
}

.text-content {
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--story-text, #2C2C2C);
}

/* End page */
.page-end {
  flex-direction: column;
  text-align: center;
}

.end-content {
  text-align: center;
}

.end-decoration {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.end-text {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--story-accent, #E07A5F);
}

.end-flourish {
  margin-top: 0.75rem;
  font-size: 1rem;
  color: var(--story-secondary, #81B29A);
  letter-spacing: 4px;
}

/* Navigation */
.nav-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  margin-top: 1rem;
}

.nav-btn {
  padding: 0.5rem 1.25rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.15s;
}

.nav-btn:hover:not(:disabled) {
  background: #f0f0f0;
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.page-indicator {
  font-size: 0.85rem;
  color: #888;
}

.download-bar {
  text-align: center;
  margin-top: 1rem;
}

.download-link {
  color: #555;
  text-decoration: none;
  font-size: 0.9rem;
}

.download-link:hover {
  color: #333;
}

.loading, .error-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #888;
}

@media (max-width: 600px) {
  .flipbook {
    height: 300px;
  }
}
</style>
