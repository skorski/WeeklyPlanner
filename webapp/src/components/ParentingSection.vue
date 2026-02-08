<template>
  <div class="parenting-section">
    <div v-if="data.weekly_theme" class="theme-banner">
      <h3>{{ data.weekly_theme.title }}</h3>
      <p>{{ data.weekly_theme.description }}</p>
    </div>

    <template v-if="data.dinner_questions?.length">
      <h4 class="section-label">Dinner Conversation Starters</h4>
      <div v-for="q in data.dinner_questions" :key="q.question" class="question-card">
        <div class="question-day">{{ q.day }} — {{ q.dinner || '' }}</div>
        <div class="question-text">"{{ q.question }}"</div>
        <div class="question-why">{{ q.why }}</div>
      </div>
    </template>

    <template v-if="data.nudges?.length">
      <h4 class="section-label" style="margin-top:24px;">Parenting Nudges</h4>
      <div v-for="n in data.nudges" :key="n.title" class="nudge-card">
        <h4>{{ n.title }}</h4>
        <p style="font-style:italic;">{{ n.context }}</p>
        <p>{{ n.suggestion }}</p>
        <ol v-if="n.how_to" class="nudge-steps">
          <li v-for="step in n.how_to" :key="step">{{ step }}</li>
        </ol>
      </div>
    </template>

    <div v-if="data.recommendation" class="book-rec">
      <div>
        <h4>{{ data.recommendation.title }}<span v-if="data.recommendation.author"> by {{ data.recommendation.author }}</span></h4>
        <p>{{ data.recommendation.why }}</p>
        <p style="font-style:italic;">{{ data.recommendation.connection }}</p>
      </div>
    </div>

    <div v-if="data.parent_reflection" class="reflection-box">
      {{ data.parent_reflection }}
    </div>
  </div>
</template>

<script setup>
defineProps({ data: Object })
</script>
