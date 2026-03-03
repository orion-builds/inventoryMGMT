<script setup>
import { ref, onMounted, computed } from 'vue'

// --- Data State ---
const events = ref([])
const products = ref([])
const loading = ref(true)

// --- UI State ---
const showAddForm = ref(false)
const showFilters = ref(false)
const isEditing = ref(false)
const originalEvent = ref(null) // Stores the immutable snapshot for the UPDATE query

// --- Filter & Sort State ---
const filterText = ref('')
const filterStart = ref('')
const filterEnd = ref('')
const filterType = ref('all')
const filterProdId = ref('all')
const sortKey = ref('event_date') 
const sortOrder = ref(-1) // Newest events first

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
      fetch('http://127.0.0.1:8000/events/'),
      fetch('http://127.0.0.1:8000/products/')
    ])
    events.value = (await evRes.json()).events || []
    products.value = (await prodRes.json()).inventory || []
  } catch (error) { console.error("Fetch failed:", error) } finally { loading.value = false }
}

/**
 * Enhanced Filter & Sort Logic
 * Dynamically calculates unit cost for display and sorting.
 */
const filteredEvents = computed(() => {
  let result = events.value.map(e => ({
    ...e,
    unit_cost: e.cost_sgd && e.quantity ? e.cost_sgd / e.quantity : 0
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

// FIX: Creates a non-reactive copy to preserve the original keys
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
  
  // Logic: Override cost in DB if switching to Finished
  const costValue = type.value.includes('Restock') ? priceSgd.value : null
  
  const payload = isEditing.value 
    ? { new_event_type: type.value, new_event_date: eventDate.value, quantity: qty.value, cost_sgd: costValue }
    : { product_id: selectedProduct.value.product_id, event_type: type.value, event_date: eventDate.value, quantity: qty.value, cost_sgd: costValue }

  let url = 'http://127.0.0.1:8000/events/'
  
  // FIX: Ensures characters like "(" and ")" are correctly encoded
  if (isEditing.value) {
    const queryParams = new URLSearchParams({
      product_id: originalEvent.value.product_id,
      event_type: originalEvent.value.event_type,
      event_date: originalEvent.value.event_date
    })
    url += `?${queryParams.toString()}`
  }

  try {
    const res = await fetch(url, {
      method: isEditing.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (!res.ok) {
      const result = await res.json()
      alert(result.detail || "Error saving event.")
    } else {
      showAddForm.value = false
      await fetchData()
    }
  } catch (err) { console.error("Save failed:", err) }
}

const deleteEvent = async (e) => {
  if (!confirm("Delete this log entry?")) return
  const queryParams = new URLSearchParams({
    product_id: e.product_id,
    event_type: e.event_type,
    event_date: e.event_date
  })
  const url = `http://127.0.0.1:8000/events/?${queryParams.toString()}`
  try {
    if ((await fetch(url, { method: 'DELETE' })).ok) await fetchData()
  } catch (err) { console.error("Delete failed:", err) }
}

onMounted(fetchData)
</script>

<template>
  <div class="events-container">
    <header class="view-header">
      <h1>Inventory Events</h1>
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
            <th @click="sortBy('unit_cost')" class="sortable">Unit Cost <span v-if="sortKey === 'unit_cost'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th class="actions-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in filteredEvents" :key="`${e.product_id}-${e.event_date}-${e.event_type}`" class="event-row">
            <td>{{ e.event_date }}</td>
            <td class="bold">{{ e.brand }} {{ e.name }}</td>
            <td><span class="badge" :class="e.event_type.includes('Restock') ? 'restocked' : 'finished'">{{ e.event_type }}</span></td>
            <td>{{ e.quantity }}</td>
            <td>{{ e.cost_sgd ? `S$${e.cost_sgd.toFixed(2)}` : '-' }}</td>
            <td class="unit-cost-cell">{{ e.cost_sgd ? `S$${(e.cost_sgd / e.quantity).toFixed(2)}` : '-' }}</td>
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
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Entry' : 'Log Activity' }}</h3>
          <button @click="showAddForm = false" class="close-x">&times;</button>
        </div>
        <div class="form-line top">
          <div class="search-container">
            <input v-model="searchQuery" @focus="showDropdown = true" :disabled="isEditing" placeholder="Search Product..." />
            <div v-if="showDropdown" class="results-dropdown">
              <div v-for="p in products.filter(p => `${p.brand} ${p.name}`.toLowerCase().includes(searchQuery.toLowerCase())).slice(0,5)" 
                :key="p.product_id" @click="selectedProduct=p; searchQuery=`${p.brand} - ${p.name}`; showDropdown=false" class="result-item">
                <strong>{{ p.brand }}</strong> {{ p.name }}
              </div>
            </div>
          </div>
          <select v-model="type">
            <option value="Restock (+)">Restocked (+)</option>
            <option value="Finished (-)">Finished (-)</option>
          </select>
        </div>
        <div class="form-line bottom">
          <div class="input-group"><label>Qty</label><input v-model.number="qty" type="number" /></div>
          <div class="input-group" v-if="type.includes('Restock')"><label>Total Price (SGD)</label><input v-model.number="priceSgd" type="number" step="0.01" /></div>
          <div class="input-group"><label>Date</label><input v-model="eventDate" type="date" /></div>
          <button @click="saveEvent" class="btn-save">{{ isEditing ? 'Update Entry' : 'Log Entry' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.events-container { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-actions { display: flex; gap: 12px; }

/* Filter Drawer Styling */
.btn-filter { background: transparent; border: 1px solid #444; color: #888; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px; transition: 0.2s; }
.btn-filter.active { background: #34495e; border-color: #42b883; color: #fff; }

.filter-drawer { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; margin-bottom: 2rem; overflow: hidden; }
.filter-grid { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.filter-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
.filter-input { background: #222; border: 1px solid #444; color: #eee; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; }
.btn-reset { background: transparent; border: 1px solid #444; color: #666; padding: 8px 16px; border-radius: 6px; cursor: pointer; height: 38px; }

/* Drawer Animation */
.drawer-enter-active, .drawer-leave-active { transition: all 0.3s ease; max-height: 300px; opacity: 1; }
.drawer-enter-from, .drawer-leave-to { max-height: 0; opacity: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; }

.table-wrapper { background: #111; border-radius: 12px; border: 1px solid #222; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; color: #42b883; text-align: left; padding: 14px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { background: #222; }
td { padding: 14px; border-bottom: 1px solid #222; }
.unit-cost-cell { color: #888; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }

.badge { padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; }
.badge.restocked { color: #42b883; background: rgba(66, 184, 131, 0.1); }
.badge.finished { color: #ff4757; background: rgba(255, 71, 87, 0.1); }

/* Hover Reveal for Buttons */
.action-buttons { opacity: 0; transition: 0.2s; display: flex; gap: 8px; justify-content: flex-end; }
.event-row:hover .action-buttons { opacity: 1; }
.event-row:hover { background: #161616; }
.btn-edit, .btn-delete { padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-edit { background: transparent; border: 1px solid #444; color: #888; }
.btn-delete { background: #ff4757; color: #fff; border: none; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #1a1a1a; border: 1px solid #333; border-radius: 16px; padding: 32px; width: 600px; }
.form-line { display: flex; gap: 16px; margin-bottom: 24px; align-items: flex-end; }
.search-container { flex: 2; position: relative; }
.input-group { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.input-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
input, select { background: #222; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 8px; }
.btn-save { width: 100%; background: #42b883; color: #000; font-weight: 800; padding: 12px; border: none; border-radius: 8px; cursor: pointer; }
.results-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #222; border: 1px solid #333; border-radius: 8px; z-index: 100; margin-top: 4px; }
.result-item { padding: 12px; cursor: pointer; }
.result-item:hover { background: #333; color: #42b883; }
</style>