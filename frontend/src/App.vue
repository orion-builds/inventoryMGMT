<template>
  <div id="app">
    <LoginView v-if="!isAuthenticated" @login-success="checkAuth" />

    <template v-else>
      <header class="app-header">
        <nav class="main-nav">
          <router-link to="/">Dashboard</router-link> |
          <router-link to="/events">Events</router-link> |
          <router-link to="/roles">Inventory</router-link> |
          <router-link to="/products">Products</router-link> |
          <router-link to="/categories">Categories</router-link>
        </nav>

        <div class="action-icons">
          <span class="user-display">{{ currentUser }}</span>
          
          <router-link to="/help" class="icon-btn" title="Help & Mechanics">
            <span>❔</span>
          </router-link>
          
          <router-link to="/settings" class="icon-btn settings-btn" title="System Settings">
            <span>⚙️</span>
          </router-link>

          <button @click="logout" class="logout-btn" title="Logout">
            <span>🚪</span>
          </button>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import LoginView from './components/LoginView.vue'; // Ensure this path is correct [cite: 2026-03-08]

const isAuthenticated = ref(false);
const currentUser = ref('');
const router = useRouter();

// Check if a 30-day token exists in browser memory [cite: 2026-03-05, 2026-03-08]
const checkAuth = () => {
  const token = localStorage.getItem('token');
  if (token) {
    isAuthenticated.value = true;
    currentUser.value = localStorage.getItem('username') || 'User';
  }
};

const logout = () => {
  // Show a standard browser confirmation pop-up [cite: 2026-03-08]
  const confirmed = window.confirm("Are you sure you want to log out?");
  
  if (confirmed) {
    localStorage.clear(); // Wipe the 30-day session token [cite: 2026-03-05, 2026-03-08]
    isAuthenticated.value = false;
    currentUser.value = '';
    router.push('/'); // Optional: Redirect to the base path if using router [cite: 2026-03-05]
  }
};

// Run check immediately when app loads [cite: 2026-03-05, 2026-03-08]
onMounted(checkAuth);
</script>

<style>
:root { --primary-green: #42b883; }
body { background-color: #1a1a1a; color: #eee; font-family: 'Inter', sans-serif; margin: 0; }

.app-header { position: relative; background: #2c3e50; border-bottom: 1px solid #444; }
.main-nav { padding: 20px; text-align: center; }
.main-nav a { 
  color: #888; text-decoration: none; font-weight: bold; 
  margin: 0 15px; font-size: 0.9rem; text-transform: uppercase; transition: color 0.2s;
}
.main-nav a.router-link-active { 
  color: var(--primary-green); border-bottom: 2px solid var(--primary-green); padding-bottom: 5px; 
}

.action-icons { 
  position: absolute; top: 50%; right: 25px; transform: translateY(-50%); 
  display: flex; align-items: center; gap: 20px;
}

/* User & Logout Styling [cite: 2026-03-06] */
.user-display { font-size: 1rem; color: #888; font-weight: bold; border-right: 1px solid #444; padding-right: 20px}
.logout-btn { 
  background: none; border: none; cursor: pointer; font-size: 1.2rem; 
  opacity: 0.6; transition: opacity 0.2s; padding: 0; display: flex; align-items: center; justify-content: center;
}
.logout-btn:hover { opacity: 1; }

.icon-btn { text-decoration: none; font-size: 1.4rem; opacity: 0.6; transition: opacity 0.2s, transform 0.2s; display: block; }
.icon-btn:hover { opacity: 1; }
.settings-btn:hover { transform: rotate(45deg); }
.icon-btn.router-link-active { opacity: 1; filter: drop-shadow(0 0 5px var(--primary-green)); }

.content-area { padding: 2rem; max-width: 1200px; margin: 0 auto; }
</style>