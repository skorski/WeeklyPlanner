<template>
  <div class="stories-container">
    <div class="stories-header">
      <router-link to="/" class="back-link">← Home</router-link>
      <h1>Children's Stories</h1>
      <p class="subtitle">Illustrated stories for bedtime and beyond</p>
    </div>

    <div v-if="loading" class="loading">Loading stories…</div>

    <div v-else-if="stories.length === 0" class="empty-state">
      <h2>No stories yet</h2>
      <p>Process a story folder with the storybook skill to add stories here.</p>
    </div>

    <div v-else class="stories-grid">
      <router-link
        v-for="story in stories"
        :key="story.slug"
        :to="`/stories/${story.slug}`"
        class="story-card"
      >
        <div class="story-cover">
          <img
            v-if="story.coverImage"
            :src="`/stories/${story.slug}/${story.coverImage}`"
            :alt="story.title"
          />
          <div v-else class="cover-placeholder">📖</div>
        </div>
        <div class="story-info">
          <h3>{{ story.title }}</h3>
          <div class="story-meta">
            {{ story.pageCount }} pages
            <span v-if="story.hasPdf" class="pdf-badge">PDF</span>
          </div>
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stories = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/stories/index.json')
    stories.value = await res.json()
  } catch (e) {
    console.error('Failed to load stories:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stories-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.stories-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.stories-header h1 {
  font-size: 2rem;
  margin: 0.5rem 0 0.25rem;
}

.stories-header .subtitle {
  color: #666;
  font-size: 1rem;
}

.back-link {
  color: #666;
  text-decoration: none;
  font-size: 0.9rem;
}

.back-link:hover {
  color: #333;
}

.stories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.5rem;
}

.story-card {
  text-decoration: none;
  color: inherit;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.story-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
}

.story-cover {
  aspect-ratio: 1;
  overflow: hidden;
  background: #f5f0e8;
}

.story-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
}

.story-info {
  padding: 0.75rem 1rem 1rem;
}

.story-info h3 {
  font-size: 1rem;
  margin: 0 0 0.25rem;
  line-height: 1.3;
}

.story-meta {
  font-size: 0.8rem;
  color: #888;
}

.pdf-badge {
  background: #e8f5e9;
  color: #2e7d32;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  margin-left: 6px;
}

.loading, .empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #888;
}
</style>
