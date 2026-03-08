<script setup>
import { ref, computed, onMounted } from 'vue'
import { authorizedFetch } from '../api'


// --- 1. EMA Simulator State ---
const emaOldPrice = ref(20.00)
const emaNewPrice = ref(15.00)
const emaAlpha = ref(0.3)

const emaSimulated = computed(() => {
  return (emaNewPrice.value * emaAlpha.value) + (emaOldPrice.value * (1 - emaAlpha.value))
})

// --- 2. WTP Simulator State ---
const wtpBasePrice = ref(50.00)
const wtpBuffer = ref(7)
const wtpCurrentDays = ref(45)
const wtpPenalty = ref(0.015) // 1.5% daily penalty

const wtpExcessDays = computed(() => Math.max(0, wtpCurrentDays.value - wtpBuffer.value))
const wtpSimulated = computed(() => {
  if (wtpExcessDays.value === 0) return wtpBasePrice.value
  return wtpBasePrice.value * Math.pow((1 - wtpPenalty.value), wtpExcessDays.value)
})

// --- NEW: Fetch actual user settings [cite: 2026-03-05, 2026-03-08] ---
const loadUserSettings = async () => {
  try {
    const response = await authorizedFetch('/settings/')
    if (response.ok) {
      const settings = await response.json()
      // If the user has a custom alpha in their DB, use it here [cite: 2026-03-08]
      if (settings.global_ema_alpha) {
        emaAlpha.value = parseFloat(settings.global_ema_alpha)
      }
      if (settings.global_holding_penalty) {
        wtpPenalty.value = parseFloat(settings.global_holding_penalty)
      }
    }
  } catch (err) {
    console.error("Could not sync simulator with user settings:", err)
  }
}

// --- 3. Margin of Error Simulator State ---
const marginDaysRemaining = ref(100)
const marginSampleSize = ref(5)
const marginCV = ref(0.20) // 20% volatility

const marginSimulated = computed(() => {
  const sampleStrength = Math.sqrt(marginSampleSize.value)
  const marginFactor = marginCV.value / sampleStrength
  const finalFactor = Math.max(0.02, marginFactor) // The 2% floor rule
  
  const days = Math.round(marginDaysRemaining.value * finalFactor)
  
  // Calculate Confidence Tier
  let conf = "Low"
  let color = "status-urgent"
  if (marginFactor < 0.05 && marginSampleSize.value >= 4) {
    conf = "High"; color = "status-stable"
  } else if (marginFactor < 0.15) {
    conf = "Medium"; color = "status-warning"
  }
  
  return { days, conf, color }
})

onMounted(loadUserSettings)

</script>

