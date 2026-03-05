<script setup>
import { ref, onMounted, computed } from 'vue'

const categories = ref([])
const loading = ref(true)
const showModal = ref(false)
const showFilters = ref(false) // Toggle for snappy drawer [cite: 2026-03-03]
const isEditing = ref(false)
const currentCategoryId = ref(null)

// --- Filter State ---
const searchQuery = ref('')
const sortKey = ref('name')
const sortAsc = ref(true)

// --- Form State ---
const categoryName = ref('')
const categoryAlpha = ref(null)

const fetchCategories = async () => {
  loading.value = true
  try {
    const response = await fetch("http://127.0.0.1:8000/categories/")
    const data = await response.json()
    categories.value = data.categories || []
  } catch (err) { console.error(err) } finally { loading.value = false }
}

// --- Sorting & Filtering Logic [cite: 2026-03-03] ---
const filteredCategories = computed(() => {
  let data = [...categories.value]
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    data = data.filter(c => c.name.toLowerCase().includes(q) || String(c.category_id).includes(q))
  }
  return data.sort((a, b) => {
    let valA = a[sortKey.value]
    let valB = b[sortKey.value]
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    if (valA < valB) return sortAsc.value ? -1 : 1
    return sortAsc.value ? 1 : -1
  })
})

const sortBy = (key) => {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else { sortKey.value = key; sortAsc.value = true }
}

// --- CRUD Methods ---
const openCreateModal = () => {
  isEditing.value = false; currentCategoryId.value = null; categoryName.value = ''; categoryAlpha.value = null; showModal.value = true
}

const openEditModal = (cat) => {
  isEditing.value = true; currentCategoryId.value = cat.category_id; categoryName.value = cat.name; categoryAlpha.value = cat.ema_alpha; showModal.value = true
}

