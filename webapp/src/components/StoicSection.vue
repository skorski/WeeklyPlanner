<template>
  <div class="stoic-section">
    <div class="stoic-theme-header">
      <span class="stoic-category-tag">{{ data.theme?.category }}</span>
      <h3>{{ data.theme?.title }}</h3>
      <p>{{ data.theme?.description }}</p>
    </div>

    <blockquote v-if="data.anchor_quote" class="stoic-anchor-quote">
      "{{ data.anchor_quote.text }}"
      <cite>— {{ data.anchor_quote.source }}, <em>{{ data.anchor_quote.work }}</em> {{ data.anchor_quote.reference }}</cite>
    </blockquote>

    <div v-if="data.introduction" class="stoic-intro">{{ data.introduction }}</div>

    <template v-if="data.meditations?.length">
      <h4 style="font-size:15px;font-weight:600;margin-bottom:8px;">Meditations</h4>
      <div v-for="m in data.meditations" :key="m.title" class="meditation-card">
        <div v-if="m.day" class="meditation-day-label">{{ m.day }}</div>
        <h4>{{ m.title }}</h4>
        <p>{{ m.reflection }}</p>
        <p class="meditation-prompt-text"><strong>Prompt:</strong> {{ m.prompt }}</p>
        <p v-if="m.secondary_quote" class="meditation-sec-quote">
          "{{ m.secondary_quote.text }}" — <em>{{ m.secondary_quote.source }}</em>
        </p>
      </div>
    </template>

    <div v-if="data.family_exercise" class="stoic-exercise-card">
      <h4>🏛 {{ data.family_exercise.title }}</h4>
      <p>{{ data.family_exercise.description }}</p>
      <p style="font-style:italic;">{{ data.family_exercise.connection }}</p>
    </div>

    <div v-if="data.young_stoic" class="stoic-young-card">
      <h4>🌱 {{ data.young_stoic.title }}</h4>
      <p>{{ data.young_stoic.prompt }}</p>
      <p style="font-style:italic;">{{ data.young_stoic.lesson }}</p>
    </div>

    <div v-if="data.closing_thought" class="stoic-closing">
      {{ data.closing_thought }}
    </div>
  </div>
</template>

<script setup>
defineProps({ data: Object })
</script>
