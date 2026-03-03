<script setup>
import { ref, onMounted, computed } from 'vue'

const roles = ref([]); const products = ref([]); const history = ref([]); const categories = ref([])
const loading = ref(true)

// --- UI Toggles & Search ---
const showDefinitions = ref(false); const showRoleModal = ref(false)   
const showSwapModal = ref(false); const showHistoryModal = ref(false)
const showFilters = ref(false) 

// --- Filter State ---
const roleSearchQuery = ref(''); const filterCategory = ref('all')
const minBuffer = ref(0); const maxBuffer = ref(30); const absMaxBuffer = ref(30)

// --- Sorting State ---
const sortKey = ref('name'); const sortAsc = ref(true)

// --- Form State ---
const isEditingRole = ref(false); const currentRoleId = ref(null)
const roleName = ref(''); const bufferDays = ref(7); const selectedCategory = ref('')
const roleAlpha = ref(null)
const activeRoleForSwap = ref(null); const searchQuery = ref(''); const showDropdown = ref(false)
const selectedProduct = ref(null); const startDate = ref(new Date().toISOString().split('T')[0])

const fetchData = async () => {
  loading.value = true
  try {
    const [rRes, pRes, hRes, cRes] = await Promise.all([
      fetch('http://127.0.0.1:8000/roles/'), fetch('http://127.0.0.1:8000/products/'),
      fetch('http://127.0.0.1:8000/role-history/'), fetch('http://127.0.0.1:8000/categories/')
    ])
    roles.value = (await rRes.json()).roles || []
    products.value = (await pRes.json()).inventory || []
    history.value = (await hRes.json()).role_history || []
    categories.value = (await cRes.json()).categories || []
    
    if (roles.value.length > 0) {
      const buffers = roles.value.map(r => r.target_buffer_days)
      absMaxBuffer.value = Math.max(...buffers, 30); maxBuffer.value = absMaxBuffer.value
    }
  } catch (err) { console.error(err) } finally { loading.value = false }
}

const handleMin = () => { if (minBuffer.value > maxBuffer.value) minBuffer.value = maxBuffer.value }
const handleMax = () => { if (maxBuffer.value < minBuffer.value) maxBuffer.value = minBuffer.value }

const routineStatus = computed(() => {
  return roles.value.map(role => {
    const activeEntry = history.value.find(h => h.role_id === role.role_id && !h.end_date)
    return { ...role, activeProduct: activeEntry || null }
  })
})

const getSortValue = (obj, key) => {
  if (key === 'product_name') return obj.activeProduct ? `${obj.activeProduct.brand} ${obj.activeProduct.product_name}` : ''
  if (key === 'start_date') return obj.activeProduct ? obj.activeProduct.start_date : ''
  if (key === 'ema_alpha') return obj.ema_alpha === null ? -1 : obj.ema_alpha
  return obj[key]
}

const applySortAndFilter = (dataArray) => {
  let data = [...dataArray]
  if (roleSearchQuery.value) {
    const q = roleSearchQuery.value.toLowerCase()
    data = data.filter(r => r.name.toLowerCase().includes(q) || r.category_name.toLowerCase().includes(q))
  }
  if (filterCategory.value !== 'all') {
    data = data.filter(r => r.category_id === Number(filterCategory.value))
  }
  data = data.filter(r => r.target_buffer_days >= minBuffer.value && r.target_buffer_days <= maxBuffer.value)
  return data.sort((a, b) => {
    let valA = getSortValue(a, sortKey.value); let valB = getSortValue(b, sortKey.value)
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (valA < valB) return sortAsc.value ? -1 : 1
    return sortAsc.value ? 1 : -1
  })
}

const displayRoutine = computed(() => applySortAndFilter(routineStatus.value))
const displayRoles = computed(() => applySortAndFilter(roles.value))

const sortBy = (key) => {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else { sortKey.value = key; sortAsc.value = true }
}

