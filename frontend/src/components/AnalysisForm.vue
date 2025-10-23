<template>
  <div class="card">
    <h2>사업 정보 입력</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="industry">업종 *</label>
        <input
          type="text"
          id="industry"
          v-model="formData.industry"
          placeholder="예: 배터리 제조"
          required
        />
      </div>

      <div class="form-group">
        <label for="product_name">제품명 *</label>
        <input
          type="text"
          id="product_name"
          v-model="formData.product_name"
          placeholder="예: 리튬이온 배터리"
          required
        />
      </div>

      <div class="form-group">
        <label for="raw_materials">주요 원자재 *</label>
        <input
          type="text"
          id="raw_materials"
          v-model="formData.raw_materials"
          placeholder="예: 리튬, 코발트, 니켈"
          required
        />
      </div>

      <div class="form-group">
        <label for="processes">주요 공정 (쉼표로 구분) *</label>
        <input
          type="text"
          id="processes"
          v-model="formData.processes"
          placeholder="예: 화학 처리, 고온 가공, 조립"
          required
        />
      </div>

      <div class="form-group">
        <label for="employee_count">직원 수 *</label>
        <input
          type="number"
          id="employee_count"
          v-model.number="formData.employee_count"
          placeholder="예: 45"
          required
          min="1"
        />
      </div>

      <div class="form-group">
        <label for="sales_channels">판매 채널 (쉼표로 구분) *</label>
        <input
          type="text"
          id="sales_channels"
          v-model="formData.sales_channels"
          placeholder="예: B2B, 수출"
          required
        />
      </div>

      <div class="form-group">
        <label for="export_countries">수출 국가 (쉼표로 구분)</label>
        <input
          type="text"
          id="export_countries"
          v-model="formData.export_countries"
          placeholder="예: 미국, 유럽, 일본"
        />
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" v-model="sendEmails" />
          분석 완료 후 담당자에게 이메일 자동 발송
        </label>
      </div>

      <!-- 이메일 입력란 (체크박스 체크 시에만 표시) -->
      <div v-if="sendEmails" class="form-group email-input-section">
        <label for="email_addresses">수신 이메일 주소 (쉼표로 구분) *</label>
        <input
          type="text"
          id="email_addresses"
          v-model="emailAddresses"
          placeholder="예: manager@company.com, director@company.com"
          :required="sendEmails"
        />
        <p class="input-hint">여러 이메일 주소를 쉼표(,)로 구분하여 입력하세요.</p>
      </div>

      <button type="submit" class="btn btn-primary" :disabled="isLoading">
        <span v-if="!isLoading" class="btn-text">분석 시작</span>
        <span v-else class="btn-loader">분석 중...</span>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import { analyzeRegulations, getAnalysis } from '@/api/endpoints'

const analysisStore = useAnalysisStore()

const formData = ref({
  industry: '',
  product_name: '',
  raw_materials: '',
  processes: '',
  employee_count: null,
  sales_channels: '',
  export_countries: '',
})

const sendEmails = ref(false)
const emailAddresses = ref('')
const isLoading = ref(false)

const emit = defineEmits(['analysisComplete'])

// Agent 단계별 진행률 시뮬레이션
const simulateAgentProgress = () => {
  const agentSteps = [
    { progress: 10, text: '사업 정보 분석 중', agent: 'Analyzer Agent', duration: 3000 },
    { progress: 20, text: '규제 검색 중', agent: 'Search Agent', duration: 8000 },
    { progress: 35, text: '규제 분류 중', agent: 'Classifier Agent', duration: 10000 },
    { progress: 45, text: '우선순위 결정 중', agent: 'Prioritizer Agent', duration: 5000 },
    { progress: 65, text: '체크리스트 및 리스크 평가 중', agent: 'Checklist & Risk Agent', duration: 15000 },
    { progress: 75, text: '실행 계획 수립 중', agent: 'Planning Agent', duration: 10000 },
    { progress: 90, text: 'PDF 보고서 생성 중', agent: 'Report Generator Agent', duration: 15000 },
    { progress: 95, text: '이메일 발송 중', agent: 'Email Notifier Agent', duration: 5000 },
  ]

  let currentStep = 0
  let totalElapsed = 0

  const updateStep = () => {
    if (currentStep < agentSteps.length && analysisStore.isLoading) {
      const step = agentSteps[currentStep]
      analysisStore.updateProgress(step.progress, step.text, step.agent)

      totalElapsed += step.duration
      currentStep++

      if (currentStep < agentSteps.length) {
        setTimeout(updateStep, step.duration)
      }
    }
  }

  updateStep()
}

