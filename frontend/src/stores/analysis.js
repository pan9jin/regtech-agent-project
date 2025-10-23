/**
 * 분석 상태 관리 Store (Pinia)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
  // State
  const currentAnalysis = ref(null)
  const isLoading = ref(false)
  const progress = ref(0)
  const progressText = ref('')
  const error = ref(null)

  // Getters
  const regulations = computed(() => currentAnalysis.value?.regulations || [])
  const checklists = computed(() => currentAnalysis.value?.checklists || [])
  const executionPlans = computed(() => currentAnalysis.value?.execution_plans || [])
  const riskAssessment = computed(() => currentAnalysis.value?.risk_assessment || {})
  const finalReport = computed(() => currentAnalysis.value?.final_report || {})
  const summary = computed(() => currentAnalysis.value?.summary || {})

  const analysisId = computed(() => currentAnalysis.value?.analysis_id || null)

  const hasResults = computed(() => currentAnalysis.value !== null)

  const regulationCount = computed(() => regulations.value.length)
  const checklistCount = computed(() => checklists.value.length)
  const riskScore = computed(() => riskAssessment.value?.total_risk_score || 0)

  // Priority distribution
  const priorityDistribution = computed(() => {
    const distribution = { HIGH: 0, MEDIUM: 0, LOW: 0 }
    regulations.value.forEach((reg) => {
      const priority = reg.priority || 'MEDIUM'
      if (priority in distribution) {
        distribution[priority]++
      }
    })
    return distribution
  })

  // Actions
  function setAnalysis(analysis) {
    currentAnalysis.value = analysis
    error.value = null
  }

  function updateProgress(percent, text) {
    progress.value = Math.min(100, Math.max(0, percent))
    progressText.value = text
  }

  function startLoading() {
    isLoading.value = true
    progress.value = 0
    progressText.value = '분석 시작...'
    error.value = null
  }

  function stopLoading() {
    isLoading.value = false
    progress.value = 100
    progressText.value = '완료!'
  }

  function setError(errorMessage) {
    error.value = errorMessage
    isLoading.value = false
  }

  function clearAnalysis() {
    currentAnalysis.value = null
    isLoading.value = false
    progress.value = 0
    progressText.value = ''
    error.value = null
  }

  return {
    // State
    currentAnalysis,
    isLoading,
    progress,
    progressText,
    error,

    // Getters
    regulations,
    checklists,
    executionPlans,
    riskAssessment,
    finalReport,
    summary,
    analysisId,
    hasResults,
    regulationCount,
    checklistCount,
    riskScore,
    priorityDistribution,

    // Actions
    setAnalysis,
    updateProgress,
    startLoading,
    stopLoading,
    setError,
    clearAnalysis,
  }
})
