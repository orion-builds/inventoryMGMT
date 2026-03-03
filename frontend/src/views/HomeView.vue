<script setup>
import { ref, onMounted } from 'vue'

const forecast = ref([])
const loading = ref(true)
const activePopup = ref(null)

const fetchData = async () => {
  loading.value = true
  try {
    const response = await fetch('http://127.0.0.1:8000/dashboard/forecast')
    const data = await response.json()
    forecast.value = data.forecast || []
  } catch (err) { 
    console.error(err) 
  } finally { 
    loading.value = false 
  }
}

const getPointY = (stock) => 80 - (Math.min(stock || 0, 5) * 16)
const toDate = (str) => new Date(str)

/**
 * Robust margin calculation based on your tiered confidence levels.
 * High (3+ units): ±10% | Medium (2 units): ±25% | Low (1 unit): ±45%.
 */
const getMarginDays = (item) => {
  if (item.status !== 'Calculated') return 0
  const marginMap = { 'High': 0.10, 'Medium': 0.25, 'Low': 0.45 }
  const factor = marginMap[item.confidence] || 0
  return Math.round(item.days_remaining * factor)
}

const getStatusClass = (days) => {
  if (days <= 7) return 'status-urgent'
  if (days <= 14) return 'status-warning'
  return 'status-stable'
}

const getGraphData = (item) => {
  if (!item.history?.length) return null
  const start = toDate(item.history[0].date)
  const runout = toDate(item.expected_restock)
  const today = new Date()
  
  // Scales the X-axis based on the maximum confidence boundary.
  const maxBound = toDate(item.max_runout || item.expected_restock)
  const totalMs = Math.max(1, maxBound - start)
  const getX = (d) => ((toDate(d) - start) / totalMs) * 240

  let points = []
  let curStock = 0
  item.history.forEach((p) => {
    const x = getX(p.date)
    if (p.event_type?.includes("Restock")) {
      points.push(`${x},${getPointY(curStock)}`)
      curStock = p.stock
      points.push(`${x},${getPointY(curStock)}`)
    } else {
      curStock = p.stock
      points.push(`${x},${getPointY(curStock)}`)
    }
  })

  const lastEvent = item.history[item.history.length - 1]
  const lastX = getX(lastEvent.date), lastY = getPointY(lastEvent.stock)
  const nowX = Math.min(240, getX(today))
  const expectedX = getX(item.expected_restock)
  
  // Linear interpolation for a single consistent negative gradient.
  const slope = (expectedX - lastX) !== 0 ? (80 - lastY) / (expectedX - lastX) : 0
  const nowY = lastY + (nowX - lastX) * slope

  // Shaded polygon points representing the forecast confidence interval.
  const minX = getX(item.min_runout || item.expected_restock)
  const maxX = getX(item.max_runout || item.expected_restock)
  const fanPoints = `${nowX},${nowY} ${minX},80 ${maxX},80`

  const eventDots = item.history.map(p => ({
    x: getX(p.date), y: getPointY(p.stock),
    label: `${p.event_type?.includes("Finished") ? "Remaining" : p.event_type}: ${p.stock.toFixed(2)} units`,
    date: p.date
  }))

  return { polyline: points.join(' '), eventDots, lastX, lastY, nowX, nowY, fanPoints, expectedX }
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard">
    <header class="view-header">
      <h1>Inventory Forecast</h1>
      <p class="subtitle">Usage trends and restock predictions based on your eras.</p>
    </header>

    <div v-if="loading" class="status-msg">Polishing dashboard layout...</div>

    <div v-else class="forecast-grid">
      <div v-for="item in forecast" :key="item.role_id" class="forecast-card">
        
        <div class="card-header-main">
          <div class="product-info">
            <div class="brand">{{ item.brand }}</div>
            <div class="product-name">{{ item.product_name }}</div>
          </div>
          
          <div class="days-box" :class="getStatusClass(item.days_remaining)">
            <div class="baseline-row">
              <span class="main-days-num">{{ item.days_remaining }}</span>
              <div class="label-stack">
                <span class="margin-value">(&plusmn;{{ getMarginDays(item) }})</span>
                <span class="days-label">DAYS</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card-header-sub">
          <div class="role-name">
            {{ item.role_name }}
            <span v-if="item.confidence" class="conf-pill" :class="'pill-' + item.confidence.toLowerCase()">
              {{ item.confidence }}
            </span>
          </div>
          <div class="runout-info">{{ item.expected_restock }}</div>
        </div>

        <div class="card-graph-container">
          <svg v-if="getGraphData(item)" viewBox="0 0 240 80" preserveAspectRatio="none" class="sparkline">
            <line class="zero-baseline" x1="0" y1="80" x2="240" y2="80" />
            
            <polygon v-if="item.status === 'Calculated'" 
              class="confidence-fan" :points="getGraphData(item).fanPoints" />

            <polyline fill="none" stroke="#42b883" stroke-width="2.5" :points="getGraphData(item).polyline" />
            
            <line v-if="item.status === 'Calculated'" stroke="#42b883" stroke-width="2.5"
              :x1="getGraphData(item).lastX" :y1="getGraphData(item).lastY" 
              :x2="getGraphData(item).nowX" :y2="getGraphData(item).nowY" />

            <line v-if="item.status === 'Calculated'" class="projection-line" 
              :x1="getGraphData(item).nowX" :y1="getGraphData(item).nowY" 
              :x2="getGraphData(item).expectedX" y2="80" />

            <circle v-for="(dot, idx) in getGraphData(item).eventDots" :key="idx" 
              :cx="dot.x" :cy="dot.y" r="4.5" class="node"
              @mouseenter="activePopup = { id: item.role_id + '-' + idx, ...dot }"
              @mouseleave="activePopup = null" />

            <circle v-if="item.status === 'Calculated'" :cx="getGraphData(item).expectedX" cy="80" r="5" class="node runout-node"
              @mouseenter="activePopup = { id: item.role_id + '-runout', label: 'Runout Expected', date: item.expected_restock, x: getGraphData(item).expectedX, y: 80 }"
              @mouseleave="activePopup = null" />
          </svg>

          <div v-if="activePopup?.id.startsWith(item.role_id)" class="graph-tooltip"
            :style="{ left: (activePopup.x / 240 * 100) + '%', top: (activePopup.y / 80 * 100) + '%' }">
            <div class="tt-date">{{ activePopup.date }}</div>
            <div class="tt-info">{{ activePopup.label }}</div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1400px; margin: 0 auto; padding: 40px; }
