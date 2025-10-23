<template>
  <div v-if="show" class="card">
    <h3>분석 진행 중</h3>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }">
        {{ progress }}%
      </div>
    </div>
    <p class="progress-text">{{ progressText }}</p>
  </div>
</template>

<script setup>
import { computed, watch, ref, onMounted, onUnmounted } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'

const analysisStore = useAnalysisStore()

const progress = computed(() => analysisStore.progress)
const progressText = computed(() => analysisStore.progressText)
const show = computed(() => analysisStore.isLoading)

// 진행 상황 시뮬레이션 (실제 API에서 progress 업데이트가 없을 경우)
let progressInterval = null

const simulateProgress = () => {
  const steps = [
    { value: 20, text: '규제 검색 중...' },
    { value: 40, text: '규제 분류 중...' },
    { value: 60, text: '체크리스트 생성 중...' },
    { value: 80, text: 'PDF 보고서 생성 중...' },
    { value: 95, text: '최종 검토 중...' },
  ]

  let stepIndex = 0

  progressInterval = setInterval(() => {
    if (stepIndex < steps.length && analysisStore.isLoading) {
      const step = steps[stepIndex]
      analysisStore.updateProgress(step.value, step.text)
      stepIndex++
    } else if (!analysisStore.isLoading) {
      clearInterval(progressInterval)
    }
  }, 2000)
}

watch(
  () => analysisStore.isLoading,
  (isLoading) => {
    if (isLoading) {
      simulateProgress()
    } else {
      if (progressInterval) {
        clearInterval(progressInterval)
        progressInterval = null
      }
    }
  }
)

onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
})
</script>

<style scoped>
.card {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  margin-bottom: 20px;
}

.card h3 {
  color: #667eea;
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: #f0f0f0;
  border-radius: 15px;
  overflow: hidden;
  margin: 20px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 0.9em;
}

.progress-text {
  text-align: center;
  color: #667eea;
  font-weight: 600;
  margin-top: 10px;
}
</style>
