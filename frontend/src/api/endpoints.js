import api from './index'

/**
 * 규제 분석 실행
 * @param {Object} businessInfo - 사업 정보
 * @param {string|null} emailRecipient - 이메일 수신자 (쉼표로 구분된 이메일 주소)
 */
export const analyzeRegulations = (businessInfo, emailRecipient = null) => {
  const payload = {
    business_info: businessInfo,
    email_recipient: emailRecipient,
  }
  return api.post('/api/analyze', payload)
}

/**
 * 분석 결과 조회
 * @param {string} analysisId - 분석 ID
 */
export const getAnalysis = (analysisId) => {
  return api.get(`/api/analysis/${analysisId}`)
}

/**
 * PDF 다운로드
 * @param {string} analysisId - 분석 ID
 */
export const downloadPDF = (analysisId) => {
  return api.get(`/api/download/${analysisId}`, {
    responseType: 'blob',
  })
}

/**
 * 담당자별 체크리스트 분배
 * @param {string} analysisId - 분석 ID
 * @param {boolean} sendEmails - 이메일 발송 여부
 */
export const distributeTasks = (analysisId, sendEmails = true) => {
  return api.post(`/api/distribute?analysis_id=${analysisId}&send_emails=${sendEmails}`)
}

/**
 * 통계 조회
 */
export const getStats = () => {
  return api.get('/api/stats')
}

/**
 * 헬스 체크
 */
export const healthCheck = () => {
  return api.get('/health')
}
