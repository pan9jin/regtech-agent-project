<template>
  <div class="checklist-item">
    <div class="checklist-header">
      <strong>[ ] {{ checklist.task_name }}</strong>
      <PriorityBadge :priority="checklist.priority" />
    </div>
    <div class="checklist-details">
      <div class="detail-row">
        <span class="icon">👤</span>
        <span>담당: {{ checklist.responsible_dept || '-' }}</span>
      </div>
      <div class="detail-row">
        <span class="icon">📅</span>
        <span>마감: {{ checklist.deadline || '-' }}</span>
      </div>
      <div class="detail-row">
        <span class="icon">⏱️</span>
        <span>소요시간: {{ checklist.estimated_time || '-' }}</span>
      </div>
      <div v-if="checklist.estimated_cost" class="detail-row">
        <span class="icon">💰</span>
        <span>예상 비용: {{ checklist.estimated_cost }}</span>
      </div>
      <div v-if="checklist.method && checklist.method.length > 0" class="method-section">
        <strong>실행 방법:</strong>
        <ol>
          <li v-for="(step, index) in checklist.method" :key="index">
            {{ step }}
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup>
import PriorityBadge from './PriorityBadge.vue'

defineProps({
  checklist: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
.checklist-item {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
  margin-bottom: 12px;
}

.checklist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.checklist-header strong {
  color: #333;
  font-size: 1.05em;
}

.checklist-details {
  color: #666;
  font-size: 0.95em;
}

.detail-row {
  margin-bottom: 6px;
  display: flex;
  align-items: center;
}

.icon {
  margin-right: 8px;
  font-size: 1.1em;
}

.method-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
}

.method-section strong {
  display: block;
  margin-bottom: 8px;
  color: #333;
}

.method-section ol {
  margin-left: 20px;
}

.method-section li {
  margin-bottom: 4px;
  line-height: 1.5;
}
</style>
