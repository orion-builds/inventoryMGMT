<script setup>
import { ref, onMounted, computed } from 'vue'

const roles = ref([]); const products = ref([]); const history = ref([]); const categories = ref([])
const loading = ref(true)

// UI Toggles
const showDefinitions = ref(false) 
const showRoleModal = ref(false)   
const showSwapModal = ref(false)   
const showHistoryModal = ref(false)

// Form State (Definitions)
const isEditingRole = ref(false); const currentRoleId = ref(null)
const roleName = ref(''); const bufferDays = ref(7); const selectedCategory = ref('')

// Form State (Assignments/Swap)
const activeRoleForSwap = ref(null); const searchQuery = ref(''); const showDropdown = ref(false)
const selectedProduct = ref(null); const startDate = ref(new Date().toISOString().split('T')[0])

// History Pop-up & Edit State
const selectedRoleForHistory = ref(null)
const isEditingHistory = ref(false)
const historyEntryToEdit = ref(null)
const editHistoryStartDate = ref('') // Added for start date editing
const editHistoryEndDate = ref('')

const fetchData = async () => {
  loading.value = true
  try {
    const [rRes, pRes, hRes, cRes] = await Promise.all([
      fetch('http://127.0.0.1:8000/roles/'),
      fetch('http://127.0.0.1:8000/products/'),
      fetch('http://127.0.0.1:8000/role-history/'),
      fetch('http://127.0.0.1:8000/categories/')
    ])
    roles.value = (await rRes.json()).roles || []
    products.value = (await pRes.json()).inventory || []
    history.value = (await hRes.json()).role_history || []
    categories.value = (await cRes.json()).categories || []
  } catch (err) { console.error(err) } finally { loading.value = false }
}

const routineStatus = computed(() => {
  return roles.value.map(role => {
    const activeEntry = history.value.find(h => h.role_id === role.role_id && !h.end_date)
    return { ...role, activeProduct: activeEntry || null }
  })
})

const roleSpecificHistory = computed(() => {
  if (!selectedRoleForHistory.value) return []
  return history.value.filter(h => h.role_id === selectedRoleForHistory.value.role_id)
})

// --- ROLE HISTORY METHODS ---
const openHistory = (role) => {
  selectedRoleForHistory.value = role
  showHistoryModal.value = true
  isEditingHistory.value = false
}

const startEditHistory = (h) => {
  isEditingHistory.value = true
  historyEntryToEdit.value = h
  editHistoryStartDate.value = h.start_date // Populate current start date
  editHistoryEndDate.value = h.end_date || ''
}

const saveHistoryEdit = async () => {
  // Identify the row using the ORIGINAL composite key values
  const params = new URLSearchParams({
    role_id: historyEntryToEdit.value.role_id,
    product_id: historyEntryToEdit.value.product_id,
    start_date: historyEntryToEdit.value.start_date 
  })

  try {
    const res = await fetch(`http://127.0.0.1:8000/role-history/?${params}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        start_date: editHistoryStartDate.value, // New start date
        end_date: editHistoryEndDate.value || null 
      })
    })
    if (res.ok) {
      isEditingHistory.value = false
      await fetchData()
    }
  } catch (err) { console.error("Update failed:", err) }
}

const deleteHistoryEntry = async (h) => {
  if (!confirm("Delete this history record? This cannot be undone.")) return
  const params = new URLSearchParams({
    role_id: h.role_id, product_id: h.product_id, start_date: h.start_date
  })
  try {
    const res = await fetch(`http://127.0.0.1:8000/role-history/?${params}`, { method: 'DELETE' })
    if (res.ok) await fetchData()
  } catch (err) { console.error("Delete failed:", err) }
}

// --- ROLE DEFINITION METHODS ---
const openCreateRole = () => {
  isEditingRole.value = false; roleName.value = ''; bufferDays.value = 7; selectedCategory.value = ''; showRoleModal.value = true
}
const openEditRole = (role) => {
  isEditingRole.value = true; currentRoleId.value = role.role_id
  roleName.value = role.name; bufferDays.value = role.target_buffer_days; selectedCategory.value = role.category_id
  showRoleModal.value = true
}
const saveRoleDefinition = async () => {
  const method = isEditingRole.value ? 'PATCH' : 'POST'
  const url = isEditingRole.value ? `http://127.0.0.1:8000/roles/${currentRoleId.value}` : 'http://127.0.0.1:8000/roles/'
  await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: roleName.value, target_buffer_days: bufferDays.value, category_id: selectedCategory.value }) })
  showRoleModal.value = false; await fetchData()
}
const deleteRole = async (id) => {
  if (!confirm("Delete this role?")) return
  await fetch(`http://127.0.0.1:8000/roles/${id}`, { method: 'DELETE' })
  await fetchData()
}

