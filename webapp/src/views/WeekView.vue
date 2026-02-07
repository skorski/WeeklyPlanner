<template>
  <div v-if="loading" class="loading">Loading plan…</div>
  <div v-else-if="!plan" class="empty-state">
    <h2>Plan not found</h2>
    <p>No data for week {{ date }}.</p>
    <router-link to="/" class="btn btn-primary" style="margin-top:16px;display:inline-flex;">← Back Home</router-link>
  </div>
  <div v-else class="week-container">

    <!-- Cover -->
    <div class="cover-screen">
      <h1>Weekly Planner</h1>
      <div class="week-range">{{ plan.week_range }}</div>
      <div v-if="plan.highlight" class="highlight">{{ plan.highlight }}</div>
      <div class="cover-actions">
        <a v-if="hasPdf" :href="`/plans/${date}/weekly-plan.pdf`" target="_blank" class="btn btn-outline btn-sm">📄 PDF</a>
      </div>
    </div>

    <!-- Week at a Glance -->
    <h2 class="section-title">Week at a Glance</h2>
    <table class="glance-table">
      <thead>
        <tr><th></th><th>Day</th><th>Weather</th><th>Events</th><th>Dinner</th><th>Album</th></tr>
      </thead>
      <tbody>
        <tr v-for="day in plan.days" :key="day.name">
          <td>{{ weatherIcon(day.weather) }}</td>
          <td class="day-name">{{ day.name }}</td>
          <td>{{ day.weather || '—' }}</td>
          <td>{{ day.calendar_items?.join('; ') || '—' }}</td>
          <td>{{ day.dinner || '—' }}</td>
          <td>{{ day.album || '—' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Daily Plan -->
    <h2 class="section-title">Daily Plan</h2>
    <DayCard v-for="day in plan.days" :key="day.name" :day="day" />

    <!-- Appetizers -->
    <template v-if="plan.appetizers?.length">
      <h2 class="section-title">Appetizers</h2>
      <div v-for="a in plan.appetizers" :key="a.name" class="item-card">
        <h4>{{ a.name }}</h4>
        <span v-if="a.cuisine" class="cuisine-tag" style="margin-bottom:6px;">{{ a.cuisine }}</span>
        <p>{{ a.description }}</p>
        <p v-if="a.key_ingredients" class="meta">{{ a.key_ingredients.join(', ') }}</p>
        <a v-if="a.source_url" :href="a.source_url" target="_blank" class="recipe-link">📖 {{ a.source_name || 'View recipe' }}</a>
      </div>
    </template>

    <!-- Salads -->
    <template v-if="plan.salads?.length">
      <h2 class="section-title">Salads</h2>
      <div v-for="s in plan.salads" :key="s.name" class="item-card">
        <div v-if="s.salad_type" class="cuisine-tag" style="margin-bottom:6px;">{{ s.salad_type.replace('_',' ') }}</div>
        <h4>{{ s.name }}</h4>
        <p>{{ s.description }}</p>
        <p v-if="s.key_ingredients" class="meta">{{ s.key_ingredients.join(', ') }}</p>
        <div v-if="s.dressing" class="dressing"><strong>Dressing:</strong> {{ s.dressing }}</div>
        <div v-if="s.flavor_rationale" class="rationale">{{ s.flavor_rationale }}</div>
        <a v-if="s.source_url" :href="s.source_url" target="_blank" class="recipe-link">📖 {{ s.source_name || 'View recipe' }}</a>
      </div>
    </template>

    <!-- Beverages -->
    <template v-if="plan.beverages?.length">
      <h2 class="section-title">Beverages</h2>
      <div v-for="b in plan.beverages" :key="b.name" class="item-card">
        <h4>{{ b.name }}</h4>
        <p>{{ b.description }}</p>
        <p v-if="b.why" class="meta" style="font-style:italic;">{{ b.why }}</p>
      </div>
    </template>

    <!-- Grocery List -->
    <template v-if="plan.grocery_list && Object.keys(plan.grocery_list).length">
      <h2 class="section-title">Grocery List</h2>
      <div class="grocery-section">
        <div v-for="(items, category) in plan.grocery_list" :key="category" class="grocery-category">
          <h4>{{ category }}</h4>
          <ul><li v-for="item in items" :key="item">{{ item }}</li></ul>
        </div>
      </div>
    </template>

    <!-- Prep-Ahead -->
    <template v-if="plan.prep_ahead?.length">
      <h2 class="section-title">Prep-Ahead Checklist</h2>
      <ul class="prep-checklist">
        <li v-for="task in plan.prep_ahead" :key="task">{{ task }}</li>
      </ul>
    </template>

    <!-- Parenting Corner -->
    <template v-if="plan.parenting_data">
      <h2 class="section-title">Parenting Corner</h2>
      <ParentingSection :data="plan.parenting_data" />
    </template>

    <!-- Newsletter -->
    <template v-if="plan.newsletter_data?.clusters?.length">
      <h2 class="section-title">📰 The Weekly Read</h2>
      <NewsletterSection :data="plan.newsletter_data" />
    </template>

    <!-- Notes -->
    <template v-if="plan.notes?.length">
      <h2 class="section-title">Notes</h2>
      <div class="support-section">
        <ul><li v-for="note in plan.notes" :key="note">{{ note }}</li></ul>
      </div>
    </template>

    <!-- Nutrition -->
    <template v-if="plan.nutrition_summary">
      <h2 class="section-title">Nutrition</h2>
      <div class="support-section"><p>{{ plan.nutrition_summary }}</p></div>
    </template>

    <div class="week-footer">{{ plan.week_range }} · Generated {{ plan.generated_at }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import DayCard from '../components/DayCard.vue'
import ParentingSection from '../components/ParentingSection.vue'
import NewsletterSection from '../components/NewsletterSection.vue'

const props = defineProps({ date: String })
const plan = ref(null)
const loading = ref(true)
const hasPdf = ref(false)

function weatherIcon(weather) {
  if (!weather) return ''
  const w = weather.toLowerCase()
  if (w.includes('snow')) return '❄️'
  if (w.includes('rain') || w.includes('shower')) return '🌧️'
  if (w.includes('cloud') || w.includes('overcast')) return '☁️'
  if (w.includes('partly')) return '⛅'
  if (w.includes('sun') || w.includes('clear')) return '☀️'
  return '🌤️'
}

async function loadPlan(date) {
  loading.value = true
  try {
    const res = await fetch(`/plans/${date}/plan_data.json`)
    if (!res.ok) { plan.value = null; return }
    plan.value = await res.json()

    // Check if PDF exists
    const pdfRes = await fetch(`/plans/${date}/weekly-plan.pdf`, { method: 'HEAD' })
    hasPdf.value = pdfRes.ok
  } catch (e) {
    console.error('Failed to load plan:', e)
    plan.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => loadPlan(props.date))
watch(() => props.date, (d) => loadPlan(d))
</script>
