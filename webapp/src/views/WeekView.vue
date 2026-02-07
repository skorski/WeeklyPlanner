<template>
  <div v-if="loading" class="loading">Loading plan…</div>
  <div v-else-if="!plan" class="empty-state">
    <h2>Plan not found</h2>
    <p>No data for week {{ date }}.</p>
    <router-link to="/" class="btn btn-primary" style="margin-top:16px;display:inline-flex;">← Back Home</router-link>
  </div>
  <template v-else>

    <!-- Sticky nav bar -->
    <nav class="week-nav">
      <router-link to="/" class="nav-back">← Home</router-link>
      <span class="nav-title">{{ activeSection }}</span>
      <button class="hamburger" @click="menuOpen = !menuOpen" :class="{ open: menuOpen }" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
    </nav>

    <!-- Slide-out menu -->
    <div class="menu-overlay" :class="{ open: menuOpen }" @click="menuOpen = false"></div>
    <div class="slide-menu" :class="{ open: menuOpen }">
      <div class="menu-header">Jump to…</div>

      <div class="menu-group">
        <div class="menu-group-label">Days</div>
        <button v-for="(day, i) in plan.days" :key="day.name"
          class="menu-item" :class="{ today: i === todayIndex }"
          @click="scrollTo(`day-${i}`)">
          <span class="menu-day-name">{{ shortDay(day.name) }}</span>
          <span class="menu-dinner">{{ day.dinner || '—' }}</span>
          <span v-if="i === todayIndex" class="today-badge">Today</span>
        </button>
      </div>

      <div class="menu-group">
        <div class="menu-group-label">Sections</div>
        <button class="menu-item" @click="scrollTo('glance')">Week at a Glance</button>
        <button v-if="plan.appetizers?.length" class="menu-item" @click="scrollTo('appetizers')">Appetizers</button>
        <button v-if="plan.salads?.length" class="menu-item" @click="scrollTo('salads')">Salads</button>
        <button v-if="plan.beverages?.length" class="menu-item" @click="scrollTo('beverages')">Beverages</button>
        <button v-if="plan.grocery_list" class="menu-item" @click="scrollTo('grocery')">Grocery List</button>
        <button v-if="plan.prep_ahead?.length" class="menu-item" @click="scrollTo('prep')">Prep Checklist</button>
        <button v-if="plan.parenting_data" class="menu-item" @click="scrollTo('parenting')">Parenting Corner</button>
        <button v-if="plan.newsletter_data?.clusters?.length" class="menu-item" @click="scrollTo('newsletter')">The Weekly Read</button>
      </div>

      <div class="menu-footer">
        <a v-if="hasPdf" :href="`/plans/${date}/weekly-plan.pdf`" target="_blank" class="menu-item menu-pdf">📄 Download PDF</a>
      </div>
    </div>

    <!-- Content -->
    <div class="week-container">

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
      <h2 :id="'glance'" class="section-title sticky-header">Week at a Glance</h2>
      <table class="glance-table">
        <thead>
          <tr><th></th><th>Day</th><th>Weather</th><th>Events</th><th>Dinner</th><th>Album</th></tr>
        </thead>
        <tbody>
          <tr v-for="(day, i) in plan.days" :key="day.name" :class="{ 'today-row': i === todayIndex }" @click="scrollTo(`day-${i}`)" style="cursor:pointer;">
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
      <h2 class="section-title sticky-header">Daily Plan</h2>
      <div v-for="(day, i) in plan.days" :key="day.name" :id="`day-${i}`">
        <DayCard :day="day" :isToday="i === todayIndex" />
      </div>

      <!-- Appetizers -->
      <template v-if="plan.appetizers?.length">
        <h2 id="appetizers" class="section-title sticky-header">Appetizers</h2>
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
        <h2 id="salads" class="section-title sticky-header">Salads</h2>
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
        <h2 id="beverages" class="section-title sticky-header">Beverages</h2>
        <div v-for="b in plan.beverages" :key="b.name" class="item-card">
          <h4>{{ b.name }}</h4>
          <p>{{ b.description }}</p>
          <p v-if="b.why" class="meta" style="font-style:italic;">{{ b.why }}</p>
        </div>
      </template>

      <!-- Grocery List -->
      <template v-if="plan.grocery_list && Object.keys(plan.grocery_list).length">
        <h2 id="grocery" class="section-title sticky-header">Grocery List</h2>
        <div class="grocery-section">
          <div v-for="(items, category) in plan.grocery_list" :key="category" class="grocery-category">
            <h4>{{ category }}</h4>
            <ul><li v-for="item in items" :key="item">{{ item }}</li></ul>
          </div>
        </div>
      </template>

      <!-- Prep-Ahead -->
      <template v-if="plan.prep_ahead?.length">
        <h2 id="prep" class="section-title sticky-header">Prep-Ahead Checklist</h2>
        <ul class="prep-checklist">
          <li v-for="task in plan.prep_ahead" :key="task">{{ task }}</li>
        </ul>
      </template>

      <!-- Parenting Corner -->
      <template v-if="plan.parenting_data">
        <h2 id="parenting" class="section-title sticky-header">Parenting Corner</h2>
        <ParentingSection :data="plan.parenting_data" />
      </template>

      <!-- Newsletter -->
      <template v-if="plan.newsletter_data?.clusters?.length">
        <h2 id="newsletter" class="section-title sticky-header">📰 The Weekly Read</h2>
        <NewsletterSection :data="plan.newsletter_data" />
      </template>

      <!-- Notes -->
      <template v-if="plan.notes?.length">
        <h2 class="section-title sticky-header">Notes</h2>
        <div class="support-section">
          <ul><li v-for="note in plan.notes" :key="note">{{ note }}</li></ul>
        </div>
      </template>

      <!-- Nutrition -->
      <template v-if="plan.nutrition_summary">
        <h2 class="section-title sticky-header">Nutrition</h2>
        <div class="support-section"><p>{{ plan.nutrition_summary }}</p></div>
      </template>

      <div class="week-footer">{{ plan.week_range }} · Generated {{ plan.generated_at }}</div>
    </div>
  </template>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import DayCard from '../components/DayCard.vue'
