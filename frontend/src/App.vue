<template>
  <header class="app-header">
    <nav class="main-nav">
      <router-link to="/">Dashboard</router-link> |
      <router-link to="/events">Events</router-link> |
      <router-link to="/products">Products</router-link> |
      <router-link to="/roles">Roles</router-link> |
      <router-link to="/categories">Categories</router-link>
    </nav>

    <div class="settings-wrapper">
      <router-link to="/settings" class="settings-btn" title="System Settings">
        <span class="gear-icon">⚙️</span>
      </router-link>
    </div>
  </header>

  <main class="content-area">
    <router-view />
  </main>
</template>

<style>
:root { --primary-green: #42b883; }
body { background-color: #1a1a1a; color: #eee; font-family: 'Inter', sans-serif; margin: 0; }

/* Header container for positioning */
.app-header { position: relative; background: #2c3e50; border-bottom: 1px solid #444; }

.main-nav { padding: 20px; text-align: center; }
.main-nav a { 
  color: #888; 
  text-decoration: none; 
  font-weight: bold; 
  margin: 0 15px; 
  font-size: 0.9rem; 
  text-transform: uppercase; 
  transition: color 0.2s;
}

.main-nav a.router-link-active { 
  color: var(--primary-green); 
  border-bottom: 2px solid var(--primary-green); 
  padding-bottom: 5px; 
}

/* Positioning the settings icon */
.settings-wrapper { 
  position: absolute; 
  top: 50%; 
  right: 25px; 
  transform: translateY(-50%); 
}

.settings-btn {
  text-decoration: none;
  font-size: 1.4rem;
  opacity: 0.6;
  transition: opacity 0.2s, transform 0.2s;
  display: block;
}

.settings-btn:hover { 
  opacity: 1; 
  transform: rotate(45deg); /* Subtle feedback */
}

/* Ensure active state shows green icon [cite: 2026-03-03] */
.settings-btn.router-link-active { 
  opacity: 1; 
  filter: drop-shadow(0 0 5px var(--primary-green));
}

.content-area { padding: 2rem; max-width: 1200px; margin: 0 auto; }
</style>