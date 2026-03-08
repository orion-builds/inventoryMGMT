<script setup>
import { ref, onMounted, computed } from 'vue'
import { authorizedFetch } from '../api'

// --- Data State ---
const events = ref([])
const products = ref([])
const loading = ref(true)

// --- UI State ---
const showAddForm = ref(false)
const showFilters = ref(false)
const isEditing = ref(false)
const originalEvent = ref(null) 

// --- Filter & Sort State ---
const filterText = ref('')
const filterStart = ref('')
const filterEnd = ref('')
const filterType = ref('all')
const filterProdId = ref('all')
const sortKey = ref('event_date') 
const sortOrder = ref(-1)

// --- Form State ---
const searchQuery = ref('')
const showDropdown = ref(false)
const selectedProduct = ref(null)
const type = ref('Restock (+)')
const qty = ref(1)
const priceSgd = ref(0)
const eventDate = ref(new Date().toISOString().split('T')[0])

const fetchData = async () => {
  loading.value = true
  try {
    const [evRes, prodRes] = await Promise.all([
      authorizedFetch('/events/'),
      authorizedFetch('/products/with-stock')
    ])
    
    // Check for success before parsing [cite: 2026-03-08]
    if (evRes.ok && prodRes.ok) {
      events.value = (await evRes.json()).events || []
      products.value = (await prodRes.json()).inventory || []
    }
  } catch (error) { 
    console.error("Fetch failed:", error) 
  } finally { 
    loading.value = false 
  }
}

const filteredEvents = computed(() => {
  let result = events.value.map(e => ({
    ...e,
    unit_cost_display: e.cost_sgd && e.quantity ? e.cost_sgd / e.quantity : 0,
  })).filter(e => {
    const matchesSearch = !filterText.value || 
      `${e.brand} ${e.name}`.toLowerCase().includes(filterText.value.toLowerCase());
    const matchesDate = (!filterStart.value || e.event_date >= filterStart.value) &&
                        (!filterEnd.value || e.event_date <= filterEnd.value);
    const matchesType = filterType.value === 'all' || e.event_type === filterType.value;
    const matchesProduct = filterProdId.value === 'all' || e.product_id === Number(filterProdId.value);
    return matchesSearch && matchesDate && matchesType && matchesProduct;
  });

  result.sort((a, b) => {
    let valA = a[sortKey.value]; let valB = b[sortKey.value]
    if (valA === null) valA = 0
    if (valB === null) valB = 0
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    return valA < valB ? -1 * sortOrder.value : 1 * sortOrder.value
  })
  return result
})

const uniqueProductsInEvents = computed(() => {
  const seen = new Set();
  return events.value.filter(e => {
    const duplicate = seen.has(e.product_id);
    seen.add(e.product_id);
    return !duplicate;
  }).map(e => ({ id: e.product_id, label: `${e.brand} ${e.name}` }));
})

const sortBy = (key) => {
  if (sortKey.value === key) sortOrder.value *= -1
  else { sortKey.value = key; sortOrder.value = 1 }
}

const openCreateModal = () => {
  isEditing.value = false; originalEvent.value = null
  searchQuery.value = ''; selectedProduct.value = null; qty.value = 1; priceSgd.value = 0
  type.value = 'Restock (+)'
  eventDate.value = new Date().toISOString().split('T')[0]
  showAddForm.value = true
}

const openEditModal = (event) => {
  isEditing.value = true
  originalEvent.value = { ...event } 
  selectedProduct.value = { product_id: event.product_id, brand: event.brand, name: event.name }
  searchQuery.value = `${event.brand} - ${event.name}`
  type.value = event.event_type; qty.value = event.quantity
  priceSgd.value = event.cost_sgd || 0; eventDate.value = event.event_date
  showAddForm.value = true
}