import ParentingSection from '../components/ParentingSection.vue'
import NewsletterSection from '../components/NewsletterSection.vue'

const props = defineProps({ date: String })
const plan = ref(null)
const loading = ref(true)
const hasPdf = ref(false)
const menuOpen = ref(false)
const activeSection = ref('')

// Parse the week start date from the route param (YYYY-MM-DD)
function parseWeekStart(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

// Figure out which day index matches today (0=Sun, 1=Mon, ... 6=Sat)
const todayIndex = computed(() => {
  if (!plan.value?.days?.length) return -1
  const weekStart = parseWeekStart(props.date)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffMs = today - weekStart
  const diffDays = Math.round(diffMs / 86400000)
  if (diffDays < 0 || diffDays > 6) return -1
  return diffDays
})

function shortDay(name) {
  return name?.split(' ')[0] || name
}

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

function scrollTo(id) {
  menuOpen.value = false
  nextTick(() => {
    const el = document.getElementById(id)
    if (el) {
      const navH = 48
      const y = el.getBoundingClientRect().top + window.scrollY - navH - 8
      window.scrollTo({ top: y, behavior: 'smooth' })
    }
  })
}

// Track which section is active based on scroll position
let observer = null
function setupObserver() {
  if (observer) observer.disconnect()

  const headers = document.querySelectorAll('.sticky-header[id], [id^="day-"]')
  if (!headers.length) return

  observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const id = entry.target.id
        if (id.startsWith('day-')) {
          const i = parseInt(id.split('-')[1])
          const day = plan.value?.days?.[i]
          activeSection.value = day ? `${shortDay(day.name)} — ${day.dinner || ''}` : ''
        } else {
          activeSection.value = entry.target.textContent.trim()
        }
      }
    }
  }, { rootMargin: '-56px 0px -70% 0px', threshold: 0 })

  headers.forEach(h => observer.observe(h))
}

async function loadPlan(date) {
  loading.value = true
  try {
    const res = await fetch(`/plans/${date}/plan_data.json`)
    if (!res.ok) { plan.value = null; return }
    plan.value = await res.json()

    const pdfRes = await fetch(`/plans/${date}/weekly-plan.pdf`, { method: 'HEAD' })
    hasPdf.value = pdfRes.ok
  } catch (e) {
    console.error('Failed to load plan:', e)
    plan.value = null
  } finally {
    loading.value = false
  }

  // After DOM renders, auto-scroll to today and set up observer
  await nextTick()
  await nextTick() // double-tick for v-if rendering
  setupObserver()

  if (todayIndex.value >= 0) {
    // Small delay so layout settles
    setTimeout(() => scrollTo(`day-${todayIndex.value}`), 150)
  }
}

onMounted(() => loadPlan(props.date))
watch(() => props.date, (d) => loadPlan(d))
onUnmounted(() => { if (observer) observer.disconnect() })
</script>

