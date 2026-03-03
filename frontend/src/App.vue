<template>
  <nav class="main-nav">
    <router-link to="/">Dashboard</router-link> |
    <router-link to="/events">Events</router-link> |
    <router-link to="/products">Products</router-link> |
    <router-link to="/roles">Roles</router-link> |
    <router-link to="/categories">Categories</router-link>
  </nav>
  <main class="content-area">
    <router-view />
  </main>
</template>

<style>
:root { --primary-green: #42b883; }
body { background-color: #1a1a1a; color: #eee; font-family: 'Inter', sans-serif; margin: 0; }
.main-nav { padding: 20px; background: #2c3e50; border-bottom: 1px solid #444; text-align: center; }
.main-nav a { color: #888; text-decoration: none; font-weight: bold; margin: 0 15px; font-size: 0.9rem; text-transform: uppercase; }
.main-nav a.router-link-active { color: var(--primary-green); border-bottom: 2px solid var(--primary-green); padding-bottom: 5px; }
.content-area { padding: 2rem; max-width: 1200px; margin: 0 auto; }
</style>