import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
  // State
  const currentAnalysis = ref(null)
  const isLoading = ref(false)
  const progress = ref(0)
  const progressText = ref('')
  const currentAgent = ref('')
  const error = ref(null)

  // Computed: Analysis 데이터 접근
  const analysisId = computed(() => currentAnalysis.value?.analysis_id || null)
  const regulations = computed(() => currentAnalysis.value?.regulations || [])
  const checklists = computed(() => currentAnalysis.value?.checklists || [])
  const executionPlans = computed(() => currentAnalysis.value?.execution_plans || [])
  const riskAssessment = computed(() => currentAnalysis.value?.risk_assessment || {})
  const finalReport = computed(() => currentAnalysis.value?.final_report || {})
  const businessInfo = computed(() => currentAnalysis.value?.business_info || {})
  const emailStatus = computed(() => currentAnalysis.value?.email_status || {})

  // Computed: Summary 데이터 (API 응답 구조에 따라)
  const summary = computed(() => currentAnalysis.value?.summary || {})

  // Computed: 결과 존재 여부
  const hasResults = computed(() => {
    return currentAnalysis.value !== null && regulations.value.length > 0
  })

  // Computed: 개수
  const regulationCount = computed(() => regulations.value.length)
  const checklistCount = computed(() => checklists.value.length)

  // Computed: 리스크 점수
  const riskScore = computed(() => {
    const score = riskAssessment.value?.total_risk_score || 0
    return typeof score === 'number' ? score.toFixed(1) : '0.0'
  })

  // Computed: 우선순위 분포
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
    console.log('Setting analysis in store:', analysis)
    currentAnalysis.value = analysis
    error.value = null
  }

  function updateProgress(percent, text, agent = '') {
    progress.value = percent
    progressText.value = text
    currentAgent.value = agent
  }

  function startLoading() {
    isLoading.value = true
    progress.value = 0
    progressText.value = '분석을 시작합니다...'
    currentAgent.value = ''
    error.value = null
  }

  function stopLoading() {
    isLoading.value = false
    progress.value = 100
    progressText.value = '분석 완료!'
  }

  function setError(errorMessage) {
    error.value = errorMessage
    isLoading.value = false
    progress.value = 0
    progressText.value = ''
  }

  function clearAnalysis() {
    currentAnalysis.value = null
    error.value = null
    progress.value = 0
    progressText.value = ''
  }

  return {
    // State
    currentAnalysis,
    isLoading,
    progress,
    progressText,
    currentAgent,
    error,

    // Computed
    analysisId,
    regulations,
    checklists,
    executionPlans,
    riskAssessment,
    finalReport,
    businessInfo,
    emailStatus,
    summary,
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
