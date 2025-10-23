<template>
  <div class="analyze-view">
    <AnalysisForm @analysisComplete="handleAnalysisComplete" />
    <ProgressBar />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import AnalysisForm from '@/components/AnalysisForm.vue'
import ProgressBar from '@/components/ProgressBar.vue'

const router = useRouter()

const handleAnalysisComplete = (result) => {
  // 분석 완료 후 결과 탭으로 자동 전환
  setTimeout(() => {
    router.push('/results')
  }, 1000)
}
</script>

<style scoped>
.analyze-view {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
