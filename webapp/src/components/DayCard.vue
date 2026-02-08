<template>
  <div class="day-card" :class="{ 'day-card--today': isToday }">

    <!-- Level 1: Weather Horizon -->
    <div v-if="weatherLine" class="weather-horizon">{{ weatherLine }}</div>

    <!-- Level 2: Date Hero + Today indicator -->
    <div v-if="isToday" class="today-indicator">Today</div>
    <h3>{{ day.long_name }}</h3>

    <!-- Level 3: Engagements — Gutter Layout -->
    <div v-if="parsedEngagements.length" class="engagements">
      <div v-for="(e, idx) in parsedEngagements" :key="idx" class="engagement-row">
        <span class="engagement-time">{{ e.time }}</span>
        <span class="engagement-rule"></span>
        <span class="engagement-event">{{ e.event }}</span>
      </div>
    </div>

    <!-- The Narrative -->
    <p v-if="day.day_intro" class="day-intro">{{ day.day_intro }}</p>

    <!-- The Culinary Center -->
    <template v-if="day.dinner">
      <div class="dinner-title">{{ day.dinner }}</div>
      <span v-if="day.dinner_cuisine" class="cuisine-label">{{ day.dinner_cuisine }}</span>
      <p v-if="day.dinner_description" class="description">{{ day.dinner_description }}</p>
      <p v-if="day.dinner_key_ingredients" class="ingredients">{{ day.dinner_key_ingredients.join(', ') }}</p>
      <a v-if="day.dinner_source_url" :href="day.dinner_source_url" target="_blank" class="recipe-link">
        {{ day.dinner_source_name || 'View Recipe' }} →
      </a>
      <p v-if="day.dinner_notes" class="notes">{{ day.dinner_notes }}</p>
    </template>

    <!-- Chef's Tips -->
    <div v-if="day.dinner_elevation_tips?.length" class="elevation-tips">
      <h4>Chef's Tips</h4>
      <div v-for="tip in day.dinner_elevation_tips" :key="tip.title" class="elevation-tip">
        <span class="tip-label">{{ tip.type }}</span>
        <strong>{{ tip.title }}</strong> — {{ tip.instruction }}
      </div>
    </div>

    <!-- Preparation -->
    <details v-if="day.prep_detail" class="prep-detail">
      <summary>Preparation</summary>
      <div class="prep-meta">
        <span v-if="day.prep_detail.prep_timeline">{{ day.prep_detail.prep_timeline }}</span>
        <span v-if="day.prep_detail.active_time">Active {{ day.prep_detail.active_time }}</span>
      </div>
      <ol v-if="day.prep_detail.prep_steps" class="prep-steps">
        <li v-for="step in day.prep_detail.prep_steps" :key="step">{{ step }}</li>
      </ol>
      <div v-if="day.prep_detail.special_equipment" class="prep-equipment">
        <strong>Equipment</strong> {{ day.prep_detail.special_equipment.join(', ') }}
      </div>
      <div v-if="day.prep_detail.make_ahead" class="prep-make-ahead">
        <strong>Make ahead</strong> {{ day.prep_detail.make_ahead }}
      </div>
    </details>

    <!-- Music Gallery — The Exhale -->
    <div v-if="day.album" class="album-pairing">
      <div class="album-name">{{ day.album }}</div>
      <div class="album-meta">{{ day.album_year }} · {{ day.album_genre }}</div>
      <div v-if="day.album_description" class="album-desc">{{ day.album_description }}</div>
      <div v-if="day.album_sonic_description" class="album-sonic">{{ day.album_sonic_description }}</div>
      <div v-if="day.album_pairing_rationale" class="album-rationale">{{ day.album_pairing_rationale }}</div>
      <a v-if="day.album_spotify_url" :href="day.album_spotify_url" target="_blank" class="spotify-link">Listen on Spotify →</a>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ day: Object, isToday: Boolean, weatherLine: String })

// Parse calendar items into { time, event } pairs for gutter layout
const parsedEngagements = computed(() => {
  if (!props.day.calendar_items?.length) return []
  return props.day.calendar_items.map(item => {
    // Try to extract a time like "4:00 PM", "4:00-5:00 PM", "(evening)"
    const timeMatch = item.match(/(\d{1,2}:\d{2}(?:\s*-\s*\d{1,2}:\d{2})?\s*[AP]M)/i)
    if (timeMatch) {
      const time = timeMatch[1].toUpperCase()
      // Remove the time from the event text and clean up
      const event = item.replace(timeMatch[0], '').replace(/^\s*[,\-·]\s*/, '').replace(/\s*\(\s*\)\s*/, '').trim()
      return { time, event: event || item }
    }
    // Check for "(evening)", "(morning)" etc.
    const periodMatch = item.match(/\((evening|morning|afternoon|night)\)/i)
    if (periodMatch) {
      const time = periodMatch[1].toUpperCase()
      const event = item.replace(periodMatch[0], '').trim()
      return { time, event }
    }
    // No time found — show as all-day
    return { time: '', event: item }
  })
})
</script>
