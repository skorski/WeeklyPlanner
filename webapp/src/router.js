import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import WeekView from './views/WeekView.vue'
import StoriesView from './views/StoriesView.vue'
import StoryViewerView from './views/StoryViewerView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/weeks/:date', name: 'week', component: WeekView, props: true },
  { path: '/stories', name: 'stories', component: StoriesView },
  { path: '/stories/:slug', name: 'story', component: StoryViewerView, props: true },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
