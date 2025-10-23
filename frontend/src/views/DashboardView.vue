<template>
  <div class="dashboard-view">
    <!-- 통계 그리드 -->
    <div class="stats-grid">
      <StatsCard :value="totalAnalyses" label="총 분석 수" />
      <StatsCard :value="totalRegulations" label="발견된 규제" />
      <StatsCard :value="totalChecklists" label="생성된 체크리스트" />
      <StatsCard value="88%" label="자동화율" />
    </div>

    <!-- 시스템 상태 -->
    <div class="card">
      <h3>시스템 상태</h3>
      <div class="system-status">
        <div class="status-item">
          <span class="status-indicator status-ok"></span>
          <span>규제 분석 엔진</span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-ok"></span>
          <span>이메일 자동화</span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-ok"></span>
          <span>담당자 배정 AI</span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-ok"></span>
          <span>Webhook API</span>
        </div>
      </div>
    </div>

    <!-- 최근 분석 내역 -->
    <div v-if="recentAnalyses.length > 0" class="card">
      <h3>최근 분석 내역</h3>
      <div class="recent-analyses">
        <div
          v-for="analysis in recentAnalyses"
          :key="analysis.analysis_id"
          class="analysis-item"
        >
          <div class="analysis-info">
            <div class="analysis-id">{{ analysis.analysis_id }}</div>
            <div class="analysis-industry">{{ analysis.industry }}</div>
          </div>
          <div class="analysis-stats">
            <span>규제: {{ analysis.regulation_count }}개</span>
            <span>체크리스트: {{ analysis.checklist_count }}개</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 새로고침 버튼 -->
    <div class="refresh-section">
      <button class="btn btn-primary" @click="refreshStats" :disabled="isLoading">
        <span v-if="!isLoading">🔄 통계 새로고침</span>
        <span v-else>로딩 중...</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useStatsStore } from '@/stores/stats'
import StatsCard from '@/components/StatsCard.vue'

const statsStore = useStatsStore()

const totalAnalyses = computed(() => statsStore.totalAnalyses)
const totalRegulations = computed(() => statsStore.totalRegulations)
const totalChecklists = computed(() => statsStore.totalChecklists)
const recentAnalyses = computed(() => statsStore.recentAnalyses)
const isLoading = computed(() => statsStore.isLoading)

const refreshStats = async () => {
  await statsStore.fetchStats()
}

// 컴포넌트 마운트 시 통계 로드
onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
.dashboard-view {
  animation: fadeIn 0.5s ease;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

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

.system-status {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.status-item:last-child {
  border-bottom: none;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 12px;
}

.status-ok {
  background: #4caf50;
  box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.status-warning {
  background: #ff9800;
  box-shadow: 0 0 10px rgba(255, 152, 0, 0.5);
}

.status-error {
  background: #f44336;
  box-shadow: 0 0 10px rgba(244, 67, 54, 0.5);
}

.recent-analyses {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.analysis-item:hover {
  background: #e9ecef;
  transform: translateX(5px);
}

.analysis-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.analysis-id {
  font-weight: 600;
  color: #667eea;
}

.analysis-industry {
  font-size: 0.9em;
  color: #666;
}

.analysis-stats {
  display: flex;
  flex-direction: column;
  gap: 5px;
  text-align: right;
  font-size: 0.9em;
  color: #666;
}

.refresh-section {
  display: flex;
  justify-content: center;
}

.btn {
  padding: 15px 30px;
  border: none;
  border-radius: 8px;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 200px;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .analysis-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .analysis-stats {
    text-align: left;
  }
}
</style>
