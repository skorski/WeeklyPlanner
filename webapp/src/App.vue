<template>
  <div id="app-root">
    <nav class="site-nav" v-if="$route.name !== 'home'">
      <router-link to="/" class="nav-brand">← Weekly Planner</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
</script>
