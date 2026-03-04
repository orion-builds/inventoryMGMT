<script setup>
import { ref, onMounted, computed } from 'vue'

// --- Data State ---
const products = ref([])
const loading = ref(true)
const showModal = ref(false)
const showFilters = ref(false)
const isEditing = ref(false)
const currentProductId = ref(null)

// --- Filter State ---
const searchQuery = ref('')
const filterUnit = ref('all')
const minSize = ref(0)
const maxSize = ref(2000)
const absMax = ref(2000) // Dynamic ceiling based on data
const sortKey = ref('brand')
const sortOrder = ref(1) 

// --- Form State ---
const brand = ref('')
const name = ref('')
const amount = ref(0)
const unit = ref('ml')

const fetchProducts = async () => {
  loading.value = true
  try {
    const response = await fetch("http://127.0.0.1:8000/products/")
    const data = await response.json()
    products.value = data.inventory
    
    // Set dynamic slider bounds [cite: 2026-03-03]
    if (products.value.length > 0) {
      const sizes = products.value.map(p => p.amount)
      absMax.value = Math.max(...sizes)
      maxSize.value = absMax.value
    }
  } catch (error) { console.error(error) } finally { loading.value = false }
}

// Ensure knobs don't cross [cite: 2026-03-03]
const handleMin = () => { if (minSize.value > maxSize.value) minSize.value = maxSize.value }
const handleMax = () => { if (maxSize.value < minSize.value) maxSize.value = minSize.value }

const filteredProducts = computed(() => {
  let result = [...products.value]
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => 
      p.brand.toLowerCase().includes(query) || p.name.toLowerCase().includes(query)
    )
  }
  
  if (filterUnit.value !== 'all') {
    result = result.filter(p => p.unit_of_measure === filterUnit.value)
  }
  
  // Apply Double-Knob Logic [cite: 2026-03-03]
  result = result.filter(p => p.amount >= minSize.value && p.amount <= maxSize.value)

  result.sort((a, b) => {
    let valA = a[sortKey.value]; let valB = b[sortKey.value]
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    return valA < valB ? -1 * sortOrder.value : 1 * sortOrder.value
  })
  return result
})

// --- CRUD Actions ---
const openCreateModal = () => {
  isEditing.value = false; currentProductId.value = null
  brand.value = ''; name.value = ''; amount.value = 0; unit.value = 'ml'
  showModal.value = true
}

const openEditModal = (product) => {
  isEditing.value = true; currentProductId.value = product.product_id
  brand.value = product.brand; name.value = product.name
  amount.value = product.amount; unit.value = product.unit_of_measure
  showModal.value = true
}

