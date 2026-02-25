import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '',
      name: 'home',
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/manage-database',
      name: 'manage-database',
      component: () => import('../views/ManageDatabaseView.vue')
    },
    {
      path: '/editor',
      name: 'editor',
      component: () => import('../views/EditorView.vue')
    },
    {
      path: '/jobs',
      name: 'jobs-list',
      component: () => import('../views/JobsListView.vue')
    },
    {
      path: '/jobs/complete',
      name: 'jobs-complete-list',
      component: () => import('../views/JobsCompleteListView.vue')
    },
    {
      path: '/query',
      name: 'query',
      component: () => import('../views/QueryView.vue')
    },
  ]
})

export default router
