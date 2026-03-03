import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue' // Import your actual Dashboard file
import ProductsView from '../views/ProductsView.vue'
import CategoriesView from '../views/CategoriesView.vue'
import RolesView from '../views/RolesView.vue'
import EventsView from '../views/EventsView.vue'

// REMOVED: The placeholders that were overwriting your views

const routes = [
  { 
    path: '/', 
    name: 'home',
    component: HomeView // Point this to the actual component
  },
  { path: '/products', component: ProductsView },
  { path: '/categories', component: CategoriesView },
  { path: '/roles', component: RolesView },
  { path: '/events', component: EventsView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router