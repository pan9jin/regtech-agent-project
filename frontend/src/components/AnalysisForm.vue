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
import { analyzeRegulations } from '@/api/endpoints'

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

const handleSubmit = async () => {
  // 이메일 발송 체크 시 이메일 주소 검증
  if (sendEmails.value && !emailAddresses.value.trim()) {
    alert('이메일 주소를 입력해주세요.')
    return
  }

  isLoading.value = true
  analysisStore.startLoading()

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

    // 이메일 주소 준비 (쉼표로 구분된 전체 문자열 전송)
    const emailRecipient = sendEmails.value ? emailAddresses.value.trim() : null

    // API 호출
    const response = await analyzeRegulations(businessInfo, emailRecipient)
    const result = response.data

    // Store 업데이트
    analysisStore.setAnalysis(result)
    analysisStore.stopLoading()

    // 분석 완료 이벤트
    emit('analysisComplete', result)
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
