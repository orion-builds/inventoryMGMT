<template>
  <div class="login-container">
    <div class="login-box">
      <h2>InventoryMGMT</h2>
      <p class="subtitle">Please sign in to continue</p>
      
      <form @submit.prevent="handleLogin">
        <div class="input-group">
          <label>Username</label>
          <input v-model="username" type="text" required placeholder="e.g. Dad" />
        </div>
        
        <div class="input-group">
          <label>Password</label>
          <input v-model="password" type="password" required placeholder="••••••••" />
        </div>
        
        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Login' }}
        </button>
        
        <p v-if="error" class="error-msg">{{ error }}</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const username = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

const emit = defineEmits(['login-success']);

const handleLogin = async () => {
  loading.value = true;
  error.value = '';
  
  try {
    const response = await fetch('http://127.0.0.1:8000/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // SAVE THE TOKEN FOR 30 DAYS [cite: 2026-03-05, 2026-03-08]
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('username', data.username);
      
      emit('login-success');
    } else {
      error.value = data.detail || 'Login failed';
    }
  } catch (err) {
    error.value = 'Could not connect to server';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0a;
}
.login-box {
  background: #121212;
  padding: 40px;
  border-radius: 16px;
  border: 1px solid #1e1e1e;
  width: 100%;
  max-width: 400px;
  text-align: center;
}
.input-group {
  text-align: left;
  margin-bottom: 20px;
}
input {
  width: 90%;
  padding: 12px;
  background: #1a1a1a;
  border: 2px solid #333;
  color: white;
  border-radius: 8px;
  margin-top: 8px;
}
button {
  width: 30%;
  padding: 14px;
  background: #42b883;
  color: black;
  font-weight: bold;
  border-radius: 8px;
  border: none;
  cursor: pointer;
}
.error-msg { color: #ff5252; margin-top: 15px; font-size: 0.9rem; }
</style>