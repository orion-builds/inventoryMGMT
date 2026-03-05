import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ProductsView from '../views/ProductsView.vue'
import CategoriesView from '../views/CategoriesView.vue'
import RolesView from '../views/RolesView.vue'
import EventsView from '../views/EventsView.vue'
import SettingsView from '../views/SettingsView.vue'
import HelpView from '../views/HelpView.vue'

const routes = [
  { 
    path: '/', 
    name: 'home',
    component: HomeView 
  },
  { path: '/products', name: 'products', component: ProductsView },
  { path: '/categories', name: 'categories', component: CategoriesView },
  { path: '/roles', name: 'roles', component: RolesView },
  { path: '/events', name: 'events', component: EventsView },
  { path: '/settings', name: 'settings', component: SettingsView },
  { path: '/help', name: 'help', component: HelpView}
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router