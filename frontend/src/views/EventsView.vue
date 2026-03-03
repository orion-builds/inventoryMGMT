<script setup>
import { ref, onMounted, computed } from 'vue'

const events = ref([])
const products = ref([])
const loading = ref(true)
const showAddForm = ref(false)

// Logic State for Patching
const isEditing = ref(false)
const originalEvent = ref(null) // Stores the keys of the event being edited

// Form State
const searchQuery = ref('')
const showDropdown = ref(false)
const selectedProduct = ref(null)
const type = ref('restocked')
const qty = ref(1)
const priceSgd = ref(0)
const eventDate = ref(new Date().toISOString().split('T')[0])

// 1. Dynamic Autocomplete Logic
const filteredProducts = computed(() => {
  if (!searchQuery.value) return []
  return products.value.filter(p => 
    p.brand.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
    p.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  ).slice(0, 5)
})

const selectProduct = (prod) => {
  selectedProduct.value = prod
  searchQuery.value = `${prod.brand} - ${prod.name}`
  showDropdown.value = false
}

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

// Open modal for a NEW entry
const openCreateModal = () => {
  isEditing.value = false
  originalEvent.value = null
  searchQuery.value = ''; selectedProduct.value = null; qty.value = 1; priceSgd.value = 0
  eventDate.value = new Date().toISOString().split('T')[0]
  showAddForm.value = true
}

// Open modal for EDITING an entry
const openEditModal = (event) => {
  isEditing.value = true
  originalEvent.value = event
  // Pre-fill form
  selectedProduct.value = { product_id: event.product_id, brand: event.brand, name: event.name }
  searchQuery.value = `${event.brand} - ${event.name}`
  type.value = event.event_type
  qty.value = event.quantity
  priceSgd.value = event.cost_sgd || 0
  eventDate.value = event.event_date
  showAddForm.value = true
}

