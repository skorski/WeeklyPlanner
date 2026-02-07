<template>
  <div class="newsletter-section">
    <div v-for="cluster in data.clusters" :key="cluster.theme" class="cluster">
      <h3>{{ cluster.theme }}</h3>
      <p>{{ cluster.synthesis }}</p>
      <ul>
        <li v-for="article in cluster.articles" :key="article.url">
          <strong>{{ article.title }}</strong>
          <em v-if="article.tags?.length"> ({{ article.tags.join(', ') }})</em>
          <span v-if="article.one_liner"><br>{{ article.one_liner }}</span>
        </li>
      </ul>
    </div>

    <div v-if="data.reflections" class="through-line">
      <strong>The Through-Line:</strong> {{ data.reflections }}
    </div>

    <div v-if="data.fun_section" class="fun-box">
      <h3>{{ data.fun_section.title || 'And Finally…' }}</h3>
      <p>{{ data.fun_section.content }}</p>
      <p v-if="data.fun_section.source_url" class="fun-source">
        Source: <a :href="data.fun_section.source_url" target="_blank">{{ data.fun_section.source_name || 'Link' }}</a>
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps({ data: Object })
</script>
