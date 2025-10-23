<template>
  <div class="results-view">
    <div class="card">
      <h2>분석 결과</h2>

      <!-- 분석 결과가 없을 때 -->
      <div v-if="!hasResults" class="empty-state">
        <p>분석을 먼저 실행해주세요.</p>
      </div>

      <!-- 분석 결과가 있을 때 -->
      <div v-else class="results-container">
        <!-- 요약 정보 -->
        <div class="result-summary">
          <h3>분석 요약</h3>
          <div class="result-item">
            <span>분석 ID:</span>
            <strong>{{ analysisId }}</strong>
          </div>
          <div class="result-item">
            <span>적용 규제 수:</span>
            <strong>{{ regulationCount }}개</strong>
          </div>
          <div class="result-item">
            <span>체크리스트 항목:</span>
            <strong>{{ checklistCount }}개</strong>
          </div>
          <div class="result-item">
            <span>리스크 점수:</span>
            <strong :class="getRiskScoreClass(riskScore)">{{ riskScore }}/10</strong>
          </div>
        </div>

        <!-- 액션 버튼 -->
        <div class="action-buttons">
          <button class="btn btn-primary" @click="downloadPDF" :disabled="isDownloading">
            <span v-if="!isDownloading">📄 PDF 보고서 다운로드</span>
            <span v-else>다운로드 중...</span>
          </button>

          <button class="btn btn-secondary" @click="showDistributeModal">
            📧 담당자별 체크리스트 발송
          </button>
        </div>

        <!-- 우선순위 분포 -->
        <div class="priority-distribution">
          <h3>우선순위 분포</h3>
          <div class="priority-stats">
            <div class="priority-stat">
              <PriorityBadge priority="HIGH" />
              <span class="count">{{ priorityDistribution.HIGH }}개</span>
            </div>
            <div class="priority-stat">
              <PriorityBadge priority="MEDIUM" />
              <span class="count">{{ priorityDistribution.MEDIUM }}개</span>
            </div>
            <div class="priority-stat">
              <PriorityBadge priority="LOW" />
              <span class="count">{{ priorityDistribution.LOW }}개</span>
            </div>
          </div>
        </div>

        <!-- 규제 목록 -->
        <div class="regulation-list">
          <h3>적용 규제 목록 ({{ regulationCount }}개)</h3>
          <RegulationCard
            v-for="regulation in regulations"
            :key="regulation.id"
            :regulation="regulation"
          />
        </div>

        <!-- 체크리스트 -->
        <div class="checklist-section">
          <h3>실행 체크리스트 ({{ checklistCount }}개)</h3>
          <ChecklistItem
            v-for="(checklist, index) in checklists"
            :key="index"
            :checklist="checklist"
          />
        </div>
      </div>
    </div>

    <!-- 체크리스트 분배 모달 -->
    <Modal :show="showModal" @close="showModal = false">
      <div v-if="!distributeResult">
        <h2>체크리스트 분배</h2>
        <p>담당자별로 체크리스트를 분배하고 이메일을 발송하시겠습니까?</p>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="handleDistribute">
            확인
          </button>
          <button class="btn btn-secondary" @click="showModal = false">
            취소
          </button>
        </div>
      </div>
      <div v-else>
        <h2>체크리스트 분배 완료</h2>
        <div class="alert alert-success">
          {{ distributeResult.emails_sent }}건의 이메일이 발송되었습니다.
        </div>
        <div v-if="distributeResult.report" class="distribution-report">
          <div class="result-item">
            <span>업무 균형:</span>
            <strong>{{ distributeResult.report.workload_balance }}</strong>
          </div>
          <h3>담당자별 분배 현황</h3>
          <div
            v-for="(info, assignee) in distributeResult.report.distribution"
            :key="assignee"
            class="result-item"
          >
            <span>{{ assignee }}:</span>
            <strong>{{ info.count }}개 작업 ({{ info.percentage }}%)</strong>
          </div>
        </div>
        <button class="btn btn-primary" @click="showModal = false">
          확인
        </button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import { downloadPDF as downloadPDFApi, distributeTasks } from '@/api/endpoints'
import RegulationCard from '@/components/RegulationCard.vue'
import ChecklistItem from '@/components/ChecklistItem.vue'
import PriorityBadge from '@/components/PriorityBadge.vue'
import Modal from '@/components/Modal.vue'

const analysisStore = useAnalysisStore()

const hasResults = computed(() => analysisStore.hasResults)
const analysisId = computed(() => analysisStore.analysisId)
const regulations = computed(() => analysisStore.regulations)
const checklists = computed(() => analysisStore.checklists)
const regulationCount = computed(() => analysisStore.regulationCount)
const checklistCount = computed(() => analysisStore.checklistCount)
const riskScore = computed(() => analysisStore.riskScore)
const priorityDistribution = computed(() => analysisStore.priorityDistribution)

const isDownloading = ref(false)
const showModal = ref(false)
const distributeResult = ref(null)

const getRiskScoreClass = (score) => {
  if (score >= 7) return 'risk-high'
  if (score >= 4) return 'risk-medium'
  return 'risk-low'
}

const downloadPDF = async () => {
  if (!analysisId.value) {
    alert('분석 ID가 없습니다.')
    return
  }

  isDownloading.value = true

  try {
    const response = await downloadPDFApi(analysisId.value)

    // Blob을 URL로 변환하여 다운로드
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `regulation_report_${analysisId.value}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('PDF download error:', error)
    alert('PDF 다운로드 중 오류가 발생했습니다.')
  } finally {
    isDownloading.value = false
  }
}

const showDistributeModal = () => {
  distributeResult.value = null
  showModal.value = true
}

const handleDistribute = async () => {
  if (!analysisId.value) {
    alert('분석 ID가 없습니다.')
    return
  }

  try {
    const response = await distributeTasks(analysisId.value, true)
    distributeResult.value = response.data
  } catch (error) {
    console.error('Distribution error:', error)
    alert('체크리스트 분배 중 오류가 발생했습니다.')
    showModal.value = false
  }
}
</script>

<style scoped>
.results-view {
  animation: fadeIn 0.5s ease;
}

.card {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.card h2 {
  color: #667eea;
  margin-bottom: 20px;
}

.card h3 {
  color: #667eea;
  margin-bottom: 15px;
  margin-top: 25px;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 40px;
  font-size: 1.1em;
}

.result-summary {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e0e0e0;
}

.result-item:last-child {
  border-bottom: none;
}

.risk-high {
  color: #c62828;
}

.risk-medium {
  color: #e65100;
}

.risk-low {
  color: #2e7d32;
}

.action-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.btn {
  padding: 15px 30px;
  border: none;
  border-radius: 8px;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
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

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.priority-distribution {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
}

.priority-stats {
  display: flex;
  gap: 20px;
  justify-content: space-around;
  margin-top: 15px;
}

.priority-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.priority-stat .count {
  font-weight: 600;
  color: #333;
}

.regulation-list,
.checklist-section {
  margin-top: 20px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.alert {
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.alert-success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.distribution-report {
  margin-top: 20px;
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
  .action-buttons {
    flex-direction: column;
  }

  .priority-stats {
    flex-direction: column;
  }
}
</style>
