/**
 * 통계 상태 관리 Store (Pinia)
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getStats } from '@/api/endpoints'

export const useStatsStore = defineStore('stats', () => {
  // State
  const totalAnalyses = ref(0)
  const totalRegulations = ref(0)
  const totalChecklists = ref(0)
  const recentAnalyses = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Actions
  async function fetchStats() {
    isLoading.value = true
    error.value = null

    try {
      const response = await getStats()
      const data = response.data

      totalAnalyses.value = data.total_analyses || 0
      totalRegulations.value = data.total_regulations || 0
      totalChecklists.value = data.total_checklists || 0
      recentAnalyses.value = data.recent_analyses || []
    } catch (err) {
      error.value = err.message || '통계 조회 실패'
      console.error('Failed to fetch stats:', err)
    } finally {
      isLoading.value = false
    }
  }

  function clearStats() {
    totalAnalyses.value = 0
    totalRegulations.value = 0
    totalChecklists.value = 0
    recentAnalyses.value = []
    error.value = null
  }

  return {
    // State
    totalAnalyses,
    totalRegulations,
    totalChecklists,
    recentAnalyses,
    isLoading,
    error,

    // Actions
    fetchStats,
    clearStats,
  }
})
