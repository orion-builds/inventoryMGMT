<script setup>
import { ref, onMounted } from "vue";

// 1. The Reactive Bucket
const products = ref([]);

// 2. The Fetch Logic
const fetchProducts = async () => {
  try {
    const response = await fetch("http://127.0.0.1:8000/products/");
    const data = await response.json();
    products.value = data.inventory;
  } catch (error) {
    console.error("Error fetching products:", error);
  }
};

// 3. Trigger fetch when the component hits the screen
onMounted(() => {
  fetchProducts();
});
</script>

<template>
  <div class="inventory-box">
    <h2>My Inventory</h2>

    <ul v-if="products.length > 0">
      <li v-for="item in products" :key="item.product_id">
        <strong>{{ item.brand }}</strong> - {{ item.name }} ({{ item.amount
        }}{{ item.unit_of_measure }})
      </li>
    </ul>

    <p v-else>Loading data from backend...</p>
  </div>
</template>

<style scoped>
/* Optional: Just a little styling to box it in */
.inventory-box {
  border: 1px solid #ccc;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}
</style>
