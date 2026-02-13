<template>
  <div class="home-container">
    <div class="home-hero">
      <h1>Weekly Planner</h1>
      <div class="subtitle">Family Dinners · Music · Life</div>
    </div>

    <div v-if="loading" class="loading">Loading plans…</div>

    <div v-else-if="weeks.length === 0" class="empty-state">
      <h2>No plans yet</h2>
      <p>Run the weekly planner to create your first week.</p>
    </div>

    <template v-else>
      <!-- Latest week — hero card -->
      <div class="latest-week">
        <div class="week-label">This Week</div>
        <h2>{{ latest.weekRange }}</h2>
        <div v-if="latest.highlight" class="highlight">{{ latest.highlight }}</div>
        <div class="dinner-preview">
          {{ latest.dinners.join(', ') }}
        </div>
        <div class="actions">
          <router-link :to="`/weeks/${latest.date}`" class="text-link">
            View Full Plan →
          </router-link>
          <a v-if="latest.hasPdf" :href="`/plans/${latest.date}/weekly-plan.pdf`" target="_blank" class="text-link">
            Download PDF
          </a>
        </div>
      </div>

      <!-- Archive -->
      <div v-if="archive.length > 0" class="archive-section">
        <h3>Previous Weeks</h3>
        <div v-for="week in archive" :key="week.date" class="archive-card">
          <div class="week-info">
            <h4>{{ week.weekRange }}</h4>
            <div class="dinners-summary">{{ week.dinners.slice(0, 4).join(' · ') }}<span v-if="week.dinners.length > 4"> + {{ week.dinners.length - 4 }} more</span></div>
          </div>
          <div class="archive-actions">
            <router-link :to="`/weeks/${week.date}`" class="text-link">View</router-link>
            <a v-if="week.hasPdf" :href="`/plans/${week.date}/weekly-plan.pdf`" target="_blank" class="text-link">PDF</a>
          </div>
        </div>
      </div>

      <!-- Children's Stories -->
      <div v-if="storyCount > 0" class="stories-section">
        <h3>Children's Stories</h3>
        <p>{{ storyCount }} {{ storyCount === 1 ? 'story' : 'stories' }} available</p>
        <router-link to="/stories" class="text-link">Browse Stories →</router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const weeks = ref([])
const loading = ref(true)
const storyCount = ref(0)

const latest = computed(() => weeks.value[0] || null)
const archive = computed(() => weeks.value.slice(1))

onMounted(async () => {
  try {
    const res = await fetch('/plans/index.json')
    weeks.value = await res.json()
  } catch (e) {
    console.error('Failed to load plans index:', e)
  }
  try {
    const res = await fetch('/stories/index.json')
    const stories = await res.json()
    storyCount.value = stories.length
  } catch (e) {
    // stories index may not exist yet
  }
  loading.value = false
})
</script>
