<script setup>
import { ref, onMounted, computed } from 'vue'
import { authorizedFetch } from '../api'
import katex from 'katex'
import 'katex/dist/katex.min.css'

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
    const res = await authorizedFetch('/settings/') // Relative path with token [cite: 2026-03-05]
    const data = await res.json()
    if (data.global_ema_alpha) globalAlpha.value = parseFloat(data.global_ema_alpha)
    if (data.default_holding_penalty) defaultH.value = parseFloat(data.default_holding_penalty)
  } catch (err) { 
    console.error("Failed to load user settings:", err) 
  }
}

const saveSettings = async (key, value) => {
  saving.value = true
  try {
    // Backend will update ONLY the logged-in user's database [cite: 2026-03-05, 2026-03-08]
    await authorizedFetch(`/settings/${key}?value=${value}`, { method: 'PATCH' })
    message.value = "Settings updated!"
    setTimeout(() => message.value = '', 3000)
  } finally { 
    saving.value = false 
  }
}

const exportData = async () => {
  try {
    const res = await authorizedFetch('/export-data') // Export ONLY this user's data [cite: 2026-03-05]
    const data = await res.json()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `inventory_backup_${new Date().toISOString().split('T')[0]}.json`
    a.click()
  } catch (err) { 
    alert("Export failed") 
  }
}

const handleImport = async (event) => {
  const file = event.target.files[0]
  if (!file || !confirm("⚠️ WARNING: This will permanently WIPE YOUR CURRENT DATABASE and replace it with the backup file. Do you wish to proceed?")) return
  
  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const data = JSON.parse(e.target.result)
      const res = await authorizedFetch('/import-data', {
        method: 'POST',
        body: JSON.stringify(data) // Headers are handled by api.js [cite: 2026-03-08]
      })
      if (res.ok) alert("Import Successful! Your personal database has been updated.")
      window.location.reload()
    } catch (err) { 
      alert("Import failed: Check file format") 
    }
  }
  reader.readAsText(file)
}

const rawPrices = [12, 15, 11, 18, 14, 13, 19, 12]

const simulatedEMA = (index) => {
  let lastEma = rawPrices[0]
  for (let i = 0; i <= index; i++) {
    lastEma = (rawPrices[i] * globalAlpha.value) + (lastEma * (1 - globalAlpha.value))
  }
  return lastEma
}

const mathFormula = computed(() => {
  const alpha = globalAlpha.value.toFixed(2)
  const prev = (1 - globalAlpha.value).toFixed(2)
  // Generating the LaTeX string [cite: 2026-03-05]
  return katex.renderToString(
    `P_{ema} = (P_{new} \\cdot ${alpha}) + (P_{prev} \\cdot ${prev})`,
    { throwOnError: false, displayMode: true }
  )
})

const wtpFormula = computed(() => {
  const base = simBasePrice.value
  const rate = (1 - defaultH.value).toFixed(3)
  const days = simExcessDays.value
  const result = simWTP.value.toFixed(2)

  // LaTeX format: S$Base \times Rate^{Days} = S$Result [cite: 2026-03-05]
  return katex.renderToString(
    `\\$${base} \\times ${rate}^{${days}} = \\$${result}`,
    { throwOnError: false, displayMode: true }
  )
})
// --- Security State ---
const currentPassword = ref('')
const newPassword = ref('')
const repeatPassword = ref('')
const passwordMessage = ref('')

// --- Password Visibility State ---
const showPasswords = ref(false)

// Basic validation [cite: 2026-03-08]
const isPasswordFormValid = computed(() => {
  return currentPassword.value.length > 0 && 
         newPassword.value.length >= 4 && 
         newPassword.value === repeatPassword.value
})

