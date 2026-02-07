<template>
  <div class="day-card" :class="{ 'day-card--today': isToday }">
    <div v-if="isToday" class="today-indicator">📍 Today</div>
    <h3>{{ day.long_name }}</h3>
    <p v-if="day.day_intro" class="day-intro">{{ day.day_intro }}</p>
    <div v-if="day.weather" class="weather">
      {{ weatherIcon }} {{ day.weather }}
      <span v-if="day.weather_detail"> · {{ day.weather_detail }}</span>
    </div>

    <div v-if="day.calendar_items?.length" style="margin-bottom:10px;">
      <div v-for="item in day.calendar_items" :key="item" class="calendar-item">📅 {{ item }}</div>
    </div>

    <template v-if="day.dinner">
      <div class="dinner-title">{{ day.dinner }}</div>
      <span v-if="day.dinner_cuisine" class="cuisine-tag">{{ day.dinner_cuisine }}</span>
      <p v-if="day.dinner_description" class="description">{{ day.dinner_description }}</p>
      <p v-if="day.dinner_key_ingredients" class="ingredients">{{ day.dinner_key_ingredients.join(', ') }}</p>
      <a v-if="day.dinner_source_url" :href="day.dinner_source_url" target="_blank" class="recipe-link">
        📖 Recipe: {{ day.dinner_source_name || 'View recipe' }}
      </a>
      <p v-if="day.dinner_notes" class="notes">{{ day.dinner_notes }}</p>
    </template>

    <!-- Elevation tips -->
    <div v-if="day.dinner_elevation_tips?.length" class="elevation-tips">
      <h4>🔥 Chef's Tips</h4>
      <div v-for="tip in day.dinner_elevation_tips" :key="tip.title" class="elevation-tip">
        <span class="tip-label">{{ tip.type }}:</span>
        <strong>{{ tip.title }}</strong> — {{ tip.instruction }}
      </div>
    </div>

    <!-- Prep detail -->
    <details v-if="day.prep_detail" class="prep-detail">
      <summary>🍳 Full Prep Instructions</summary>
      <div class="prep-meta">
        <span v-if="day.prep_detail.prep_timeline" class="prep-meta-item">⏱ {{ day.prep_detail.prep_timeline }}</span>
        <span v-if="day.prep_detail.active_time" class="prep-meta-item">👩‍🍳 Active: {{ day.prep_detail.active_time }}</span>
      </div>
      <ol v-if="day.prep_detail.prep_steps" class="prep-steps">
        <li v-for="step in day.prep_detail.prep_steps" :key="step">{{ step }}</li>
      </ol>
      <div v-if="day.prep_detail.special_equipment" class="prep-equipment">
        🔧 <strong>Equipment:</strong> {{ day.prep_detail.special_equipment.join(', ') }}
      </div>
      <div v-if="day.prep_detail.make_ahead" class="prep-make-ahead">
        💡 <strong>Make ahead:</strong> {{ day.prep_detail.make_ahead }}
      </div>
    </details>

    <!-- Album pairing -->
    <div v-if="day.album" class="album-pairing">
      <div class="album-name">🎵 {{ day.album }}</div>
      <div class="album-meta">{{ day.album_year }} · {{ day.album_genre }}</div>
      <div v-if="day.album_description" class="album-desc">{{ day.album_description }}</div>
      <div v-if="day.album_sonic_description" class="album-sonic">🔊 {{ day.album_sonic_description }}</div>
      <div v-if="day.album_pairing_rationale" class="album-rationale">{{ day.album_pairing_rationale }}</div>
      <a v-if="day.album_spotify_url" :href="day.album_spotify_url" target="_blank" class="spotify-link">🎧 Listen on Spotify</a>
    </div>

    <!-- Prep notes -->
    <div v-if="day.prep_notes?.length" class="prep-notes">
      <h4>Prep Notes</h4>
      <ul><li v-for="note in day.prep_notes" :key="note">{{ note }}</li></ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ day: Object, isToday: Boolean })

const weatherIcon = computed(() => {
  const w = (props.day.weather || '').toLowerCase()
  if (w.includes('snow')) return '❄️'
  if (w.includes('rain') || w.includes('shower')) return '🌧️'
  if (w.includes('cloud') || w.includes('overcast')) return '☁️'
  if (w.includes('partly')) return '⛅'
  if (w.includes('sun') || w.includes('clear')) return '☀️'
  return '🌤️'
})
</script>
