<template>
  <span :class="['priority-badge', priorityClass]">
    {{ priority }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  priority: {
    type: String,
    required: true,
    validator: (value) => ['HIGH', 'MEDIUM', 'LOW'].includes(value),
  },
})

const priorityClass = computed(() => {
  return `priority-${props.priority.toLowerCase()}`
})
</script>

<style scoped>
.priority-badge {
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 600;
  display: inline-block;
}

.priority-high {
  background: #ffebee;
  color: #c62828;
}

.priority-medium {
  background: #fff3e0;
  color: #e65100;
}

.priority-low {
  background: #e8f5e9;
  color: #2e7d32;
}
</style>
