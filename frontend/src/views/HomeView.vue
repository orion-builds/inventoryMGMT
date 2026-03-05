<script setup>
import { ref, onMounted, computed } from 'vue'

const forecast = ref([])
const summary = ref({ daily: 0, monthly: 0, yearly: 0 }) 
const timeframe = ref('daily') 
const searchQuery = ref('') 
const loading = ref(true)
const activePopup = ref(null)
const isExpanded = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const response = await fetch('http://127.0.0.1:8000/dashboard/forecast')
    const data = await response.json()
    forecast.value = data.forecast || []
    summary.value = data.summary || { daily: 0, monthly: 0, yearly: 0 } 
  } catch (err) { 
    console.error(err) 
  } finally { 
    loading.value = false 
  }
}

// 1. Filter by the search query
const filteredForecast = computed(() => {
  if (!searchQuery.value) return forecast.value
  const q = searchQuery.value.toLowerCase()
  return forecast.value.filter(item => 
    item.brand.toLowerCase().includes(q) || 
    item.product_name.toLowerCase().includes(q) ||
    item.role_name.toLowerCase().includes(q)
  )
})

// 2. Partition based on urgency (target_buffer_days)
const visibleCards = computed(() => {
  const data = filteredForecast.value
  if (!data.length) return []
  const urgentCount = data.filter(item => item.days_remaining <= (item.target_buffer_days || 7)).length
  const threshold = Math.max(3, urgentCount)
  return data.slice(0, threshold)
})

const hiddenCards = computed(() => {
  const data = filteredForecast.value
  if (!data.length) return []
  const urgentCount = data.filter(item => item.days_remaining <= (item.target_buffer_days || 7)).length
  const threshold = Math.max(3, urgentCount)
  return data.slice(threshold)
})

const currentTotalDisplay = computed(() => {
  return summary.value[timeframe.value]?.toFixed(2) || '0.00'
})

// Graph & Logic Helpers
const getPointY = (stock, maxVal) => 80 - ((Math.min(stock || 0, maxVal) / maxVal) * 80)
const toDate = (str) => new Date(str)

const getMarginDays = (item) => {
  if (item.status !== 'Calculated' || item.cv === undefined || item.cv === null) return 0
  
  const sampleStrength = Math.sqrt(item.intervals_count || 1)
  const marginFactor = item.cv / sampleStrength
  
  // This 0.02 floor will now correctly apply to items with 0 variation [cite: 2026-03-04]
  const finalFactor = Math.max(0.02, marginFactor)
  
  return Math.round(item.days_remaining * finalFactor)
}

const getStatusClass = (item) => {
  if (item.days_remaining === 9999) return 'status-unknown' 
  const buffer = item.target_buffer_days || 7
  if (item.days_remaining <= buffer) return 'status-urgent'
  if (item.days_remaining <= buffer + 7) return 'status-warning'
  return 'status-stable'
}

const getGraphData = (item) => {
  if (!item.history?.length) return null
  const start = toDate(item.history[0].date)
  const today = new Date()
  const maxBound = toDate(item.max_runout || item.expected_restock || new Date().toISOString().split('T')[0])
  const totalMs = Math.max(1, maxBound - start)
  const getX = (d) => ((toDate(d) - start) / totalMs) * 240

  // 1. Calculate the dynamic ceiling for this specific product [cite: 2026-03-04]
  const localMax = Math.max(5, ...item.history.map(p => p.stock))

  let points = []
  let curStock = 0
  item.history.forEach((p) => {
    const x = getX(p.date)
    if (p.event_type?.includes("Restock") || p.event_type === "Init") {
      points.push(`${x},${getPointY(curStock, localMax)}`)
      curStock = p.stock
      points.push(`${x},${getPointY(curStock, localMax)}`)
    } else {
      curStock = p.stock
      points.push(`${x},${getPointY(curStock, localMax)}`)
    }
  })

  const lastEvent = item.history[item.history.length - 1]
  const lastX = getX(lastEvent.date), lastY = getPointY(lastEvent.stock, localMax)
  const nowX = Math.min(240, getX(today))
  const expectedX = getX(item.expected_restock)
  const slope = (expectedX - lastX) !== 0 ? (80 - lastY) / (expectedX - lastX) : 0
  const nowY = lastY + (nowX - lastX) * slope
  const minX = getX(item.min_runout || item.expected_restock)
  const maxX = getX(item.max_runout || item.expected_restock)
  const fanPoints = `${nowX},${nowY} ${minX},80 ${maxX},80`

  return { polyline: points.join(' '), lastX, lastY, nowX, nowY, fanPoints, expectedX, 
    eventDots: item.history.map(p => ({ 
      x: getX(p.date), 
      y: getPointY(p.stock, localMax), 
      label: `${p.event_type}: ${p.stock.toFixed(2)} units`, 
      type: p.event_type, 
      date: p.date 
    }))
  }
}