const saveEvent = async () => {
  if (!selectedProduct.value) return alert("Please select a product.")
  
  // Existing validation logic... [cite: 2026-03-03]
  if (type.value === 'Init' && !isEditing.value) {
    const hasInit = events.value.some(e => e.product_id === selectedProduct.value.product_id && e.event_type === 'Init')
    if (hasInit) return alert("An initialization entry already exists for this product.")
  }

  const costValue = (type.value.includes('Restock') || type.value === 'Init') ? priceSgd.value : null
  const payload = isEditing.value 
    ? { new_event_type: type.value, new_event_date: eventDate.value, quantity: qty.value, cost_sgd: costValue }
    : { product_id: selectedProduct.value.product_id, event_type: type.value, event_date: eventDate.value, quantity: qty.value, cost_sgd: costValue }

  let endpoint = '/events/' // Use relative path [cite: 2026-03-05]
  if (isEditing.value) {
    const queryParams = new URLSearchParams({
      product_id: originalEvent.value.product_id,
      event_type: originalEvent.value.event_type,
      event_date: originalEvent.value.event_date
    })
    endpoint += `?${queryParams.toString()}`
  }

  try {
    const res = await authorizedFetch(endpoint, {
      method: isEditing.value ? 'PATCH' : 'POST',
      body: JSON.stringify(payload)
    })
    if (res.ok) { showAddForm.value = false; await fetchData() }
  } catch (err) { console.error("Save failed:", err) }
}

const deleteEvent = async (e) => {
  if (!confirm("Delete this log entry?")) return
  const queryParams = new URLSearchParams({ 
    product_id: e.product_id, 
    event_type: e.event_type, 
    event_date: e.event_date 
  })
  const endpoint = `/events/?${queryParams.toString()}`
  
  try { 
    const res = await authorizedFetch(endpoint, { method: 'DELETE' })
    if (res.ok) await fetchData() 
  } catch (err) { 
    console.error("Delete failed:", err) 
  }
}

const isStockAvailable = computed(() => {
  if (type.value !== 'Finished (-)') return true;
  if (!selectedProduct.value || selectedProduct.value.stock_on_hand === undefined) return true;
  return qty.value <= selectedProduct.value.stock_on_hand;
});

const stockErrorMessage = computed(() => {
  if (!isStockAvailable.value && selectedProduct.value) {
    return `Error: Only ${selectedProduct.value.stock_on_hand} units remaining in inventory.`;
  }
  return "";
});

// NEW: Future Date Validation
const maxDateString = new Date().toISOString().split('T')[0];
const isDateValid = computed(() => eventDate.value <= maxDateString);

onMounted(fetchData)
</script>