const handleChangePassword = async () => {
  if (newPassword.value !== repeatPassword.value) {
    passwordMessage.value = "Error: New passwords do not match."
    return
  }

  try {
    const res = await authorizedFetch('/auth/change-password', {
      method: 'PATCH',
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value
      })
    })

    if (res.ok) {
      passwordMessage.value = "✅ Success: Password updated!"
      // Reset fields [cite: 2026-03-08]
      currentPassword.value = ''
      newPassword.value = ''
      repeatPassword.value = ''
      setTimeout(() => passwordMessage.value = '', 5000)
    } else {
      const errorData = await res.json()
      passwordMessage.value = `❌ ${errorData.detail || 'Update failed'}`
    }
  } catch (err) {
    passwordMessage.value = "❌ Server connection error."
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="settings-container">
    <h1>System Settings</h1>
    <h2>Data Management</h2>
    <section class="settings-card data-management">
      <h3>Backup tools</h3>
      <p class="explanation">Backup your learned habits and product history to a local JSON file.</p>
      <div class="data-actions">
        <button @click="exportData" class="btn-subtle">Download Backup (.json)</button>
        <div class="tooltip-wrapper">
          <label class="btn-subtle import-label">
            Upload Backup
            <input type="file" @change="handleImport" accept=".json" hidden />
          </label>
          <span class="tooltip-text">⚠️ Warning: This will wipe the current database!</span>
        </div>
      </div>
    </section>
    <h2>Security</h2>
    <section class="settings-card">
      <h3>Change Password</h3>
      <p class="explanation">Update your login credentials. We recommend at least 8 characters.</p>
      
      <div class="password-form">
        <div class="form-row">
          <div class="input-group">
            <label class="tiny-label">Current Password</label>
            <input :type="showPasswords ? 'text' : 'password'" v-model="currentPassword" class="settings-input" placeholder="••••••••" />
          </div>
        </div>

        <div class="form-row">
          <div class="input-group">
            <label class="tiny-label">New Password</label>
            <input :type="showPasswords ? 'text' : 'password'" v-model="newPassword" class="settings-input" placeholder="••••••••" />
          </div>
          <div class="input-group">
            <label class="tiny-label">Repeat New Password</label>
            <input :type="showPasswords ? 'text' : 'password'" v-model="repeatPassword" class="settings-input" placeholder="••••••••" />
          </div>
        </div>

        <p v-if="passwordMessage" :class="['status-msg', passwordMessage.includes('Success') ? 'text-success' : 'text-error']" style="margin-bottom: -0.5rem;">
          {{ passwordMessage }}
        </p>

        <div class="action-footer-between">
          <label class="show-pass-label">
            <input type="checkbox" v-model="showPasswords" />
            <span>Show passwords</span>
          </label>

          <button @click="handleChangePassword" class="btn-apply-block" :disabled="!isPasswordFormValid">
            Update Password
          </button>
        </div>
      </div>
    </section>
    <h2>System Variables</h2>
    <section class="settings-card">
      <h3>Price Smoothing (EMA Alpha)</h3>

      <div class="ema-viz-container">
        <div class="ema-graph-area">
          <span class="tiny-label">Smoothing Simulation</span>
          <div class="visual-graph">
            <div v-for="(p, i) in [12, 15, 11, 18, 14, 13, 19, 12]" :key="i" class="data-point">
              <div class="bar-raw" :style="{ height: (p * 5) + 'px' }"></div>
              <div class="bar-ema" :style="{ height: (simulatedEMA(i) * 5) + 'px' }"></div>
            </div>
          </div>
          <div class="graph-legend">
            <div class="legend-item"><span class="dot raw"></span> Raw Price</div>
            <div class="legend-item"><span class="dot ema"></span> EMA Baseline</div>
          </div>
        </div>

        <div class="ema-formula-area">
          <span class="tiny-label">Live Formula</span>
          <div class="dynamic-formula" v-html="mathFormula"></div>
          <p class="formula-caption">
            Weighted at <strong>{{ (globalAlpha * 100).toFixed(0) }}%</strong> on the latest deal.
          </p>
        </div>
      </div>

      <div class="ema-control-row">
        <input v-model.number="globalAlpha" type="range" min="0.01" max="1.0" step="0.01" class="ema-slider-main" />
        <div class="ema-value-box">
          <span class="ema-num">{{ globalAlpha.toFixed(2) }}</span>
        </div>
        <div class="ema-action-stack">
          <button @click="globalAlpha = 0.3" class="btn-reset-link">Reset to Default</button>
          <button @click="saveSettings('global_ema_alpha', globalAlpha)" class="btn-apply-block">Apply Changes</button>
        </div>
      </div>
    </section>

    <section class="settings-card penalty-card">
      <h3>Inventory Holding Penalty ($H$)</h3>
      <p class="explanation">
        Determines how much you discount your Willingness To Pay for every day you are "stocked up" beyond your buffer.
      </p>
      
      <div class="ema-viz-container">
        <div class="ema-graph-area">
          <span class="tiny-label">Penalty Simulation</span>
          
          <div class="sim-controls-stacked">
            <div class="control-group">
              <label>Daily Penalty: <strong>{{ (defaultH * 100).toFixed(1) }}%</strong></label>
              <input v-model.number="defaultH" type="range" min="0.001" max="0.05" step="0.001" class="ema-slider-main" />
            </div>
            
            <div class="control-group">
              <label>Excess Days: <strong>{{ simExcessDays }} days</strong></label>
              <input v-model.number="simExcessDays" type="range" min="0" max="120" class="ema-slider-main" />
            </div>
          </div>
        </div>

        <div class="ema-formula-area">
          <span class="tiny-label">Simulated WTP</span>
          <div class="dynamic-formula" v-html="wtpFormula"></div>
          <p class="formula-caption">
            Outcome: <b>{{ Math.round((simWTP / simBasePrice) * 100) }}%</b> of market price.
          </p>
        </div>
      </div>

      <div class="action-footer-right">
        <button @click="defaultH = 0.015" class="btn-reset-link">Reset to Default</button>
        <button @click="saveSettings('default_holding_penalty', defaultH)" class="btn-apply-block">Update Global Penalty</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.settings-container { max-width: 800px; margin: 0 auto; padding: 40px; }
.settings-card { background: #1a1a1a; padding: 24px; padding-top: 12px; border-radius: 12px; border-left: 4px solid var(--primary-green); margin-bottom: 24px; }
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

.btn-save.full { width: 100%; margin-top: 10px; padding: 12px; }
input[type="range"] { width: 100%; accent-color: var(--primary-green); cursor: pointer; }
.data-actions { display: flex; gap: 12px; }
.btn-subtle { 
  flex: 1; 
  background: transparent; 
  border: 1px solid #444; 
  color: #888; 
  padding: 12px; 
  border-radius: 8px; 
  font-size: 0.85rem; /* Explicitly set same font size */
  font-weight: 700; 
  cursor: pointer; 
  text-align: center;
  transition: 0.2s;
  display: flex; /* Helps with vertical centering in the label */
  align-items: center;
  justify-content: center;
}
.btn-subtle:hover { border-color: #666; color: #eee; background: #222; }
.import-label { margin: 0; font-family: inherit; }
h2 {
  margin: 40px 0 20px;
  font-size: 1.2rem;
  color: var(--primary-green);
  text-transform: uppercase;
  letter-spacing: 1px;
}
/* Tooltip Container */
.tooltip-wrapper {
  position: relative;
  flex: 1; /* Match the button sizing */
  display: flex;
}

/* Tooltip Styling */
.tooltip-text {
  visibility: hidden;
  width: 200px;
  background-color: #721c24; /* Danger red */
  color: #f8d7da;
  text-align: center;
  border-radius: 6px;
  padding: 8px;
  font-size: 0.75rem;
  font-weight: 800;
  border: 1px solid #f5c6cb;
  
  /* Positioning */
  position: absolute;
  z-index: 10;
  bottom: 125%; /* Show above the button */
  left: 50%;
  transform: translateX(-50%);
  
  /* Smooth Fade */
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none; /* Don't block clicks */
}

/* Tooltip Arrow */
.tooltip-text::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: #721c24 transparent transparent transparent;
}

/* Hover Trigger */
.tooltip-wrapper:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

/* Ensure the label still fills the container */
.import-label {
  width: 100%;
}

.horizontal-layout {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 10px;
}

/* 1. The Slider - Takes up the left side */
.ema-slider {
  flex: 1; /* Stretches to fill available space until it hits the stack */
  max-width: 300px; /* Limits the length on desktop */
}

/* 2. The Stack - Value on top, Button on bottom [cite: 2026-03-05] */
.control-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  gap: 4px;
}

.val-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 800;
  color: var(--primary-green);
}

