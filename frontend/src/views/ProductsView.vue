<script setup>
import { ref, onMounted, computed } from 'vue'

const products = ref([])
const loading = ref(true)
const showModal = ref(false)
const isEditing = ref(false)
const currentProductId = ref(null)

// Filter and Sort State
const searchQuery = ref('')
const sortKey = ref('brand'); const sortOrder = ref(1) 

// Form State
const brand = ref(''); const name = ref(''); const amount = ref(0); const unit = ref('ml')

const fetchProducts = async () => {
  loading.value = true
  try {
    const response = await fetch("http://127.0.0.1:8000/products/")
    const data = await response.json()
    products.value = data.inventory
  } catch (error) { console.error(error) } finally { loading.value = false }
}

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
  const url = isEditing.value 
    ? `http://127.0.0.1:8000/products/${currentProductId.value}` 
    : 'http://127.0.0.1:8000/products/'
    
  try {
    const response = await fetch(url, {
      method: isEditing.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (response.ok) {
      showModal.value = false; await fetchProducts()
    }
  } catch (err) { console.error("Save failed:", err) }
}

const deleteProduct = async (id) => {
  if (!confirm("Are you sure you want to delete this product?")) return
  try {
    const response = await fetch(`http://127.0.0.1:8000/products/${id}`, { method: 'DELETE' })
    if (response.ok) await fetchProducts()
    else alert((await response.json()).detail)
  } catch (err) { console.error(err) }
}

const filteredProducts = computed(() => {
  let result = [...products.value]
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => p.brand.toLowerCase().includes(query) || p.name.toLowerCase().includes(query))
  }
  result.sort((a, b) => {
    let valA = a[sortKey.value]; let valB = b[sortKey.value]
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    return valA < valB ? -1 * sortOrder.value : 1 * sortOrder.value
  })
  return result
})

const sortBy = (key) => {
  if (sortKey.value === key) sortOrder.value *= -1
  else { sortKey.value = key; sortOrder.value = 1 }
}

onMounted(fetchProducts)
</script>

<template>
  <div class="products-container">
    <header class="view-header">
      <h1>Product Management</h1>
      <div class="header-actions">
        <input v-model="searchQuery" placeholder="Filter products..." class="search-input" />
        <button @click="openCreateModal" class="btn-toggle">+ New Product</button>
      </div>
    </header>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content add-card">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Product' : 'Add to Catalog' }}</h3>
          <button @click="showModal = false" class="close-x">&times;</button>
        </div>
        <div class="form-grid">
          <input v-model="brand" placeholder="Brand" />
          <input v-model="name" placeholder="Product Name" />
          <input v-model.number="amount" type="number" placeholder="Size" />
          <select v-model="unit">
            <option value="ml">ml</option>
            <option value="g">g</option>
          </select>
        </div>
        <button @click="saveProduct" class="btn-save">
          {{ isEditing ? 'Update Product' : 'Save Product' }}
        </button>
      </div>
    </div>

    <div class="table-wrapper">
      <table v-if="!loading && filteredProducts.length > 0">
        <thead>
          <tr>
            <th @click="sortBy('brand')" class="sortable">Brand <span v-if="sortKey === 'brand'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('name')" class="sortable">Name <span v-if="sortKey === 'name'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th @click="sortBy('amount')" class="sortable">Size <span v-if="sortKey === 'amount'">{{ sortOrder === 1 ? '▲' : '▼' }}</span></th>
            <th>Unit</th>
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
      <p v-else class="status-msg">No products found.</p>
    </div>
  </div>
</template>

<style scoped>
/* Hover Reveal Logic */
.product-row .action-buttons {
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.product-row:hover .action-buttons { opacity: 1; }
.product-row:hover { background-color: #2a2a2a; }

/* Buttons */
.btn-edit {
  background: transparent;
  border: 1px solid #888;
  color: #ccc;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: bold;
}
.btn-edit:hover { border-color: var(--primary-green); color: var(--primary-green); }

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

/* Modal & Structure */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75); display: flex;
  justify-content: center; align-items: center; z-index: 100;
  backdrop-filter: blur(4px);
}
.modal-content {
  width: 90%; max-width: 600px; background: #252525;
  border-radius: 8px; border-left: 4px solid var(--primary-green);
  padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.close-x { background: none; border: none; color: #888; font-size: 2rem; cursor: pointer; }

.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.header-actions { display: flex; gap: 1rem; }
.search-input { width: 200px; }
.add-card { margin-bottom: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr 100px 100px; gap: 10px; margin: 15px 0; }
.table-wrapper { background: #222; border-radius: 8px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #2c3e50; color: var(--primary-green); text-align: left; padding: 12px; font-size: 0.85rem; text-transform: uppercase; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { background-color: #34495e; }
td { padding: 12px; border-bottom: 1px solid #333; }
.actions-cell { width: 150px; padding-right: 15px; }
.bold { font-weight: bold; }
.status-msg { padding: 40px; text-align: center; color: #888; }
.btn-save { width: 100%; margin-top: 10px; background-color: var(--primary-green); color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; cursor: pointer; }
</style>