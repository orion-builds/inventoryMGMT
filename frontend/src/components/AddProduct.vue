<script setup>
import { ref } from 'vue'

// 1. Reactive state: These variables sync with the input boxes
const brand = ref('')
const name = ref('')
const amount = ref(0)
const unit = ref('ml')

// 2. Define an "Emit": This is how a child component shouts to its parent
const emit = defineEmits(['product-added'])

const submitProduct = async () => {
  const newProduct = {
    brand: brand.value,
    name: name.value,
    amount: amount.value,
    unit_of_measure: unit.value
  }

  try {
    // 3. The Handshake: Sending data to your FastAPI backend
    const response = await fetch('http://127.0.0.1:8000/products/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProduct)
    })
    
    if (response.ok) {
      alert("Product saved to SQLite!")
      // 4. Clear the form
      brand.value = ''; name.value = ''; amount.value = 0
      // 5. Tell App.vue to refresh the list
      emit('product-added')
    }
  } catch (err) {
    console.error("Failed to save product:", err)
  }
}
</script>

<template>
  <section class="add-form">
    <h3>Add New Item</h3>
    <input v-model="brand" placeholder="Brand (e.g., CeraVe)">
    <input v-model="name" placeholder="Product Name">
    <div class="input-row">
      <input v-model.number="amount" type="number" placeholder="Amount">
      <select v-model="unit">
        <option value="ml">ml</option>
        <option value="g">g</option>
      </select>
    </div>
    <button @click="submitProduct">Add to Inventory</button>
  </section>
</template>

<style scoped>
.add-form {
  border: 1px solid #444;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.input-row { display: flex; gap: 0.5rem; }
input, select, button { padding: 0.6rem; border-radius: 4px; border: 1px solid #ccc; }
button { background-color: #42b883; color: white; font-weight: bold; cursor: pointer; }
</style>