// Maps confidence levels to status colors for the margin text [cite: 2026-03-04]
const getMarginClass = (item) => {
  if (item.days_remaining === 9999) return 'grey-text'
  const confMap = { 'Low': 'status-urgent', 'Medium': 'status-warning', 'High': 'status-stable' }
  return confMap[item.confidence] || ''
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard">
    <header class="view-header">
      <div class="title-stack">
        <h1>InventoryMGMT</h1>
        <p class="subtitle">For the purposes of determining expenditure & restock timing</p>
      </div>
      
      <div class="burn-summary-header">
        <div class="summary-details">
          <span class="tiny-label">EST. EXPENDITURE</span>
          <div class="main-burn-row">
            <span class="currency">S$</span>
            <span class="total-value">{{ currentTotalDisplay }}</span>
          </div>
        </div>
        <div class="toggle-control">
          <label>per</label>
          <select v-model="timeframe" class="burn-select">
            <option value="daily">Day</option>
            <option value="monthly">Month</option>
            <option value="yearly">Year</option>
          </select>
        </div>
      </div>
    </header>

    <div class="search-section">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input v-model="searchQuery" placeholder="Filter by brand, product, or role..." class="dashboard-search" />
      </div>
    </div>

    <div v-if="loading" class="status-msg">Polishing dashboard layout...</div>

    <div v-else class="forecast-container">
      <div class="forecast-grid">
        <div v-for="item in visibleCards" :key="item.role_id" class="forecast-card">
          <div class="card-header-main">
            <div class="product-info">
              <div class="brand">{{ item.brand }}</div>
              <div class="product-name">{{ item.product_name }}</div>
            </div>
            <div class="days-box" :class="getStatusClass(item)">
              <div class="baseline-row">
                <span class="main-days-num">{{ item.days_remaining === 9999 ? '?' : item.days_remaining }}</span>
                <div class="label-stack">
                  <span class="margin-value" :class="getMarginClass(item)">(&plusmn;{{ getMarginDays(item) }})</span>
                  <span class="days-label">DAYS</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="card-header-sub">
            <div class="role-meta">
              <div class="role-name">
                {{ item.role_name }}
              </div>
              <div class="item-daily-cost" :class="{ 'grey-text': item.days_remaining === 9999 }">
                S${{ item.daily_cost?.toFixed(2) }} 
                <span class="per-day">/ day</span>
              </div>
            </div>
            
            <div class="runout-meta">
              <div class="runout-info">{{ item.expected_restock }}</div>
              <div class="wtp-info" v-if="item.status === 'Calculated' && item.ema_unit_cost > 0">
                <span class="wtp-label">WTP </span>S${{ item.target_deal_price?.toFixed(2) }} ({{ Math.round((item.target_deal_price / item.ema_unit_cost) * 100) }}%)
              </div>
            </div>
          </div>
          
          <div class="card-graph-container">
            <svg v-if="getGraphData(item)" viewBox="0 0 240 80" preserveAspectRatio="none" class="sparkline">
              <line class="zero-baseline" x1="0" y1="80" x2="240" y2="80" />
              <polygon v-if="item.status === 'Calculated'" class="confidence-fan" :points="getGraphData(item).fanPoints" />
              <polyline fill="none" stroke="#42b883" stroke-width="2.5" :points="getGraphData(item).polyline" />
              
              <line v-if="item.status === 'Calculated'" stroke="#42b883" stroke-width="2.5" :x1="getGraphData(item).lastX" :y1="getGraphData(item).lastY" :x2="getGraphData(item).nowX" :y2="getGraphData(item).nowY" />
              
              <line v-if="item.status === 'Calculated'" class="projection-line" :x1="getGraphData(item).nowX" :y1="getGraphData(item).nowY" :x2="getGraphData(item).expectedX" y2="80" />
              
              <svg v-for="(dot, idx) in getGraphData(item).eventDots" :key="idx" :x="dot.x - 5" :y="dot.y - 5" width="10" height="10" viewBox="0 0 10 10" preserveAspectRatio="xMidYMid meet" class="node-wrapper">
                  <circle cx="5" cy="5" r="4.5" :class="['node', { 'node-init': dot.type === 'Init' }]" @mouseenter="activePopup = { id: item.role_id + '-' + idx, ...dot }" @mouseleave="activePopup = null" />
              </svg>

              <svg v-if="item.status === 'Calculated'" :x="getGraphData(item).expectedX - 6" y="74" width="12" height="12" viewBox="0 0 12 12" preserveAspectRatio="xMidYMid meet" class="node-wrapper">
                <circle cx="6" cy="6" r="5" class="node runout-node" @mouseenter="activePopup = { id: item.role_id + '-runout', label: 'Runout Expected', date: item.expected_restock, x: getGraphData(item).expectedX, y: 80 }" @mouseleave="activePopup = null" />
              </svg>
            </svg>
            <div v-if="activePopup?.id.startsWith(item.role_id)" class="graph-tooltip" :style="{ left: (activePopup.x / 240 * 100) + '%', top: (activePopup.y / 80 * 100) + '%' }">
              <div class="tt-date">{{ activePopup.date }}</div>
              <div class="tt-info">{{ activePopup.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hiddenCards.length > 0" class="drawer-container">
        <div class="drawer-header">
          <button class="drawer-toggle" @click="isExpanded = !isExpanded">
            {{ isExpanded ? 'Hide' : 'Show' }} {{ hiddenCards.length }} More Product{{ hiddenCards.length === 1 ? '' : 's' }}
            <span class="chevron" :class="{ rotated: isExpanded }">▼</span>
          </button>
        </div>
        
        <transition name="drawer-fade">
          <div v-if="isExpanded" class="forecast-grid drawer-content">
            <div v-for="item in hiddenCards" :key="item.role_id" class="forecast-card">
              <div class="card-header-main">
                <div class="product-info">
                  <div class="brand">{{ item.brand }}</div>
                  <div class="product-name">{{ item.product_name }}</div>
                </div>
                <div class="days-box" :class="getStatusClass(item)">
                  <div class="baseline-row">
                    <span class="main-days-num">{{ item.days_remaining === 9999 ? '?' : item.days_remaining }}</span>
                    <div class="label-stack">
                      <span class="margin-value" :class="getMarginClass(item)">(&plusmn;{{ getMarginDays(item) }})</span>
                      <span class="days-label">DAYS</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="card-header-sub">
                <div class="role-meta">
                  <div class="role-name">{{ item.role_name }}</div>
                  <div class="item-daily-cost">S${{ item.daily_cost?.toFixed(2) }} <span class="per-day">/ day</span></div>
                </div>
              <div class="runout-meta">
                <div class="runout-info">{{ item.expected_restock }}</div>
                <div class="wtp-info" v-if="item.status === 'Calculated' && item.ema_unit_cost > 0">
                  <span class="wtp-label">WTP </span>S${{ item.target_deal_price?.toFixed(2) }} 
                  ({{ Math.round((item.target_deal_price / item.ema_unit_cost) * 100) }}%)
                </div>
              </div>
              </div>
              
              <div class="card-graph-container">
                <svg v-if="getGraphData(item)" viewBox="0 0 240 80" preserveAspectRatio="none" class="sparkline">
                  <line class="zero-baseline" x1="0" y1="80" x2="240" y2="80" />
                  <polygon v-if="item.status === 'Calculated'" class="confidence-fan" :points="getGraphData(item).fanPoints" />
                  <polyline fill="none" stroke="#42b883" stroke-width="2.5" :points="getGraphData(item).polyline" />
                  <line v-if="item.status === 'Calculated'" class="projection-line" :x1="getGraphData(item).nowX" :y1="getGraphData(item).nowY" :x2="getGraphData(item).expectedX" y2="80" />
                  
                  <svg v-for="(dot, idx) in getGraphData(item).eventDots" :key="idx" :x="dot.x - 5" :y="dot.y - 5" width="10" height="10" viewBox="0 0 10 10" preserveAspectRatio="xMidYMid meet" class="node-wrapper">
                    <circle cx="5" cy="5" r="4.5" :class="['node', { 'node-init': dot.type === 'Init' }]" @mouseenter="activePopup = { id: item.role_id + '-' + idx, ...dot }" @mouseleave="activePopup = null" />
                  </svg>
                  
                  <svg v-if="item.status === 'Calculated'" :x="getGraphData(item).expectedX - 6" y="74" width="12" height="12" viewBox="0 0 12 12" preserveAspectRatio="xMidYMid meet" class="node-wrapper">
                    <circle cx="6" cy="6" r="5" class="node runout-node" @mouseenter="activePopup = { id: item.role_id + '-runout', label: 'Runout Expected', date: item.expected_restock, x: getGraphData(item).expectedX, y: 80 }" @mouseleave="activePopup = null" />
                  </svg>
                </svg>
                <div v-if="activePopup?.id.startsWith(item.role_id)" class="graph-tooltip" :style="{ left: (activePopup.x / 240 * 100) + '%', top: (activePopup.y / 80 * 100) + '%' }">
                  <div class="tt-date">{{ activePopup.date }}</div>
                  <div class="tt-info">{{ activePopup.label }}</div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 2rem; }

/* Search Bar Styling */
.search-section { margin-bottom: 2.5rem; }
.search-input-wrapper { position: relative; max-width: 500px; }
.search-icon { position: absolute; left: 15px; top: 50%; transform: translateY(-50%); opacity: 0.5; }
.dashboard-search { 
  width: 100%; background: #121212; border: 1px solid #333; border-radius: 30px; 
  padding: 12px 20px 12px 45px; color: #eee; font-size: 0.9rem; transition: border-color 0.2s;
}
.dashboard-search:focus { border-color: #42b883; outline: none; background: #1a1a1a; }

/* Financial Header Styling */
.burn-summary-header { background: #1a1a1a; padding: 16px 24px; border-radius: 12px; border-left: 4px solid #42b883; display: flex; align-items: center; gap: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
.tiny-label { font-size: 0.6rem; color: #666; font-weight: 800; letter-spacing: 1px; display: block; margin-bottom: 2px; }
.main-burn-row { display: flex; align-items: baseline; gap: 4px; }
.currency { font-size: 1rem; color: #42b883; font-weight: 700; }
.total-value { font-size: 2.2rem; font-weight: 900; color: #fff; font-family: 'JetBrains Mono', monospace; line-height: 1; }
.toggle-control { display: flex; flex-direction: column; gap: 4px; }
.toggle-control label { font-size: 0.6rem; color: #666; font-weight: 800; text-transform: uppercase; }
.burn-select { background: #222; border: 1px solid #333; color: #42b883; font-size: 0.8rem; font-weight: 700; padding: 4px 8px; border-radius: 4px; cursor: pointer; }

/* Drawer Styling */
.drawer-container { margin-top: 50px; }
.drawer-header { display: flex; align-items: center; justify-content: center; position: relative; margin-bottom: 30px; }
.drawer-header::after { content: ''; position: absolute; left: 0; right: 0; height: 1px; background: #333; z-index: 1; }
.drawer-toggle { z-index: 2; background: #2c3e50; border: 1px solid #444; color: #888; padding: 8px 24px; border-radius: 20px; font-weight: bold; cursor: pointer; font-size: 0.75rem; text-transform: uppercase; transition: 0.2s; }
.drawer-toggle:hover { color: #fff; background: #1a1a1a; border-color: #42b883; }
.chevron { display: inline-block; margin-left: 8px; transition: 0.3s; font-size: 0.6rem; }
.chevron.rotated { transform: rotate(180deg); }

/* Forecast Grid & Transitions */
.forecast-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.forecast-card { background: #121212; border: 1px solid #1e1e1e; border-radius: 16px; padding: 24px; display: flex; flex-direction: column; position: relative; }
.drawer-fade-enter-active, .drawer-fade-leave-active { transition: all 0.5s ease; max-height: 2000px; overflow: hidden; }
.drawer-fade-enter-from, .drawer-fade-leave-to { opacity: 0; max-height: 0; }

/* Product Info */
.card-header-main { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 12px; }
.product-info { flex: 1; display: flex; flex-direction: column; }
.brand { color: #42b883; font-weight: 700; text-transform: uppercase; font-size: 0.7rem; margin-bottom: 4px; }
.product-name { color: #fff; font-weight: 700; font-size: 1.1rem; line-height: 1.3; }

/* Days Box Styles */
.days-box { flex-shrink: 0; }
.baseline-row { display: flex; align-items: baseline; gap: 8px; position: relative; }
.main-days-num { font-size: 2.8rem; font-weight: 900; line-height: 1; margin: 0; }
.label-stack { display: flex; flex-direction: column; position: relative; }
.days-label { font-size: 0.75rem; font-weight: 800; line-height: 1; opacity: 0.9; }
.margin-value { position: absolute; bottom: 100%; left: 0; font-size: 0.85rem; font-weight: 700; opacity: 0.85; white-space: nowrap; padding-bottom: 2px; }

/* Meta & Status Colors */
.card-header-sub { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.role-meta { display: flex; flex-direction: column; gap: 2px; }
.role-name { color: #888; font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; }
.item-daily-cost { font-size: 0.75rem; color: #42b883; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.per-day { font-size: 0.6rem; color: #555; text-transform: uppercase; }
.status-urgent { color: #ff4757; }
.status-warning { color: #f1c40f; }
.status-stable { color: #42b883; }

/* Runout & Willingness to Pay Styling */
.runout-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.runout-info { color: #777; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
.wtp-info { font-size: 0.75rem; color: #42b883; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.wtp-label { font-size: 0.6rem; color: #555; text-transform: uppercase; font-family: 'Inter', sans-serif; font-weight: 800; letter-spacing: 0.5px; }

/* Graph Components */
.card-graph-container { height: 80px; position: relative; margin-top: auto; }
.sparkline { width: 100%; height: 80px; overflow: visible; }
.confidence-fan { fill: #42b883; fill-opacity: 0.07; stroke: none; }
.projection-line { stroke: #42b883; stroke-width: 2; stroke-dasharray: 6; opacity: 0.4; }
.zero-baseline { stroke: #ff4757; stroke-width: 1; opacity: 0.2; }

/* Fixed Node Logic */
.node-wrapper { overflow: visible; }
.node { fill: #42b883; stroke: #000; cursor: pointer; transition: r 0.2s; vector-effect: non-scaling-stroke; }
.runout-node { fill: #ff4757; }
.node:hover { r: 6; fill: #fff; }

.graph-tooltip { position: absolute; transform: translate(-50%, calc(-100% - 12px)); background: #1a1a1a; border: 1px solid #42b883; padding: 8px 12px; border-radius: 6px; color: #fff; font-size: 0.7rem; text-align: center; white-space: nowrap; z-index: 100; box-shadow: 0 8px 20px rgba(0,0,0,0.5); pointer-events: none; }
.tt-date { color: #777; font-size: 0.65rem; margin-bottom: 2px; }
.tt-info { font-weight: 700; color: #42b883; }
.status-unknown { color: #555 !important; }
.grey-text { color: #555 !important; border-color: #333 !important; }
/* Blue styling for initialization data points [cite: 2026-03-04] */
.node-init { fill: #3498db !important; }
</style>