onMounted(fetchData)
</script>

<template>
  <div class="roles-command-center">
    <header class="view-header">
      <div class="title-group">
        <h1>{{ showDefinitions ? 'Role Definitions' : 'Active Routine' }}</h1>
        <button @click="showDefinitions = !showDefinitions" class="btn-subtle">
          Manage {{ showDefinitions ? 'Active Routine' : 'Role Definitions' }}
        </button>
      </div>
      <div class="header-actions">
        <button @click="showFilters = !showFilters" class="btn-filter" :class="{ active: showFilters }">🔍 Filter</button>
        <button @click="openCreateRole" class="btn-toggle">+ New Role</button>
      </div>
    </header>

    <transition name="drawer">
      <div v-if="showFilters" class="filter-drawer">
        <div class="filter-grid">
          <div class="filter-group main-search">
            <label>Search Roles</label>
            <input v-model="roleSearchQuery" placeholder="Filter by name..." class="filter-input" />
          </div>
          <div class="filter-group slider-group">
            <label>Buffer Range: {{ minBuffer }}d - {{ maxBuffer }}d</label>
            <div class="multi-range-container">
              <input type="range" v-model.number="minBuffer" :min="0" :max="absMaxBuffer" @input="handleMin" class="range-input min-input" />
              <input type="range" v-model.number="maxBuffer" :min="0" :max="absMaxBuffer" @input="handleMax" class="range-input max-input" />
              <div class="slider-track"></div>
            </div>
          </div>
          <div class="filter-group">
            <label>Category</label>
            <select v-model="filterCategory" class="filter-input">
              <option value="all">All Categories</option>
              <option v-for="c in categories" :key="c.category_id" :value="c.category_id">{{ c.name }}</option>
            </select>
          </div>
          <button @click="roleSearchQuery=''; filterCategory='all'; minBuffer=0; maxBuffer=absMaxBuffer" class="btn-reset">Reset</button>
        </div>
      </div>
    </transition>

    <div class="table-wrapper">
      <table v-if="!loading">
        <thead>
          <tr v-if="!showDefinitions">
            <th @click="sortBy('name')" class="sortable col-role">Role <span v-if="sortKey === 'name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('category_name')" class="sortable col-cat">Category <span v-if="sortKey === 'category_name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('target_buffer_days')" class="sortable col-buffer">Buffer <span v-if="sortKey === 'target_buffer_days'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('product_name')" class="sortable col-product">Current Product <span v-if="sortKey === 'product_name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('start_date')" class="sortable col-date">Started <span v-if="sortKey === 'start_date'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th class="col-actions"></th>
          </tr>
          <tr v-else>
            <th @click="sortBy('name')" class="sortable col-role">Name <span v-if="sortKey === 'name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('category_name')" class="sortable col-cat">Category <span v-if="sortKey === 'category_name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('target_buffer_days')" class="sortable col-buffer">Buffer <span v-if="sortKey === 'target_buffer_days'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('ema_alpha')" class="sortable col-alpha">Alpha <span v-if="sortKey === 'ema_alpha'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in (showDefinitions ? displayRoles : displayRoutine)" :key="role.role_id" class="unified-row">
            <td class="bold clickable" @click="openHistory(role)">{{ role.name }}</td>
            <td><span class="cat-tag">{{ role.category_name }}</span></td>
            <td class="mono-text">{{ role.target_buffer_days }}d</td>
            <template v-if="!showDefinitions">
              <td class="prod-cell">
                <div v-if="role.activeProduct" class="product-wrap">
                  <span class="brand-text">{{ role.activeProduct.brand }}</span>
                  <span class="prod-sub">{{ role.activeProduct.product_name }}</span>
                </div>
                <span v-else class="empty-text">Not Assigned</span>
              </td>
              <td class="date-text">{{ role.activeProduct?.start_date || '-' }}</td>
              <td class="actions-cell"><button class="btn-swap-mini" @click="openSwapModal(role)">Swap Product</button></td>
            </template>
            <template v-else>
              <td>
                <span v-if="role.ema_alpha !== null" class="alpha-text">{{ role.ema_alpha.toFixed(2) }}</span>
                <span v-else class="global-text">Default</span>
              </td>
              <td class="actions-cell">
                <div class="action-buttons">
                  <button class="btn-edit" @click="openEditRole(role)">Edit</button>
                  <button class="btn-delete" @click="deleteRole(role.role_id)">Delete</button>
                </div>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.roles-command-center { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.title-group { display: flex; align-items: center; gap: 24px; }
.header-actions { display: flex; align-items: center; gap: 12px; }

.btn-filter { background: transparent; border: 1px solid #444; color: #888; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px; transition: 0.2s; }
.btn-filter.active { background: #34495e; border-color: #42b883; color: #fff; }
.btn-toggle { background: #42b883; color: #000 !important; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 800; cursor: pointer; }

.filter-drawer { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; margin-bottom: 2rem; overflow: hidden; }
.filter-grid { display: flex; flex-direction: row; flex-wrap: wrap; gap: 32px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
.filter-input { background: #222; border: 1px solid #444; color: #eee; padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; width: 220px; }
.btn-reset { background: transparent; border: 1px solid #444; color: #666; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 700; transition: 0.2s; }

/* Snappy Drawer Animation [cite: 2026-03-03] */
.drawer-enter-active { transition: all 0.2s cubic-bezier(0, 0, 0.2, 1); max-height: 500px; }
.drawer-leave-active { transition: all 0.15s cubic-bezier(0.4, 0, 1, 1); max-height: 500px; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; max-height: 0; transform: translateY(-8px) scale(0.98); }

.table-wrapper { background: #111; border-radius: 12px; border: 1px solid #222; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; color: #42b883; text-align: left; padding: 12px 14px; font-size: 0.75rem; text-transform: uppercase; border-bottom: 2px solid #222; transition: 0.2s; }
th.sortable:hover { background: #222; cursor: pointer; color: #fff; }

.unified-row { height: 56px; } 
td { padding: 6px 14px; border-bottom: 1px solid #222; vertical-align: middle; }

.col-role { width: 18%; }
.col-cat { width: 12%; }
.col-buffer { width: 80px; text-align: center !important; }
.col-product { width: auto; }
.col-date { width: 110px; }
.col-actions { width: 140px; text-align: right; }

.product-wrap { display: flex; flex-direction: column; line-height: 1.2; white-space: normal; }
.brand-text { color: #42b883; font-weight: 800; font-size: 0.85rem; }
.prod-sub { color: #eee; font-weight: 400; font-size: 0.75rem; }
.mono-text { text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #888; }

.btn-swap-mini { opacity: 0; transition: 0.2s; background: transparent; border: 1px solid #444; color: #888; padding: 6px 12px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; cursor: pointer; }
.unified-row:hover .btn-swap-mini { opacity: 1; }
.btn-swap-mini:hover { border-color: #42b883; color: #42b883; }

.action-buttons { opacity: 0; transition: 0.2s; display: flex; gap: 8px; justify-content: flex-end; }
.unified-row:hover .action-buttons { opacity: 1; }
.btn-subtle { background: transparent; color: #888; border: 1px solid #333; padding: 8px 14px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-edit { background: transparent; border: 1px solid #444; color: #888; padding: 5px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-delete { background: #ff4757; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
/* Styling for fallback/default values [cite: 2026-03-03] */
.global-text { 
  color: #555; /* Muted grey [cite: 2026-03-03] */
  font-size: 0.7rem; /* Significantly smaller [cite: 2026-03-03] */
  font-style: italic; 
  text-transform: uppercase; /* Adds to the mechanical, pro-tool aesthetic [cite: 2026-03-03] */
  letter-spacing: 0.5px;
}
</style>