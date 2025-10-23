<template>
  <div class="regulation-item">
    <div class="regulation-header">
      <div class="regulation-name">{{ regulation.name }}</div>
      <PriorityBadge :priority="regulation.priority" />
    </div>
    <div class="regulation-detail">
      <div><strong>카테고리:</strong> {{ regulation.category }}</div>
      <div><strong>관할 기관:</strong> {{ regulation.authority }}</div>
      <div><strong>적용 이유:</strong> {{ regulation.why_applicable }}</div>
      <div v-if="regulation.key_requirements && regulation.key_requirements.length > 0">
        <strong>주요 요구사항:</strong>
        <ul>
          <li v-for="(req, index) in regulation.key_requirements" :key="index">
            {{ req }}
          </li>
        </ul>
      </div>
      <div v-if="regulation.reference_url">
        <strong>참고 URL:</strong>
        <a :href="regulation.reference_url" target="_blank" rel="noopener noreferrer">
          {{ regulation.reference_url }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import PriorityBadge from './PriorityBadge.vue'

defineProps({
  regulation: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
.regulation-item {
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 15px;
  transition: all 0.3s ease;
}

.regulation-item:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
}

.regulation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.regulation-name {
  font-size: 1.2em;
  font-weight: 700;
  color: #333;
}

.regulation-detail {
  margin-top: 10px;
  color: #666;
  line-height: 1.8;
}

.regulation-detail > div {
  margin-bottom: 8px;
}

.regulation-detail strong {
  color: #333;
}

.regulation-detail ul {
  margin-top: 8px;
  margin-left: 20px;
}

.regulation-detail ul li {
  margin-bottom: 4px;
}

.regulation-detail a {
  color: #667eea;
  text-decoration: none;
  word-break: break-all;
}

.regulation-detail a:hover {
  text-decoration: underline;
}
</style>