// --- ASSIGNMENT / SWAP METHODS ---
const openSwapModal = (role) => { activeRoleForSwap.value = role; searchQuery.value = ''; selectedProduct.value = null; showSwapModal.value = true }
const confirmSwap = async () => {
  await fetch('http://127.0.0.1:8000/role-history/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role_id: activeRoleForSwap.value.role_id, product_id: selectedProduct.value.product_id, start_date: startDate.value, end_date: null }) })
  showSwapModal.value = false; await fetchData()
}

const filteredProducts = computed(() => {
  if (!searchQuery.value) return []
  return products.value.filter(p => p.brand.toLowerCase().includes(searchQuery.value.toLowerCase()) || p.name.toLowerCase().includes(searchQuery.value.toLowerCase())).slice(0, 5)
})

onMounted(fetchData)
</script>

<template>
  <div class="roles-command-center">
    <header class="view-header">
      <h1>{{ showDefinitions ? 'Role Definitions' : 'Active Routine' }}</h1>
      <div class="header-btns">
        <button @click="showDefinitions = !showDefinitions" class="btn-secondary">
          {{ showDefinitions ? 'Manage Active Roles' : 'Manage Role Definitions' }}
        </button>
        <button v-if="showDefinitions" @click="openCreateRole" class="btn-toggle">+ New Role</button>
      </div>
    </header>

    <div v-if="!loading">
      <section v-if="!showDefinitions" class="routine-section">
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Role</th><th>Category</th><th>Current Product</th><th>Started</th><th class="actions-header"></th></tr>
            </thead>
            <tbody>
              <tr v-for="role in routineStatus" :key="role.role_id" class="routine-row">
                <td class="bold clickable" @click="openHistory(role)">{{ role.name }}</td>
                <td><span class="cat-tag">{{ role.category_name }}</span></td>
                <td>
                  <template v-if="role.activeProduct">
                    <span class="brand-text">{{ role.activeProduct.brand }}</span> {{ role.activeProduct.product_name }}
                  </template>
                  <span v-else class="empty-text">Not Assigned</span>
                </td>
                <td class="date-text">{{ role.activeProduct?.start_date || '-' }}</td>
                <td class="actions-cell">
                  <div class="action-buttons">
                    <button class="btn-swap-hover" @click="openSwapModal(role)">Swap Product</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="definitions-section">
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Name</th><th>Category</th><th>Buffer</th><th class="actions-header"></th></tr>
            </thead>
            <tbody>
              <tr v-for="r in roles" :key="r.role_id" class="role-row">
                <td class="bold clickable" @click="openHistory(r)">{{ r.name }}</td>
                <td><span class="cat-tag">{{ r.category_name }}</span></td>
                <td>{{ r.target_buffer_days }}d</td>
                <td class="actions-cell">
                  <div class="action-buttons">
                    <button class="btn-edit" @click="openEditRole(r)">Edit</button>
                    <button class="btn-delete" @click="deleteRole(r.role_id)">Delete</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="showRoleModal" class="modal-overlay" @click.self="showRoleModal = false">
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>{{ isEditingRole ? 'Edit Role' : 'Create Role' }}</h3>
          <button @click="showRoleModal = false" class="close-x">&times;</button>
        </div>
        <div class="form-grid">
          <input v-model="roleName" placeholder="Role Name" />
          <select v-model="selectedCategory">
            <option v-for="c in categories" :key="c.category_id" :value="c.category_id">{{ c.name }}</option>
          </select>
          <input v-model.number="bufferDays" type="number" />
          <button @click="saveRoleDefinition" class="btn-save">Save Definition</button>
        </div>
      </div>
    </div>

    <div v-if="showSwapModal" class="modal-overlay" @click.self="showSwapModal = false">
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>Swap for {{ activeRoleForSwap?.name }}</h3>
          <button @click="showSwapModal = false" class="close-x">&times;</button>
        </div>
        <div class="form-grid">
          <div class="search-container">
            <input v-model="searchQuery" @focus="showDropdown = true" placeholder="Search products..." />
            <div v-if="showDropdown && filteredProducts.length" class="results-dropdown">
              <div v-for="p in filteredProducts" :key="p.product_id" @click="selectedProduct = p; searchQuery = `${p.brand} - ${p.name}`; showDropdown = false" class="result-item">
                <strong>{{ p.brand }}</strong> - {{ p.name }}
              </div>
            </div>
          </div>
          <input v-model="startDate" type="date" />
          <button @click="confirmSwap" class="btn-save">Confirm Swap</button>
        </div>
      </div>
    </div>

    <div v-if="showHistoryModal" class="modal-overlay" @click.self="showHistoryModal = false; isEditingHistory = false">
      <div class="modal-content history-modal">
        <div class="modal-header">
          <h3>History: {{ selectedRoleForHistory?.name }}</h3>
          <button @click="showHistoryModal = false; isEditingHistory = false" class="close-x">&times;</button>
        </div>

        <div v-if="isEditingHistory" class="inline-edit-box">
          <h4>Editing Entry: {{ historyEntryToEdit?.product_name }}</h4>
          <div class="edit-grid">
            <div class="input-group">
              <label>Start Date</label>
              <input v-model="editHistoryStartDate" type="date" />
            </div>
            <div class="input-group">
              <label>End Date</label>
              <input v-model="editHistoryEndDate" type="date" />
            </div>
            <div class="btn-group">
              <button @click="saveHistoryEdit" class="btn-save mini">Update Dates</button>
              <button @click="isEditingHistory = false" class="btn-secondary mini">Cancel</button>
            </div>
          </div>
        </div>

        <div class="table-wrapper mini-table">
          <table v-if="roleSpecificHistory.length > 0">
            <thead>
              <tr><th>Product</th><th>Start</th><th>End</th><th class="actions-header"></th></tr>
            </thead>
            <tbody>
              <tr v-for="h in roleSpecificHistory" :key="`${h.product_id}-${h.start_date}`" class="history-row-mini">
                <td><strong>{{ h.brand }}</strong> {{ h.product_name }}</td>
                <td class="date-text">{{ h.start_date }}</td>
                <td class="date-text">{{ h.end_date || 'Current' }}</td>
                <td class="actions-cell-mini">
                  <div class="action-buttons-mini">
                    <button class="btn-edit" @click="startEditHistory(h)">Edit</button>
                    <button class="btn-delete" @click="deleteHistoryEntry(h)">Delete</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="status-msg">No previous products logged for this role.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scannable Table Aesthetic */
.table-wrapper { background: #222; border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #2c3e50; color: var(--primary-green); text-align: left; padding: 12px; font-size: 0.85rem; text-transform: uppercase; }
td { padding: 12px; border-bottom: 1px solid #333; }
.bold { font-weight: bold; }

/* Clickable Roles */
.clickable { color: var(--primary-green); cursor: pointer; text-decoration: underline rgba(66, 184, 131, 0); transition: 0.2s; }
.clickable:hover { text-decoration-color: var(--primary-green); }

.cat-tag { background: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; color: #aaa; }
.brand-text { color: var(--primary-green); font-weight: bold; }
.empty-text { color: #555; font-style: italic; }
.date-text { font-family: monospace; color: #888; font-size: 0.8rem; }

/* Hover Action Reveal */
.routine-row .action-buttons, .role-row .action-buttons, .history-row-mini .action-buttons-mini {
  opacity: 0; transition: opacity 0.2s ease-in-out; display: flex; gap: 8px; justify-content: flex-end;
}
.routine-row:hover .action-buttons, .role-row:hover .action-buttons, .history-row-mini:hover .action-buttons-mini { opacity: 1; }
.routine-row:hover, .role-row:hover, .history-row-mini:hover { background-color: #2a2a2a; }

/* Button Styles */
.btn-swap-hover {
  background: transparent; border: 1px solid var(--primary-green); color: var(--primary-green);
  padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; font-weight: bold;
}
.btn-swap-hover:hover { background: var(--primary-green); color: white; }

.btn-edit { background: transparent; border: 1px solid #888; color: #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; }
.btn-edit:hover { border-color: var(--primary-green); color: var(--primary-green); }

.btn-delete { background: #e74c3c; border: none; color: white; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; font-weight: bold; }
.btn-delete:hover { background: #c0392b; }

.actions-cell { width: 160px; padding-right: 15px; }
.actions-cell-mini { width: 150px; padding-right: 10px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-btns { display: flex; gap: 10px; }
.btn-secondary { background: transparent; border: 1px solid #555; color: #aaa; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-secondary:hover { border-color: var(--primary-green); color: white; }

/* Modals & Forms */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(4px); }
.modal-content { background: #252525; padding: 30px; border-radius: 8px; border-left: 4px solid var(--primary-green); width: 450px; }
.history-modal { width: 95%; max-width: 750px; }
.mini-table { margin-top: 15px; max-height: 400px; overflow-y: auto; }
.close-x { background: none; border: none; color: #888; font-size: 1.5rem; cursor: pointer; }

/* Inline Edit Box Styling */
.inline-edit-box { background: #1a1a1a; padding: 15px; border-radius: 6px; border: 1px solid #333; margin-bottom: 20px; border-left: 3px solid var(--primary-green); }
.inline-edit-box h4 { margin-top: 0; font-size: 0.9rem; color: var(--primary-green); }
.edit-grid { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-end; }
.input-group { display: flex; flex-direction: column; gap: 5px; }
.input-group label { font-size: 0.7rem; text-transform: uppercase; color: #888; font-weight: bold; }
.btn-group { display: flex; gap: 8px; }
.btn-save.mini, .btn-secondary.mini { padding: 6px 12px; height: 35px; margin: 0; }
</style>