const saveProduct = async () => {
  const payload = { brand: brand.value, name: name.value, amount: amount.value, unit_of_measure: unit.value }
  const url = isEditing.value ? `http://127.0.0.1:8000/products/${currentProductId.value}` : 'http://127.0.0.1:8000/products/'
  try {
    const res = await fetch(url, { method: isEditing.value ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (res.ok) { showModal.value = false; await fetchProducts() }
  } catch (err) { console.error(err) }
}

const deleteProduct = async (id) => {
  if (!confirm("Delete this product?")) return
  try { if ((await fetch(`http://127.0.0.1:8000/products/${id}`, { method: 'DELETE' })).ok) await fetchProducts() } catch (err) { console.error(err) }
}

const sortBy = (key) => {
  if (sortKey.value === key) sortOrder.value *= -1
  else { sortKey.value = key; sortOrder.value = 1 }
}

onMounted(fetchProducts)
</script>

<template>
  <div class="products-container">
    <header class="view-header">
      <h1>Product Catalog</h1>
      <div class="header-actions">
        <button @click="showFilters = !showFilters" class="btn-filter" :class="{ active: showFilters }">
          🔍 Filter
        </button>
        <button @click="openCreateModal" class="btn-toggle">+ New Product</button>
      </div>
    </header>

    <transition name="drawer">
      <div v-if="showFilters" class="filter-drawer">
        <div class="filter-grid">
          <div class="filter-group main-search">
            <label>Search</label>
            <input v-model="searchQuery" placeholder="Brand or Name..." class="filter-input" />
          </div>
          
          <div class="filter-group slider-group">
            <label>Size Range: {{ minSize }} - {{ maxSize }}</label>
            <div class="multi-range-container">
              <input type="range" v-model.number="minSize" :min="0" :max="absMax" @input="handleMin" class="range-input min-input" />
              <input type="range" v-model.number="maxSize" :min="0" :max="absMax" @input="handleMax" class="range-input max-input" />
              <div class="slider-track"></div>
            </div>
          </div>

          <div class="filter-group">
            <label>Unit</label>
            <select v-model="filterUnit" class="filter-input">
              <option value="all">All Units</option>
              <option value="ml">ml</option>
              <option value="g">g</option>
              <option value="pcs">pcs</option>
              <option value="caps">caps</option>
            </select>
          </div>

          <button @click="searchQuery=''; filterUnit='all'; minSize=0; maxSize=absMax;" class="btn-reset">Reset</button>
        </div>
      </div>
    </transition>

    <div class="table-wrapper">
      <table v-if="!loading && filteredProducts.length > 0">
        <thead>
          <tr>
            <th @click="sortBy('brand')" class="sortable">Brand <span v-if="sortKey === 'brand'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('name')" class="sortable">Name <span v-if="sortKey === 'name'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('amount')" class="sortable">Size <span v-if="sortKey === 'amount'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('unit')" class="sortable"> Unit <span v-if="sortKey === 'unit'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th class="actions-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredProducts" :key="item.product_id" class="product-row">
            <td class="bold">{{ item.brand }}</td>
            <td>{{ item.name }}</td>
            <td>{{ item.amount }}</td>
            <td>{{ item.unit_of_measure }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit" @click="openEditModal(item)">Edit</button>
                <button @click="deleteProduct(item.product_id)" class="btn-delete">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loading" class="status-msg">Loading products...</p>
      <p v-else class="status-msg">No products match your filters.</p>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Product' : 'Add Product' }}</h3>
          <button @click="showModal = false" class="close-x">&times;</button>
        </div>
        <div class="form-grid">
          <input v-model="brand" placeholder="Brand" />
          <input v-model="name" placeholder="Product Name" />
          <input v-model.number="amount" type="number" placeholder="Size" />
          <select v-model="unit">
            <option value="ml">ml</option>
            <option value="g">g</option>
            <option value="pcs">pcs</option>
            <option value="caps">caps</option>
          </select>
        </div>
        <button @click="saveProduct" class="btn-save">{{ isEditing ? 'Update Catalog' : 'Add to Catalog' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.products-container { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-actions { display: flex; gap: 12px; }

/* Filter Drawer Styles */
.btn-filter { background: transparent; border: 1px solid #444; color: #888; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.btn-filter.active { background: #34495e; border-color: #42b883; color: #fff; }

.filter-drawer { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; margin-bottom: 2rem; }
.filter-grid { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
.filter-input { background: #222; border: 1px solid #444; color: #eee; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; }

.main-search { flex: 1; min-width: 250px; }
.slider-group { flex: 1; min-width: 250px; }

/* Double-Knob Logic [cite: 2026-03-03] */
.multi-range-container { position: relative; width: calc(95% + 9px); margin-left: -2px; height: 32px; display: flex; align-items: center; }
.range-input { position: absolute; width: 100%; pointer-events: none; appearance: none; background: none; z-index: 2; }
.range-input::-webkit-slider-thumb { pointer-events: auto; appearance: none; width: 18px; height: 18px; background: #42b883; border-radius: 50%; border: 2px solid #1a1a1a; cursor: pointer; }
.min-input { z-index: 3; }
.slider-track { position: absolute; width: 95%; height: 6px; background: #333; border-radius: 5px; z-index: 1; left: 18px; right: 0px;}

.btn-reset { background: transparent; border: 1px solid #444; color: #666; padding: 8px 16px; border-radius: 6px; cursor: pointer; height: 38px; }

/* Table Styles */
.table-wrapper { background: #111; border-radius: 12px; border: 1px solid #222; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; color: #42b883; text-align: left; padding: 14px; font-size: 0.75rem; text-transform: uppercase; }
td { padding: 14px; border-bottom: 1px solid #222; }
.product-row:hover { background-color: #161616; }
.bold { font-weight: bold; }

/* Hover Actions */
.action-buttons { opacity: 0; transition: 0.2s; display: flex; gap: 8px; justify-content: flex-end; }
.product-row:hover .action-buttons { opacity: 1; }

.btn-toggle { background: #42b883; color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }
.btn-edit { background: transparent; border: 1px solid #444; color: #888; padding: 5px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-delete { background: #ff4757; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }

/* Transitions & Modals */
.drawer-enter-active { transition: all 0.2s cubic-bezier(0, 0, 0.2, 1); max-height: 200px; overflow: hidden; }
.drawer-leave-active {transition: all 0.15s cubic-bezier(0.4, 0, 1, 1); max-height: 250px; overflow: hidden; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; max-height: 0; transform: translateY(-8px) scale(0.98); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #1a1a1a; border: 1px solid #333; border-radius: 16px; border-left: 4px solid #42b883; padding: 32px; width: 600px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr 100px 100px; gap: 12px; margin: 20px 0; }
input, select { background: #222; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 8px; }
.btn-save { width: 100%; background: #42b883; color: #000; font-weight: 800; padding: 12px; border: none; border-radius: 8px; cursor: pointer; }
/* Unified Table Header Logic [cite: 2026-03-03] */
th { 
  background: #1a1a1a; 
  color: #42b883; 
  text-align: left; 
  padding: 12px 14px; 
  font-size: 0.75rem; 
  text-transform: uppercase; 
  border-bottom: 2px solid #222; 
  transition: 0.2s; /* Standard smooth transition for the suite [cite: 2026-03-03] */
}

/* Hover Effect for Sortable Headers [cite: 2026-03-03] */
th.sortable {
  cursor: pointer;
  user-select: none;
}

th.sortable:hover { 
  background: #222; 
  color: #fff; /* Highlights text to white on hover [cite: 2026-03-03] */
}

/* Ensure the actions header doesn't highlight if not sortable [cite: 2026-03-03] */
.actions-header {
  cursor: default;
}
</style>