const saveCategory = async () => {
  if (!categoryName.value) return alert("Name is required.")
  const url = isEditing.value ? `http://127.0.0.1:8000/categories/${currentCategoryId.value}` : 'http://127.0.0.1:8000/categories/'
  const payload = { name: categoryName.value, ema_alpha: categoryAlpha.value === "" ? null : categoryAlpha.value }
  try {
    const res = await fetch(url, { method: isEditing.value ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (res.ok) { showModal.value = false; await fetchCategories() }
  } catch (err) { console.error(err) }
}

const deleteCategory = async (id) => {
  if (!confirm("Delete category? (Fails if roles are linked)")) return
  try {
    const res = await fetch(`http://127.0.0.1:8000/categories/${id}`, { method: 'DELETE' })
    if (res.ok) await fetchCategories()
    else alert((await res.json()).detail)
  } catch (err) { console.error(err) }
}

onMounted(fetchCategories)
</script>

<template>
  <div class="categories-container">
    <header class="view-header">
      <h1>Category Management</h1>
      <div class="header-actions">
        <button @click="showFilters = !showFilters" class="btn-filter" :class="{ active: showFilters }">🔍 Filter</button>
        <button @click="openCreateModal" class="btn-toggle">+ New Category</button>
      </div>
    </header>

    <transition name="drawer">
      <div v-if="showFilters" class="filter-drawer">
        <div class="filter-grid">
          <div class="filter-group main-search">
            <label>Search Categories</label>
            <input v-model="searchQuery" placeholder="Filter by name or ID..." class="filter-input" />
          </div>
          <button @click="searchQuery=''" class="btn-reset">Reset</button>
        </div>
      </div>
    </transition>

    <div class="table-wrapper">
      <table v-if="!loading">
        <thead>
          <tr>
            <th @click="sortBy('category_id')" class="sortable col-id">ID <span v-if="sortKey === 'category_id'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('name')" class="sortable col-name">Category Name <span v-if="sortKey === 'name'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('ema_alpha')" class="sortable col-alpha">EMA Alpha <span v-if="sortKey === 'ema_alpha'">{{ sortAsc ? '▲' : '▼' }}</span></th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in filteredCategories" :key="c.category_id" class="unified-row">
            <td class="mono-text">{{ c.category_id }}</td>
            <td class="bold">{{ c.name }}</td>
            <td>
              <span v-if="c.ema_alpha !== null" class="alpha-text">{{ c.ema_alpha.toFixed(2) }}</span>
              <span v-else class="global-text">Default</span>
            </td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit-icon" @click="openEditModal(c)">Edit</button>
                <button class="btn-delete-icon" @click="deleteCategory(c.category_id)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Category' : 'Add Category' }}</h3>
          <button @click="showModal = false" class="close-x-circle">&times;</button>
        </div>
        <div class="form-grid">
          <div class="input-group">
            <label>Category Name</label>
            <input v-model="categoryName" placeholder="e.g. Cleansers, Serums..." />
          </div>
          <div class="input-group">
            <label>EMA Alpha Override (0.0 - 1.0)</label>
            <input v-model.number="categoryAlpha" type="number" step="0.01" placeholder="Leave blank for Global Default" @keyup.enter="saveCategory" />
          </div>
          <button @click="saveCategory" class="btn-save">{{ isEditing ? 'Update Category' : 'Save Category' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.categories-container { max-width: 1400px; margin: 0 auto; padding: 40px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-actions { display: flex; align-items: center; gap: 12px; }

/* Filter Drawer Style [cite: 2026-03-03] */
.filter-drawer { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 24px; margin-bottom: 2rem; overflow: hidden; }
.filter-grid { display: flex; align-items: flex-end; gap: 24px; }
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-group label { font-size: 0.65rem; color: #666; font-weight: 800; text-transform: uppercase; }
.filter-input { background: #222; border: 1px solid #444; color: #eee; padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; width: 250px; }
.btn-reset { background: transparent; border: 1px solid #444; color: #666; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 700; transition: 0.2s; }

/* Snappy Animation [cite: 2026-03-03] */
.drawer-enter-active { transition: all 0.2s cubic-bezier(0, 0, 0.2, 1); max-height: 200px; }
.drawer-leave-active { transition: all 0.15s cubic-bezier(0.4, 0, 1, 1); max-height: 200px; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; max-height: 0; transform: translateY(-8px) scale(0.98); }

/* Table Columns [cite: 2026-03-03] */
.col-id { width: 80px; }
.col-name { width: auto; }
.col-alpha { width: 120px; }
.col-actions { width: 160px; text-align: right; }

.table-wrapper { background: #111; border-radius: 12px; border: 1px solid #222; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; color: #42b883; text-align: left; padding: 12px 14px; font-size: 0.75rem; text-transform: uppercase; border-bottom: 2px solid #222; transition: 0.2s; }
th.sortable:hover { background: #222; cursor: pointer; color: #fff; }

/* Standard Density [cite: 2026-03-03] */
.unified-row { height: 56px; } 
td { padding: 6px 14px; border-bottom: 1px solid #222; vertical-align: middle; }
.unified-row:hover { background: #161616; }

/* Actions [cite: 2026-03-03] */
.action-buttons { opacity: 0; transition: 0.2s; display: flex; gap: 8px; justify-content: flex-end; }
.unified-row:hover .action-buttons { opacity: 1; }

/* Text Logic [cite: 2026-03-03] */
.global-text { color: #555; font-size: 0.7rem; font-style: italic; text-transform: uppercase; letter-spacing: 0.5px; }
.mono-text { font-family: 'JetBrains Mono', monospace; color: #555; font-size: 0.85rem; }

/* Edit/Delete & Modal [cite: 2026-03-03] */
.btn-edit-icon { background: transparent; border: 1px solid #444; color: #888; padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.btn-delete-icon { background: #ff4757; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }

/* Inherits base modal styles from global CSS */
.modal-content { 
  border-left: 4px solid #42b883; 
  width: 450px; 
}

.form-grid { display: grid; gap: 15px; }
.input-group label { font-size: 0.7rem; text-transform: uppercase; color: #888; font-weight: bold; margin-bottom: 5px; display: block; }
input { background: #222; border: 1px solid #333; color: white; padding: 10px; border-radius: 8px; width: 100%; }
.btn-save { width: 100%; padding: 12px; background: #42b883; border: none; border-radius: 8px; color: #000; cursor: pointer; font-weight: 800; }
</style>