.btn-apply-mini {
  background: transparent;
  border: 1px solid var(--primary-green);
  color: var(--primary-green);
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  cursor: pointer;
  transition: 0.2s;
}

.btn-apply-mini:hover {
  background: var(--primary-green);
  color: #000;
}
.ema-control-row {
  display: flex;
  align-items: center;
  gap: 32px; /* Wide gap for a clean look */
  margin-top: 20px;
  width: 100%;
}

/* Slider stretches to fill */
.ema-slider-main {
  flex: 1; 
  accent-color: var(--primary-green);
}

/* Value box centered in the middle */
.ema-value-box {
  min-width: 60px;
  text-align: center;
}

.ema-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--primary-green);
}

/* Vertical stack for the buttons [cite: 2026-03-05] */
.ema-action-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 160px;
}

.btn-apply-block {
  background: var(--primary-green);
  color: #000;
  border: none;
  padding: 10px;
  border-radius: 6px;
  font-weight: 800;
  font-size: 0.75rem;
  text-transform: uppercase;
  cursor: pointer;
  transition: 0.2s;
}

.btn-apply-block:hover {
  filter: brightness(1.1);
}

.action-footer-right {
  display: flex;
  justify-content: flex-end;
  align-items: center; /* Vertically centers the text link with the button [cite: 2026-03-05] */
  gap: 20px; /* Increased space for better tap targets on mobile [cite: 2026-03-05] */
  margin-top: 32px; /* Extra separation from the simulator box [cite: 2026-03-05] */
  width: 100%;
}