const handleSubmit = async () => {
  // 이메일 발송 체크 시 이메일 주소 검증
  if (sendEmails.value && !emailAddresses.value.trim()) {
    alert('이메일 주소를 입력해주세요.')
    return
  }

  isLoading.value = true
  analysisStore.startLoading()

  // Agent 진행 상황 시뮬레이션 시작
  simulateAgentProgress()

  try {
    // 데이터 변환
    const businessInfo = {
      industry: formData.value.industry,
      product_name: formData.value.product_name,
      raw_materials: formData.value.raw_materials,
      processes: formData.value.processes.split(',').map((s) => s.trim()),
      employee_count: formData.value.employee_count,
      sales_channels: formData.value.sales_channels.split(',').map((s) => s.trim()),
      export_countries: formData.value.export_countries
        ? formData.value.export_countries.split(',').map((s) => s.trim())
        : [],
    }

    // 이메일 주소 준비 (쉼표로 구분된 배열 전송)
    const emailRecipients = sendEmails.value
      ? emailAddresses.value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length > 0)
      : []

    if (sendEmails.value && emailRecipients.length === 0) {
      alert('올바른 이메일 주소를 입력해주세요.')
      return
    }

    // API 호출
    const response = await analyzeRegulations(
      businessInfo,
      emailRecipients.length > 0 ? emailRecipients : null,
    )
    const triggerResult = response.data

    console.log('Analysis trigger response:', triggerResult)

    // 전체 데이터 가져오기 (regulations, checklists 등 포함)
    if (triggerResult.analysis_id) {
      const fullDataResponse = await getAnalysis(triggerResult.analysis_id)
      const fullResult = fullDataResponse.data

      console.log('Full analysis data:', fullResult)

      // 100% 완료 표시
      analysisStore.updateProgress(100, '분석 완료!', '')

      // Store 업데이트 (전체 데이터 사용)
      analysisStore.setAnalysis(fullResult)

      // 0.5초 대기 후 로딩 종료 및 결과 화면으로 이동
      setTimeout(() => {
        analysisStore.stopLoading()
        emit('analysisComplete', fullResult)
      }, 500)
    } else {
      throw new Error('분석 ID를 받지 못했습니다.')
    }
  } catch (error) {
    console.error('Analysis error:', error)
    analysisStore.setError(error.message || '분석 중 오류가 발생했습니다')
  } finally {
    isLoading.value = false
  }
}

// 데모 모드: URL에 ?demo=1이 있으면 샘플 데이터 입력
if (window.location.search.includes('demo=1')) {
  formData.value = {
    industry: '배터리 제조',
    product_name: '리튬이온 배터리',
    raw_materials: '리튬, 코발트, 니켈',
    processes: '화학 처리, 고온 가공, 조립',
    employee_count: 45,
    sales_channels: 'B2B, 수출',
    export_countries: '미국, 유럽, 일본',
  }
}
</script>

<style scoped>
.card {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  margin-bottom: 20px;
}

.card h2 {
  color: #667eea;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #555;
}

.form-group input[type='text'],
.form-group input[type='number'] {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1em;
  transition: border-color 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input[type='checkbox'] {
  margin-right: 8px;
}

.btn {
  padding: 15px 30px;
  border: none;
  border-radius: 8px;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
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

.btn-loader {
  display: inline-block;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.btn-loader::before {
  content: '';
  display: inline-block;
  width: 16px;
  height: 16px;
  margin-right: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
}

/* 이메일 입력 섹션 */
.email-input-section {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
    padding-top: 0;
    padding-bottom: 0;
  }
  to {
    opacity: 1;
    max-height: 200px;
    padding-top: 15px;
    padding-bottom: 15px;
  }
}

.input-hint {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 0.85em;
  color: #666;
  font-style: italic;
}
</style>