const saveEvent = async () => {
  if (!selectedProduct.value) return alert("Please select a product.")
  
  const payload = isEditing.value 
    ? { quantity: qty.value, cost_sgd: type.value === 'restocked' ? priceSgd.value : null }
    : {
        product_id: selectedProduct.value.product_id,
        event_type: type.value,
        event_date: eventDate.value,
        quantity: qty.value,
        cost_sgd: type.value === 'restocked' ? priceSgd.value : null
      }

  let url = 'http://127.0.0.1:8000/events/'
  if (isEditing.value) {
    const params = new URLSearchParams({
      product_id: originalEvent.value.product_id,
      event_type: originalEvent.value.event_type,
      event_date: originalEvent.value.event_date
    })
    url += `?${params}`
  }

  try {
    const response = await fetch(url, {
      method: isEditing.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (response.ok) {
      showAddForm.value = false 
      await fetchData()
    }
  } catch (err) { console.error(err) }
}

const deleteEvent = async (event) => {
  if (!confirm("Delete this log entry?")) return
  const params = new URLSearchParams({
    product_id: event.product_id,
    event_type: event.event_type,
    event_date: event.event_date
  })
  try {
    const response = await fetch(`http://127.0.0.1:8000/events/?${params}`, { method: 'DELETE' })
    if (response.ok) await fetchData()
  } catch (err) { console.error("Delete failed:", err) }
}

onMounted(fetchData)
</script>

<template>
  <div class="events-container">
    <header class="view-header">
      <h1>Inventory Events</h1>
      <button @click="openCreateModal" class="btn-toggle">+ New Event</button>
    </header>

    <div v-if="showAddForm" class="modal-overlay" @click.self="showAddForm = false">
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Entry' : 'Log Activity' }}</h3>
          <button @click="showAddForm = false" class="close-x">&times;</button>
        </div>
        
        <div class="form-line top">
          <div class="search-container">
            <input 
              v-model="searchQuery" 
              @focus="showDropdown = true"
              :disabled="isEditing"
              placeholder="Search Product (e.g. CeraVe)..." 
              class="search-input"
            />
            <div v-if="showDropdown && filteredProducts.length" class="results-dropdown">
              <div v-for="p in filteredProducts" :key="p.product_id" @click="selectProduct(p)" class="result-item">
                <strong>{{ p.brand }}</strong> {{ p.name }}
              </div>
            </div>
          </div>

          <select v-model="type" class="type-select" :disabled="isEditing">
            <option value="restocked">Restocked (+)</option>
            <option value="finished">Finished (-)</option>
          </select>
        </div>

        <div class="form-line bottom">
          <div class="input-group">
            <label>Qty</label>
            <input v-model.number="qty" type="number" />
          </div>

          <div class="input-group" v-if="type === 'restocked'">
            <label>Price (SGD)</label>
            <input v-model.number="priceSgd" type="number" step="0.01" />
          </div>

          <div class="input-group">
            <label>Date</label>
            <input v-model="eventDate" type="date" :disabled="isEditing" />
          </div>

          <button @click="saveEvent" class="btn-save">{{ isEditing ? 'Update Entry' : 'Log Entry' }}</button>
        </div>
      </div>
    </div>

    <div class="table-wrapper">
      <table v-if="!loading && events.length > 0">
        <thead>
          <tr>
            <th>Date</th>
            <th>Product</th>
            <th>Type</th>
            <th>Qty</th>
            <th>Cost</th>
            <th class="actions-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in events" :key="`${e.product_id}-${e.event_date}-${e.event_type}`" class="event-row">
            <td>{{ e.event_date }}</td>
            <td class="bold">{{ e.brand }} {{ e.name }}</td>
            <td><span class="badge" :class="e.event_type">{{ e.event_type }}</span></td>
            <td>{{ e.quantity }}</td>
            <td>{{ e.cost_sgd ? `S$${e.cost_sgd.toFixed(2)}` : '-' }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit" @click="openEditModal(e)">Edit</button>
                <button class="btn-delete" @click="deleteEvent(e)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loading" class="status-msg">Loading history...</p>
      <p v-else class="status-msg">No events recorded.</p>
    </div>
  </div>
</template>

<style scoped>
/* Table Row Hover Logic */
.event-row .action-buttons {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.event-row:hover .action-buttons { opacity: 1; }
.event-row:hover { background-color: #2a2a2a; }

.btn-edit {
  background: transparent;
  border: 1px solid #888;
  color: #ccc;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: bold;
}
.btn-edit:hover { border-color: #3498db; color: #3498db; }

.btn-delete {
  background-color: #e74c3c;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: bold;
}
.btn-delete:hover { background-color: #c0392b; }

.actions-cell { width: 140px; padding-right: 15px; }
th:last-child, td:last-child { text-align: right; }

/* Existing Styling */
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); display: flex; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(4px); }
.modal-content { width: 90%; max-width: 800px; background: #252525; border-radius: 8px; border-left: 4px solid #3498db; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.close-x { background: none; border: none; color: #888; font-size: 2rem; cursor: pointer; }
.form-line { display: flex; gap: 15px; align-items: flex-end; margin-bottom: 20px; }
.search-container { flex: 2; position: relative; }
.type-select { flex: 1; height: 38px; }
.input-group { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.input-group label { font-size: 0.7rem; color: #888; text-transform: uppercase; font-weight: bold; }
.results-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #333; border: 1px solid #444; border-radius: 4px; z-index: 10; margin-top: 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
.result-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #444; }
.result-item:hover { background: #444; color: #3498db; }
.table-wrapper { background: #222; border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #2c3e50; color: var(--primary-green); text-align: left; padding: 12px; font-size: 0.85rem; text-transform: uppercase; }
td { padding: 12px; border-bottom: 1px solid #333; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; }
.badge.restocked { color: #42b883; background: rgba(66, 184, 131, 0.1); }
.badge.finished { color: #e74c3c; background: rgba(231, 76, 60, 0.1); }
.btn-save { padding: 0 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; height: 38px; }
.bold { font-weight: bold; }
.status-msg { padding: 40px; text-align: center; color: #888; }
</style>