<template>
  <div class="help-container">
    <header class="view-header">
      <div class="title-stack">
        <h1>System Mechanics</h1>
        <p class="subtitle">Interactive documentation for the math powering your inventory engine.</p>
      </div>
    </header>

    <div class="mechanics-grid">
      
      <section class="mechanic-card">
        <div class="card-header">
          <h2>1. Price Smoothing (EMA)</h2>
          <span class="badge">Baseline Price</span>
        </div>
        <p class="explanation">
          To prevent temporary sales from permanently ruining your baseline price, the system uses an <strong>Exponential Moving Average (EMA)</strong>. 
          The <code>Alpha (α)</code> determines how aggressively the system "learns" from new prices. An Alpha of 1.0 means it forgets the past instantly; 0.0 means it never learns.
        </p>
        
        <div class="simulator-box">
          <div class="sim-controls">
            <div class="input-group">
              <label>Old Baseline: S${{ emaOldPrice.toFixed(2) }}</label>
              <input v-model.number="emaOldPrice" type="range" min="5" max="100" step="1" />
            </div>
            <div class="input-group">
              <label>New Deal Price: S${{ emaNewPrice.toFixed(2) }}</label>
              <input v-model.number="emaNewPrice" type="range" min="5" max="100" step="1" />
            </div>
            <div class="input-group">
              <label>Alpha (α): {{ emaAlpha.toFixed(2) }}</label>
              <input v-model.number="emaAlpha" type="range" min="0.01" max="1.0" step="0.01" />
            </div>
          </div>
          
          <div class="sim-result">
            <span class="tiny-label">NEW CALCULATED BASELINE</span>
            <div class="math-formula">
              (S${{ emaNewPrice.toFixed(2) }} &times; {{ emaAlpha.toFixed(2) }}) + (S${{ emaOldPrice.toFixed(2) }} &times; {{ (1 - emaAlpha).toFixed(2) }})
            </div>
            <div class="final-val">S${{ emaSimulated.toFixed(2) }}</div>
          </div>
        </div>
      </section>

      <section class="mechanic-card">
        <div class="card-header">
          <h2>2. Willingness to Pay (WTP)</h2>
          <span class="badge">Economic Model</span>
        </div>
        <p class="explanation">
          WTP calculates the maximum price you should pay today to justify hoarding an item. It only penalizes you for <strong>Excess Days</strong> (days beyond your Target Buffer). 
          The higher your <code>Holding Penalty (H)</code>, the more aggressively the price must drop to justify an early purchase.
        </p>
        
        <div class="simulator-box">
          <div class="sim-controls">
            <div class="input-group">
              <label>Baseline Price: S${{ wtpBasePrice.toFixed(2) }}</label>
              <input v-model.number="wtpBasePrice" type="range" min="10" max="200" step="1" />
            </div>
            <div class="split-group">
              <div class="input-group">
                <label>Current Stock: {{ wtpCurrentDays }}d</label>
                <input v-model.number="wtpCurrentDays" type="range" min="0" max="200" />
              </div>
              <div class="input-group">
                <label>Target Buffer: {{ wtpBuffer }}d</label>
                <input v-model.number="wtpBuffer" type="range" min="0" max="60" />
              </div>
            </div>
            <div class="input-group">
              <label>Daily Penalty (H): {{ (wtpPenalty * 100).toFixed(2) }}%</label>
              <input v-model.number="wtpPenalty" type="range" min="0.001" max="0.05" step="0.001" />
            </div>
          </div>
          
          <div class="sim-result">
            <span class="tiny-label">TARGET DEAL PRICE</span>
            <div class="math-formula">
              Excess Days = {{ wtpCurrentDays }} - {{ wtpBuffer }} = {{ wtpExcessDays }}<br>
              S${{ wtpBasePrice.toFixed(2) }} &times; {{ (1 - wtpPenalty).toFixed(3) }}<sup>{{ wtpExcessDays }}</sup>
            </div>
            <div class="final-val">
              S${{ wtpSimulated.toFixed(2) }} 
              <span class="pct-sub">({{ Math.round((wtpSimulated / wtpBasePrice) * 100) }}%)</span>
            </div>
          </div>
        </div>
      </section>

      <section class="mechanic-card">
        <div class="card-header">
          <h2>3. Margin of Error (&plusmn; Days)</h2>
          <span class="badge">Forecasting</span>
        </div>
        <p class="explanation">
          The Dashboard calculates a <code>(&plusmn;)</code> margin based on your consumption stability. It uses the <strong>Coefficient of Variation (CV)</strong> (how erratic your usage is) divided by the square root of your <strong>Sample Size</strong> (how many times you've finished the product). 
        </p>
        
        <div class="simulator-box">
          <div class="sim-controls">
            <div class="input-group">
              <label>Estimated Days Remaining: {{ marginDaysRemaining }}</label>
              <input v-model.number="marginDaysRemaining" type="range" min="10" max="500" step="10" />
            </div>
            <div class="input-group">
              <label>Sample Size (Depletions): {{ marginSampleSize }}</label>
              <input v-model.number="marginSampleSize" type="range" min="1" max="20" step="1" />
            </div>
            <div class="input-group">
              <label>Usage Volatility (CV): {{ Math.round(marginCV * 100) }}%</label>
              <input v-model.number="marginCV" type="range" min="0.0" max="1.0" step="0.05" />
            </div>
          </div>
          
          <div class="sim-result">
            <span class="tiny-label">CONFIDENCE: <span :class="marginSimulated.color" class="conf-badge">{{ marginSimulated.conf }}</span></span>
            <div class="math-formula">
              Margin = {{ marginCV.toFixed(2) }} &divide; &radic;{{ marginSampleSize }} = {{ (marginCV / Math.sqrt(marginSampleSize)).toFixed(3) }}<br>
              &plusmn; Days = {{ marginDaysRemaining }} &times; {{ Math.max(0.02, marginCV / Math.sqrt(marginSampleSize)).toFixed(3) }}
            </div>
            <div class="final-val" :class="marginSimulated.color">
              &plusmn; {{ marginSimulated.days }} Days
            </div>
          </div>
        </div>
      </section>
      
      <section class="mechanic-card reference-card">
        <div class="card-header">
          <h2>4. Event Type Reference</h2>
        </div>
        <div class="ref-grid">
          <div class="ref-item">
            <span class="badge restocked">RESTOCK (+)</span>
            <p><strong>Adds to Stock.</strong> Used for calculating WTP, Baseline Prices, and the Machine Learning penalty loop. Requires a cost and quantity.</p>
          </div>
          <div class="ref-item">
            <span class="badge finished">FINISHED (-)</span>
            <p><strong>Deducts from Stock.</strong> The core metric for determining how fast you consume a product. Ignored by pricing algorithms.</p>
          </div>
          <div class="ref-item">
            <span class="badge init">INIT (LEGACY)</span>
            <p><strong>Sets an Anchor.</strong> Used when you start tracking a half-empty bottle. The system won't start counting consumption days until the <em>next</em> 'Finished' event.</p>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<style scoped>
.help-container { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { margin-bottom: 2rem; border-bottom: 1px solid #333; padding-bottom: 20px; }
.title-stack h1 { margin: 0; }
.subtitle { color: #888; font-size: 0.9rem; margin-top: 8px; }

.mechanics-grid { display: grid; grid-template-columns: 1fr; gap: 32px; }

.mechanic-card { background: #121212; border: 1px solid #222; border-radius: 16px; padding: 32px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-header h2 { margin: 0; font-size: 1.4rem; color: #fff; }
.badge { background: #1a1a1a; border: 1px solid #444; color: #aaa; padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }

.explanation { font-size: 0.9rem; color: #888; line-height: 1.6; margin-bottom: 24px; max-width: 900px; }
code { background: #1a1a1a; padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; color: #42b883; font-size: 0.85em; }

/* Simulator Layout */
.simulator-box { display: grid; grid-template-columns: 1.5fr 1fr; gap: 40px; background: #1a1a1a; padding: 30px; border-radius: 12px; border-left: 4px solid #42b883; box-shadow: inset 0 2px 10px rgba(0,0,0,0.2); }
.sim-controls { display: flex; flex-direction: column; gap: 20px; }
.split-group { display: flex; gap: 20px; }
.input-group { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.input-group label { font-size: 0.75rem; color: #aaa; font-weight: 700; text-transform: uppercase; }

/* Custom Sliders */
input[type="range"] { width: 100%; accent-color: #42b883; cursor: pointer; height: 6px; background: #333; border-radius: 3px; appearance: none; outline: none; }
input[type="range"]::-webkit-slider-thumb { appearance: none; width: 16px; height: 16px; background: #42b883; border-radius: 50%; cursor: pointer; }

/* Results Area */
.sim-result { display: flex; flex-direction: column; justify-content: center; border-left: 1px solid #333; padding-left: 40px; }
.tiny-label { font-size: 0.65rem; color: #666; font-weight: 800; letter-spacing: 1px; display: block; margin-bottom: 12px; }
.math-formula { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #777; margin-bottom: 16px; line-height: 1.5; background: #121212; padding: 10px 14px; border-radius: 6px; border: 1px solid #222; }
.final-val { font-size: 2.5rem; font-weight: 900; color: #fff; font-family: 'JetBrains Mono', monospace; line-height: 1; }
.pct-sub { font-size: 1.2rem; color: #42b883; opacity: 0.8; }

/* Status Colors */
.status-urgent { color: #ff4757 !important; }
.status-warning { color: #f1c40f !important; }
.status-stable { color: #42b883 !important; }
.conf-badge { padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.05); }

/* Reference Cards */
.reference-card { border-left: 4px solid #333; }
.ref-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.ref-item { background: #1a1a1a; padding: 20px; border-radius: 8px; }
.ref-item p { font-size: 0.85rem; color: #888; margin-top: 12px; line-height: 1.5; }
.badge.restocked { color: #42b883; background: rgba(66, 184, 131, 0.1); }
.badge.finished { color: #ff4757; background: rgba(255, 71, 87, 0.1); }
.badge.init { color: #3498db; background: rgba(52, 152, 219, 0.1); }

@media (max-width: 900px) {
  .simulator-box { grid-template-columns: 1fr; }
  .sim-result { border-left: none; border-top: 1px solid #333; padding-left: 0; padding-top: 24px; }
  .ref-grid { grid-template-columns: 1fr; }
}
</style>