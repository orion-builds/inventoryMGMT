<script setup>
import { ref, onMounted } from 'vue'

const categories = ref([])
const loading = ref(true)
const showModal = ref(false)
const isEditing = ref(false)
const currentCategoryId = ref(null)

// Form State
const categoryName = ref('')

const fetchCategories = async () => {
  loading.value = true
  try {
    const response = await fetch("http://127.0.0.1:8000/categories/")
    const data = await response.json()
    categories.value = data.categories || []
  } catch (err) { console.error(err) } finally { loading.value = false }
}

const openCreateModal = () => {
  isEditing.value = false
  currentCategoryId.value = null
  categoryName.value = ''
  showModal.value = true
}

const openEditModal = (cat) => {
  isEditing.value = true
  currentCategoryId.value = cat.category_id
  categoryName.value = cat.name
  showModal.value = true
}

const saveCategory = async () => {
  if (!categoryName.value) return alert("Name is required.")
  
  const url = isEditing.value 
    ? `http://127.0.0.1:8000/categories/${currentCategoryId.value}` 
    : 'http://127.0.0.1:8000/categories/'
    
  try {
    const response = await fetch(url, {
      method: isEditing.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: categoryName.value })
    })
    
    if (response.ok) {
      showModal.value = false
      await fetchCategories()
    }
  } catch (err) { console.error(err) }
}

const deleteCategory = async (id) => {
  if (!confirm("Delete this category? This will fail if roles are linked to it.")) return
  try {
    const response = await fetch(`http://127.0.0.1:8000/categories/${id}`, { method: 'DELETE' })
    if (response.ok) await fetchCategories()
    else alert((await response.json()).detail)
  } catch (err) { console.error(err) }
}

onMounted(fetchCategories)
</script>

<template>
  <div class="categories-container">
    <header class="view-header">
      <h1>Category Management</h1>
      <button @click="openCreateModal" class="btn-toggle">+ New Category</button>
    </header>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Category' : 'Add Category' }}</h3>
          <button @click="showModal = false" class="close-x">&times;</button>
        </div>
        <div class="form-grid">
          <div class="input-group">
            <label>Category Name</label>
            <input v-model="categoryName" placeholder="e.g. Cleansers, Serums..." @keyup.enter="saveCategory" />
          </div>
          <button @click="saveCategory" class="btn-save">
            {{ isEditing ? 'Update Category' : 'Save Category' }}
          </button>
        </div>
      </div>
    </div>

    <div class="table-wrapper">
      <table v-if="!loading && categories.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>Category Name</th>
            <th class="actions-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in categories" :key="c.category_id" class="category-row">
            <td>{{ c.category_id }}</td>
            <td class="bold">{{ c.name }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit" @click="openEditModal(c)">Edit</button>
                <button class="btn-delete" @click="deleteCategory(c.category_id)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loading" class="status-msg">Loading categories...</p>
      <p v-else class="status-msg">No categories found.</p>
    </div>
  </div>
</template>

<style scoped>
/* Table Formatting & Hover Logic */
th { 
  background: #2c3e50; 
  color: var(--primary-green); 
  text-align: left; 
  padding: 12px; 
  font-size: 0.85rem; 
  text-transform: uppercase; 
}

.category-row .action-buttons {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.category-row:hover .action-buttons { opacity: 1; }
.category-row:hover { background-color: #2a2a2a; }

/* Modal & Form Styles */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75); display: flex;
  justify-content: center; align-items: center; z-index: 100;
  backdrop-filter: blur(4px);
}
.modal-content {
  width: 90%; max-width: 400px; background: #252525;
  border-radius: 8px; border-left: 4px solid var(--primary-green);
  padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.input-group { display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; }
.input-group label { font-size: 0.7rem; color: #888; text-transform: uppercase; font-weight: bold; }

/* Shared Component Styles */
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.table-wrapper { background: #222; border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
td { padding: 12px; border-bottom: 1px solid #333; }
.actions-cell { width: 140px; padding-right: 15px; }
.bold { font-weight: bold; }
.btn-save { width: 100%; padding: 10px; background: var(--primary-green); border: none; border-radius: 4px; color: white; cursor: pointer; font-weight: bold; }
.close-x { background: none; border: none; color: #888; font-size: 1.5rem; cursor: pointer; }

.btn-edit { background: transparent; border: 1px solid #888; color: #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; }
.btn-edit:hover { border-color: var(--primary-green); color: var(--primary-green); }
.btn-delete { background: #e74c3c; border: none; color: white; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; font-weight: bold; }
.btn-delete:hover { background: #c0392b; }
</style>