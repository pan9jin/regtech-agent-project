<template>
  <div v-if="show" class="card">
    <h3>분석 진행 중</h3>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }">
        <span v-if="progress > 0">{{ Math.round(progress) }}%</span>
      </div>
    </div>
    <div class="progress-info">
      <p class="progress-text">{{ progressText }}</p>
      <p v-if="currentAgent" class="agent-name">
        <span class="agent-icon">⚙️</span>
        {{ currentAgent }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'

const analysisStore = useAnalysisStore()

const progress = computed(() => analysisStore.progress)
const progressText = computed(() => analysisStore.progressText)
const currentAgent = computed(() => analysisStore.currentAgent)
const show = computed(() => analysisStore.isLoading)
</script>

<style scoped>
.card {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card h3 {
  color: #667eea;
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 35px;
  background: #f0f0f0;
  border-radius: 15px;
  overflow: hidden;
  margin: 20px 0;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.8s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 0.9em;
  position: relative;
}

.progress-fill span {
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-text {
  text-align: center;
  color: #667eea;
  font-weight: 600;
  font-size: 1em;
  margin: 0;
}

.agent-name {
  text-align: center;
  color: #888;
  font-size: 0.95em;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  animation: pulse 2s ease-in-out infinite;
}

.agent-icon {
  font-size: 1.2em;
  animation: rotate 2s linear infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