<template>
  <div class="events-container">
    <header class="view-header">
      <h1>Inventory Ledger</h1>
      <div class="header-actions">
        <button @click="showFilters = !showFilters" class="btn-filter" :class="{ active: showFilters }">
          🔍 Filter
        </button>
        <button @click="openCreateModal" class="btn-toggle">+ New Event</button>
      </div>
    </header>

    <transition name="drawer">
      <div v-if="showFilters" class="filter-drawer">
        <div class="filter-grid">
          <input v-model="filterText" placeholder="Search Brand/Product..." class="filter-input main-search" />
          <div class="filter-group"><label>From</label><input v-model="filterStart" type="date" class="filter-input" /></div>
          <div class="filter-group"><label>To</label><input v-model="filterEnd" type="date" class="filter-input" /></div>
          <select v-model="filterType" class="filter-input">
            <option value="all">All Types</option>
            <option value="Restock (+)">Restock (+)</option>
            <option value="Finished (-)">Finished (-)</option>
            <option value="Init">Initialization</option>
          </select>
          <select v-model="filterProdId" class="filter-input">
            <option value="all">All Products</option>
            <option v-for="p in uniqueProductsInEvents" :key="p.id" :value="p.id">{{ p.label }}</option>
          </select>
          <button @click="filterText=''; filterStart=''; filterEnd=''; filterType='all'; filterProdId='all'" class="btn-reset">Reset</button>
        </div>
      </div>
    </transition>

    <div class="table-wrapper">
      <table v-if="!loading && filteredEvents.length > 0">
        <thead>
          <tr>
            <th @click="sortBy('event_date')" class="sortable">Date <span v-if="sortKey === 'event_date'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('brand')" class="sortable">Product <span v-if="sortKey === 'brand'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('event_type')" class="sortable">Type <span v-if="sortKey === 'event_type'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('quantity')" class="sortable">Qty <span v-if="sortKey === 'quantity'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('cost_sgd')" class="sortable">Total Cost <span v-if="sortKey === 'cost_sgd'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('unit_cost_display')" class="sortable">Unit Cost <span v-if="sortKey === 'unit_cost_display'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('implied_h')" class="sortable">Value ($H$) <span v-if="sortKey === 'implied_h'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th class="actions-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in filteredEvents" :key="`${e.product_id}-${e.event_date}-${e.event_type}`" class="event-row">
            <td>{{ e.event_date }}</td>
            <td class="bold">{{ e.brand }} {{ e.name }}</td>
            <td>
              <span class="badge" :class="{
                'restocked': e.event_type.includes('Restock'),
                'finished': e.event_type.includes('Finished'),
                'init': e.event_type === 'Init'
              }">{{ e.event_type }}</span>
            </td>
            <td>{{ e.quantity }}</td>
            <td>{{ e.cost_sgd ? `S$${e.cost_sgd.toFixed(2)}` : '-' }}</td>
            <td class="">{{ e.cost_sgd ? `S$${e.unit_cost_display.toFixed(2)}` : '-' }}</td>
            <td class="h-cell">
              <template v-if="typeof e.implied_h === 'number'">
                <span class="h-val">{{ e.implied_h.toFixed(1) }}%</span>
                <span class="h-label">/day</span>
              </template>
              <span v-else class="empty-text">-</span>
            </td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit" @click="openEditModal(e)">Edit</button>
                <button @click="deleteEvent(e)" class="btn-delete">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loading" class="status-msg">Loading history...</p>
      <p v-else class="status-msg">No logs found.</p>
    </div>

    <div v-if="showAddForm" class="modal-overlay" @click.self="showAddForm = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Entry' : 'Log Activity' }}</h3>
          <button @click="showAddForm = false" class="close-x-circle">&times;</button>
        </div>

        <div class="form-body">
          <div class="form-row">
            <div class="input-group full-width">
              <label>Product</label>
              <div class="search-container">
                <input v-model="searchQuery" @focus="showDropdown = true" :disabled="isEditing" placeholder="Search Product..." />
                <div v-if="showDropdown" class="results-dropdown">
                  <div v-for="p in products.filter(p => `${p.brand} ${p.name}`.toLowerCase().includes(searchQuery.toLowerCase())).slice(0,5)" 
                    :key="p.product_id" @click="selectedProduct=p; searchQuery=`${p.brand} - ${p.name}`; showDropdown=false" class="result-item">
                    <strong>{{ p.brand }}</strong> {{ p.name }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <div class="label-with-info">
                <label>Entry Type</label>
                <div class="info-trigger">
                  ?
                  <div class="info-tooltip">
                    <p><strong class="text-green">Restock (+):</strong> Clean purchase data. Used for WTP & Penalty math.</p>
                    <p><strong class="text-blue">Init:</strong> Half-empty stash or unknown price. Consumption rate starts only after this partial unit is finished.</p>
                    <p><strong class="text-red">Finished (-):</strong> Record only current unit used up. Typically 1.</p>
                  </div>
                </div>
              </div>
              <select v-model="type">
                <option value="Restock (+)">Restocked (+)</option>
                <option value="Finished (-)">Finished (-)</option>
                <option value="Init">Initialization (Legacy)</option>
              </select>
            </div>
            <div class="input-group">
              <label>Date</label>
              <input v-model="eventDate" type="date" :max="maxDateString" />
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <label>Quantity</label>
              <input v-model.number="qty" type="number" step="0.1" placeholder="e.g. 0.6" />
            </div>
            <div class="input-group" v-if="type.includes('Restock') || type === 'Init'">
              <label>Total Price (SGD)</label>
              <input v-model.number="priceSgd" type="number" step="0.01" />
            </div>
          </div>

          <transition name="fade">
            <div v-if="!isStockAvailable || !isDateValid" class="stock-warning-box">
              <span class="warning-icon">⚠️</span>
              {{ !isDateValid ? "Error: Event date cannot be in the future." : stockErrorMessage }}
            </div>
          </transition>

          <button 
            @click="saveEvent" 
            class="btn-save" 
            :disabled="!isStockAvailable || !isDateValid"
            :class="{ 'btn-disabled': !isStockAvailable || !isDateValid }"
          >
            {{ isEditing ? 'Update Entry' : 'Log Entry' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Main Container & Header */
.events-container { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-actions { display: flex; gap: 12px; }

/* Filter System */
.filter-drawer { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; margin-bottom: 2rem; overflow: hidden; }
.filter-grid { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.filter-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
.filter-input { background: #222; border: 1px solid #444; color: #eee; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; }
.btn-reset { background: transparent; border: 1px solid #444; color: #666; padding: 8px 16px; border-radius: 6px; cursor: pointer; height: 38px; }

/* Transitions */
.drawer-enter-active { transition: all 0.2s cubic-bezier(0, 0, 0.2, 1); max-height: 250px; }
.drawer-leave-active { transition: all 0.15s cubic-bezier(0.4, 0, 1, 1); max-height: 250px; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; max-height: 0; transform: translateY(-8px) scale(0.98); }

/* Table Styling */
.table-wrapper { background: #111; border-radius: 12px; border: 1px solid #222; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; color: #42b883; text-align: left; padding: 12px 14px; font-size: 0.75rem; text-transform: uppercase; border-bottom: 2px solid #222; transition: 0.2s; }
th.sortable:hover { background: #222; cursor: pointer; color: #fff; }
.sortable { cursor: pointer; user-select: none; }
td { padding: 14px; border-bottom: 1px solid #222; }
.event-row:hover { background: #161616; }
.bold { font-weight: bold; }

/* Metrics & Badges */
.h-cell { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }
.h-label { font-size: 0.6rem; color: #555; text-transform: uppercase; font-family: 'Inter', sans-serif; font-weight: 800; margin-left: 2px; }
.badge { padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; white-space: nowrap;}
.badge.restocked { color: #42b883; background: rgba(66, 184, 131, 0.1); }
.badge.finished { color: #ff4757; background: rgba(255, 71, 87, 0.1); }
.badge.init { color: #3498db; background: rgba(52, 152, 219, 0.1); }

/* Modal & Form Body [cite: 2026-03-04] */
/* Inherits base modal styles from global CSS */
.modal-content { 
  width: 500px; /* Preserve specific width for the events modal */
}

.form-body { display: flex; flex-direction: column; gap: 20px; margin-top: 20px; }
.form-row { display: flex; gap: 16px; width: 100%; }
.full-width { flex: 1; }
.input-group { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.input-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
input, select { background: #222; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; font-size: 0.9rem; transition: 0.2s; }
input:focus, select:focus { border-color: #42b883; outline: none; background: #2a2a2a; }

/* Note: Circular Close Button CSS removed entirely to use global styles */

/* Tooltip System [cite: 2026-03-04] */
.label-with-info { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.info-trigger { width: 14px; height: 14px; background: #333; color: #888; border-radius: 50%; font-size: 0.6rem; font-weight: 900; display: flex; align-items: center; justify-content: center; cursor: help; position: relative; }
.info-tooltip { position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); width: 240px; background: #222; border: 1px solid #444; color: #eee; padding: 12px; border-radius: 8px; font-size: 0.75rem; line-height: 1.4; opacity: 0; pointer-events: none; transition: 0.2s; z-index: 100; box-shadow: 0 10px 20px rgba(0,0,0,0.4); }
.info-trigger:hover .info-tooltip { opacity: 1; bottom: 150%; }
.info-tooltip p { margin-bottom: 12px; }
.info-tooltip p:last-child { margin-bottom: 0; }
.text-green { color: #42b883; }
.text-blue { color: #3498db; }
.text-red { color: #ff4757; }

/* Buttons */
.btn-save { width: 100%; background: #42b883; color: #000; font-weight: 800; padding: 14px; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; }
.action-buttons { opacity: 0; transition: 0.2s; display: flex; gap: 8px; justify-content: flex-end; }
.event-row:hover .action-buttons { opacity: 1; }
.btn-edit, .btn-delete { padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-edit { background: transparent; border: 1px solid #444; color: #888; }
.btn-delete { background: #ff4757; color: #fff; border: none; }

/* Notification styling [cite: 2026-03-04] */
.stock-warning-box {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid #ff4757;
  color: #ff4757;
  padding: 10px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.warning-icon { font-size: 1rem; }
.btn-disabled { opacity: 0.4; cursor: not-allowed !important; filter: grayscale(1); }

/* Transition [cite: 2026-03-04] */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>