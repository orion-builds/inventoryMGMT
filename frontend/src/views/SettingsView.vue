<script setup>
import { ref, onMounted, computed } from 'vue'

const globalAlpha = ref(0.3)
const defaultH = ref(0.015) // The holding penalty [cite: 2026-03-03]
const saving = ref(false)
const message = ref('')

// Simulation variables [cite: 2026-03-03]
const simBasePrice = ref(50)
const simExcessDays = ref(30)
const simWTP = computed(() => {
  return simBasePrice.value * Math.pow((1 - defaultH.value), simExcessDays.value)
})

const fetchSettings = async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/settings/')
    const data = await res.json()
    if (data.global_ema_alpha) globalAlpha.value = parseFloat(data.global_ema_alpha)
    if (data.default_holding_penalty) defaultH.value = parseFloat(data.default_holding_penalty)
  } catch (err) { console.error(err) }
}

const saveSettings = async (key, value) => {
  saving.value = true
  try {
    await fetch(`http://127.0.0.1:8000/settings/${key}?value=${value}`, { method: 'PATCH' })
    message.value = "Settings updated!"
    setTimeout(() => message.value = '', 3000)
  } finally { saving.value = false }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="settings-container">
    <h1>System Settings</h1>
    
    <section class="settings-card">
      <h3>Price Smoothing (EMA Alpha)</h3>
      <input v-model.number="globalAlpha" type="range" min="0.01" max="1.0" step="0.01" />
      <div class="val-row">
        <span class="val">{{ globalAlpha.toFixed(2) }}</span>
        <button @click="saveSettings('global_ema_alpha', globalAlpha)" class="btn-save">Apply</button>
      </div>
    </section>

    <section class="settings-card penalty-card">
      <h3>Inventory Holding Penalty ($H$)</h3>
      <p class="explanation">
        Determines how much you discount your Willingness To Pay for every day you are "stocked up" beyond your buffer.
      </p>
      
      <div class="simulator-box">
        <div class="sim-controls">
          <label>Daily Penalty: <strong>{{ (defaultH * 100).toFixed(1) }}%</strong></label>
          <input v-model.number="defaultH" type="range" min="0.001" max="0.05" step="0.001" />
          
          <label>Excess Days: <strong>{{ simExcessDays }} days</strong></label>
          <input v-model.number="simExcessDays" type="range" min="0" max="120" />
        </div>
        
        <div class="sim-result">
          <span class="tiny-label">SIMULATED WTP</span>
          <div class="wtp-calc">
            S${{ simBasePrice }} &times; {{ (1 - defaultH).toFixed(3) }}<sup>{{ simExcessDays }}</sup> = 
            <span class="final-wtp">S${{ simWTP.toFixed(2) }}</span>
          </div>
          <p class="pct-label">({{ Math.round((simWTP / simBasePrice) * 100) }}% of market price)</p>
        </div>
      </div>

      <button @click="saveSettings('default_holding_penalty', defaultH)" class="btn-save full">
        Update Global Penalty
      </button>
    </section>
  </div>
</template>

<style scoped>
.settings-container { max-width: 800px; margin: 0 auto; padding: 40px; }
.settings-card { background: #1a1a1a; padding: 24px; border-radius: 12px; border-left: 4px solid var(--primary-green); margin-bottom: 24px; }
.explanation { font-size: 0.85rem; color: #888; margin-bottom: 20px; }

.simulator-box { 
  display: grid; grid-template-columns: 1fr 1fr; gap: 30px; 
  background: #111; padding: 20px; border-radius: 8px; margin-bottom: 20px;
}
.sim-controls { display: flex; flex-direction: column; gap: 15px; }
.sim-controls label { font-size: 0.75rem; color: #666; text-transform: uppercase; }

.sim-result { border-left: 1px solid #333; padding-left: 30px; display: flex; flex-direction: column; justify-content: center; }
.wtp-calc { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; margin: 10px 0; }
.final-wtp { color: var(--primary-green); font-weight: 900; font-size: 1.4rem; }
.pct-label { font-size: 0.8rem; color: #555; font-weight: bold; }

.btn-save.full { width: 100%; margin-top: 10px; padding: 12px; }
input[type="range"] { width: 100%; accent-color: var(--primary-green); cursor: pointer; }
</style>