.forecast-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.forecast-card { background: #121212; border: 1px solid #1e1e1e; border-radius: 16px; padding: 24px; display: flex; flex-direction: column; position: relative; }

/* Product Name Wrap Fix. */
.card-header-main { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 12px; }
.product-info { flex: 1; display: flex; flex-direction: column; }
.brand { color: #42b883; font-weight: 700; text-transform: uppercase; font-size: 0.7rem; margin-bottom: 4px; }
.product-name { color: #fff; font-weight: 700; font-size: 1.1rem; line-height: 1.3; white-space: normal; overflow: visible; }

/* The Alignment Logic. */
.days-box { flex-shrink: 0; }
.baseline-row { display: flex; align-items: baseline; gap: 8px; position: relative; }
.main-days-num { font-size: 2.8rem; font-weight: 900; line-height: 1; margin: 0; }
.label-stack { display: flex; flex-direction: column; position: relative; }
.days-label { font-size: 0.75rem; font-weight: 800; line-height: 1; opacity: 0.9; }

/* Margin positioned absolutely to not affect baseline. */
.margin-value { position: absolute; bottom: 100%; left: 0; font-size: 0.85rem; font-weight: 700; opacity: 0.5; white-space: nowrap; padding-bottom: 2px; }

.card-header-sub { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.role-name { color: #555; font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; }
.conf-pill { font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; margin-left: 8px; text-transform: uppercase; border: 1px solid transparent; }
.pill-high { color: #42b883; border-color: rgba(66, 184, 131, 0.3); background: rgba(66, 184, 131, 0.05); }
.pill-medium { color: #f1c40f; border-color: rgba(241, 196, 15, 0.3); background: rgba(241, 196, 15, 0.05); }
.pill-low { color: #ff4757; border-color: rgba(255, 71, 87, 0.3); background: rgba(255, 71, 87, 0.05); }

.runout-info { color: #777; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
.status-urgent { color: #ff4757; }
.status-warning { color: #f1c40f; }
.status-stable { color: #42b883; }

.card-graph-container { height: 80px; position: relative; margin-top: auto; }
.sparkline { width: 100%; height: 80px; overflow: visible; }
.confidence-fan { fill: #42b883; fill-opacity: 0.07; stroke: none; }
.projection-line { stroke: #42b883; stroke-width: 2; stroke-dasharray: 6; opacity: 0.4; }
.zero-baseline { stroke: #ff4757; stroke-width: 1; opacity: 0.2; }
.node { fill: #42b883; stroke: #000; cursor: pointer; transition: r 0.2s; }
.runout-node { fill: #ff4757; }
.node:hover { r: 6; fill: #fff; }

.graph-tooltip { position: absolute; transform: translate(-50%, calc(-100% - 12px)); background: #1a1a1a; border: 1px solid #42b883; padding: 8px 12px; border-radius: 6px; color: #fff; font-size: 0.7rem; text-align: center; white-space: nowrap; z-index: 100; box-shadow: 0 8px 20px rgba(0,0,0,0.5); pointer-events: none; }
.tt-date { color: #777; font-size: 0.65rem; margin-bottom: 2px; }
.tt-info { font-weight: 700; color: #42b883; }
</style>