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
          <span v-for="dinner in latest.dinners" :key="dinner" class="dinner-tag">{{ dinner }}</span>
        </div>
        <div class="actions">
          <router-link :to="`/weeks/${latest.date}`" class="btn btn-primary">
            📖 View Full Plan
          </router-link>
          <a v-if="latest.hasPdf" :href="`/plans/${latest.date}/weekly-plan.pdf`" target="_blank" class="btn btn-outline">
            📄 Download PDF
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
            <router-link :to="`/weeks/${week.date}`" class="btn btn-primary btn-sm">View</router-link>
            <a v-if="week.hasPdf" :href="`/plans/${week.date}/weekly-plan.pdf`" target="_blank" class="btn btn-outline btn-sm">PDF</a>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const weeks = ref([])
const loading = ref(true)

const latest = computed(() => weeks.value[0] || null)
const archive = computed(() => weeks.value.slice(1))

onMounted(async () => {
  try {
    const res = await fetch('/plans/index.json')
    weeks.value = await res.json()
  } catch (e) {
    console.error('Failed to load plans index:', e)
  } finally {
    loading.value = false
  }
})
</script>
