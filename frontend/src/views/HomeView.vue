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
  } catch (err) { console.error(err) } finally { loading.value = false }
}

const getPointY = (stock) => 40 - (Math.min(stock || 0, 5) * 8)
const toDate = (str) => new Date(str)

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
  const totalMs = Math.max(1, runout - start)

  // Linear scaling: Maps any date to the 0-300px timeline
  const getX = (d) => ((toDate(d) - start) / totalMs) * 300

  // 1. Build the historical sawtooth
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

  // 2. The "Now" Point Calculation
  // This point sits on the gradient between Last Event and Runout
  const lastEvent = item.history[item.history.length - 1]
  const lastX = getX(lastEvent.date)
  const lastY = getPointY(lastEvent.stock)
  
  // Calculate "Today" position on the X-axis
  const nowX = Math.min(300, getX(today))
  
  // Linear Interpolation for Y at "Today" to keep the gradient identical
  // Y = y1 + (x - x1) * ((y2 - y1) / (x2 - x1))
  const runoutX = 300
  const runoutY = 40 // Y coordinate for 0 stock
  const slope = (runoutY - lastY) / (runoutX - lastX)
  const nowY = lastY + (nowX - lastX) * slope

  const eventDots = item.history.map(p => ({
    x: getX(p.date),
    y: getPointY(p.stock),
    label: `${p.event_type?.includes("Finished") ? "Remaining" : p.event_type}: ${p.stock.toFixed(2)} units`,
    date: p.date
  }))

  return { 
    polyline: points.join(' '), 
    eventDots, 
    lastX, lastY,
    nowX, nowY 
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard">
    <header class="view-header">
      <h1>Inventory Forecast</h1>
      <p class="subtitle">Usage trends and restock predictions based on your eras.</p>
    </header>

    <div v-if="loading" class="status-msg">Calibrating forecast gradients...</div>

    <div v-else class="forecast-list">
      <div v-for="item in forecast" :key="item.role_id" class="forecast-row">
        
        <div class="col-info">
          <div class="product-line">
            <span class="brand">{{ item.brand }}</span>
            <span class="product-name">{{ item.product_name }}</span>
          </div>
          <div class="role-sub">{{ item.role_name }}</div>
        </div>

        <div class="col-graph">
          <svg v-if="getGraphData(item)" viewBox="0 0 300 40" preserveAspectRatio="none" class="sparkline">
            <line class="zero-baseline" x1="0" y1="40" x2="300" y2="40" />
            
            <polyline fill="none" stroke="#42b883" stroke-width="1.5" :points="getGraphData(item).polyline" />
            
            <line v-if="item.status === 'Calculated'" 
              stroke="#42b883" stroke-width="1.5"
              :x1="getGraphData(item).lastX" :y1="getGraphData(item).lastY" 
              :x2="getGraphData(item).nowX" :y2="getGraphData(item).nowY" />

            <line v-if="item.status === 'Calculated'" 
              class="projection-line" 
              :x1="getGraphData(item).nowX" :y1="getGraphData(item).nowY" 
              x2="300" y2="40" />

            <circle v-for="(dot, idx) in getGraphData(item).eventDots" :key="idx" 
              :cx="dot.x" :cy="dot.y" r="3.5" class="node"
              @mouseenter="activePopup = { id: item.role_id + '-' + idx, ...dot }"
              @mouseleave="activePopup = null" />

            <circle v-if="item.status === 'Calculated'" :cx="300" cy="40" r="4" class="node runout-node"
              @mouseenter="activePopup = { id: item.role_id + '-runout', label: 'Runout Expected', date: item.expected_restock, x: 300, y: 40 }"
              @mouseleave="activePopup = null" />
          </svg>

          <div v-if="activePopup?.id.startsWith(item.role_id)" class="graph-tooltip"
            :style="{ left: (activePopup.x / 300 * 100) + '%', top: (activePopup.y / 40 * 100) + '%' }">
            <div class="tt-date">{{ activePopup.date }}</div>
            <div class="tt-info">{{ activePopup.label }}</div>
          </div>
        </div>

        <div class="col-status">
          <template v-if="item.status === 'Calculated'">
            <div class="days-box" :class="getStatusClass(item.days_remaining)">
              {{ item.days_remaining }} <small>days left</small>
            </div>
            <div class="expected-date">Runout: {{ item.expected_restock }}</div>
          </template>
          <div v-else class="no-data">Insufficient Data</div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }
.forecast-row { display: grid; grid-template-columns: 320px 1fr 200px; align-items: center; padding: 30px 0; border-bottom: 1px solid #222; gap: 40px; position: relative; }
.brand { color: #42b883; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; margin-right: 10px; }
.product-name { color: #fff; font-size: 1.1rem; }
.role-sub { color: #555; font-size: 0.85rem; }
.col-graph { height: 40px; position: relative; }
.sparkline { width: 100%; height: 100%; overflow: visible; }
.zero-baseline { stroke: #ff4757; stroke-width: 1; opacity: 0.4; }
.projection-line { stroke: #42b883; stroke-width: 1.5; stroke-dasharray: 4; opacity: 0.6; }
.node { fill: #42b883; stroke: #111; stroke-width: 1.5; cursor: help; }
.runout-node { fill: #ff4757; }
.node:hover { r: 5; fill: #fff; }
.graph-tooltip { position: absolute; transform: translate(-50%, calc(-100% - 10px)); background: #1a1a1a; border: 1px solid #42b883; padding: 8px 12px; border-radius: 4px; color: #fff; font-size: 0.75rem; text-align: center; white-space: nowrap; z-index: 100; pointer-events: none; }
.tt-date { color: #888; font-family: monospace; margin-bottom: 2px; }
.tt-info { font-weight: bold; color: #42b883; }
.col-status { text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
.days-box { border: 1px solid; padding: 8px 16px; border-radius: 8px; font-weight: 800; font-size: 1.8rem; margin-bottom: 6px; min-width: 130px; text-align: center; line-height: 1; }
.days-box small { font-size: 0.7rem; text-transform: uppercase; display: block; margin-top: 4px; opacity: 0.8; }
.status-urgent { color: #ff4757; border-color: #ff4757; background: rgba(255, 71, 87, 0.05); }
.status-warning { color: #f1c40f; border-color: #f1c40f; background: rgba(241, 196, 15, 0.05); }
.status-stable { color: #42b883; border-color: #42b883; background: rgba(66, 184, 131, 0.05); }
.expected-date { color: #888; font-size: 0.85rem; letter-spacing: 0.2px; }
</style>