.btn-reset-link {
  background: transparent;
  border: none;
  color: #666;
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 700;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.btn-reset-link:hover {
  color: #aaa;
}

/* Visualization Layout [cite: 2026-03-05] */
.ema-viz-container {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 40px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #222;
}

.visual-graph {
  height: 100px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding-bottom: 5px;
  border-bottom: 1px solid #333;
}

.data-point { display: flex; align-items: flex-end; gap: 2px; }
.bar-raw { width: 8px; background: #333; border-radius: 2px; }
.bar-ema { 
  width: 8px; 
  background: var(--primary-green); 
  border-radius: 2px; 
  transition: height 0.1s ease-out; /* Makes the slider feel snappy */
}

.tiny-label { font-size: 0.65rem; color: #555; text-transform: uppercase; font-weight: 800; display: block; margin-bottom: 10px; }

/* Dynamic Formula Styling [cite: 2026-03-05] */
.ema-formula-area {
  background: #111;
  padding: 20px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.dynamic-formula {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.2rem;
  color: var(--primary-green);
  margin: 10px 0;
}

.formula-caption {
  font-size: 0.75rem;
  color: #666;
  font-style: italic;
}

/* Legend Styling [cite: 2026-03-05] */
.graph-legend {
  display: flex;
  gap: 20px;
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.65rem;
  color: #666;
  font-weight: 700;
  text-transform: uppercase;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.dot.raw { background: #333; }
.dot.ema { background: var(--primary-green); }

/* Dynamic Formula Styling [cite: 2026-03-05] */
.dynamic-formula {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: var(--primary-green);
  margin: 10px 0;
  white-space: nowrap; /* Prevents weird line breaks */
}

.dynamic-formula sub {
  font-size: 0.6rem;
  vertical-align: sub;
  opacity: 0.8;
}

/* Target the generated KaTeX elements [cite: 2026-03-05] */
.dynamic-formula :deep(.katex) {
  font-size: 1.1rem;
  color: var(--primary-green);
}

.ema-formula-area {
  background: #111;
  padding: 20px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 120px; /* Prevents jumping when numbers change [cite: 2026-03-05] */
}

/* Ensure consistent math styling across the entire settings page [cite: 2026-03-05] */
.wtp-math :deep(.katex) {
  font-size: 1.2rem; /* Slightly larger for the final result [cite: 2026-03-05] */
  color: var(--primary-green);
}

/* Adjust the simulation box to handle the new formula height [cite: 2026-03-05] */
.sim-result {
  border-left: 1px solid #333;
  padding-left: 30px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 140px; 
}

/* Stack the sliders vertically within the left area [cite: 2026-03-05] */
.sim-controls-stacked {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 10px 0;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-group label {
  font-size: 0.7rem;
  color: #666;
  text-transform: uppercase;
  font-weight: 800;
}

.control-group label strong {
  color: var(--primary-green);
  font-family: 'JetBrains Mono', monospace;
}

/* Ensure the WTP KaTeX formula is centered and bold [cite: 2026-03-05] */
.wtp-math :deep(.katex) {
  font-size: 1.2rem;
  color: var(--primary-green);
  font-weight: 900;
}

/* Container for the specific password form logic */
.password-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 1rem;
  max-width: 100%; /* Keeps the form from stretching too wide [cite: 2026-03-08] */
}

/* Rows for inputs to sit side-by-side or stacked [cite: 2026-03-08] */
.form-row {
  display: flex;
  gap: 1.2rem;
  flex-wrap: wrap; /* Allows stacking on smaller mobile screens [cite: 2026-03-08] */
}

/* Individual input containers */
.input-group {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Standardized settings inputs [cite: 2026-03-08] */
.settings-input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 0.8rem;
  color: #fff;
  font-family: inherit;
  transition: border-color 0.2s;
}

.settings-input:focus {
  outline: none;
  border-color: var(--accent-color, #42b883); /* Vue Green or your accent [cite: 2026-03-08] */
  background: rgba(255, 255, 255, 0.08);
}

/* Action area at the bottom of the card [cite: 2026-03-08] */
.action-footer-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* Status message colors [cite: 2026-03-08] */
.text-success { color: #4ade80; font-size: 0.9rem; font-weight: 500; }
.text-error { color: #f87171; font-size: 0.9rem; font-weight: 500; }

/* Disabled state for the update button [cite: 2026-03-08] */
.btn-apply-block:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  filter: grayscale(1);
}

/* Layout for the checkbox label [cite: 2026-03-08] */
.show-pass-label {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
  user-select: none;
  transition: color 0.2s;
}

.show-pass-label:hover {
  color: rgba(255, 255, 255, 0.9);
}

/* Customizing the checkbox appearance slightly [cite: 2026-03-08] */
.show-pass-label input[type="checkbox"] {
  cursor: pointer;
  accent-color: var(--accent-color, #42b883); /* Matches your UI theme */
  width: 16px;
  height: 16px;
}

.status-msg {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
}

</style>