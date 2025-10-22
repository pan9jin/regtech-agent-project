// API Base URL
const API_BASE = window.location.origin;

// 현재 분석 ID
let currentAnalysisId = null;

// ============================================================
// 탭 전환
// ============================================================

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;

        // 모든 탭 비활성화
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        // 선택된 탭 활성화
        btn.classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // 대시보드 탭이면 통계 로드
        if (tabName === 'dashboard') {
            loadStats();
        }
    });
});

// ============================================================
// 폼 제출
// ============================================================

document.getElementById('analysis-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');

    // 데이터 준비
    const data = {
        industry: formData.get('industry'),
        product_name: formData.get('product_name'),
        raw_materials: formData.get('raw_materials'),
        processes: formData.get('processes').split(',').map(s => s.trim()),
        employee_count: parseInt(formData.get('employee_count')),
        sales_channels: formData.get('sales_channels').split(',').map(s => s.trim()),
        export_countries: formData.get('export_countries') ?
            formData.get('export_countries').split(',').map(s => s.trim()) : []
    };

    const sendEmails = formData.get('send_emails') === 'on';

    // 버튼 비활성화
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';

    // 진행 상황 표시
    showProgress();

    try {
        // API 호출
        const response = await fetch(`${API_BASE}/api/analyze?send_emails=${sendEmails}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('분석 실패');
        }

        const result = await response.json();
        currentAnalysisId = result.analysis_id;

        // 진행 완료
        updateProgress(100, '분석 완료!');

        setTimeout(() => {
            hideProgress();
            showResults(result);

            // 결과 탭으로 전환
            document.querySelector('[data-tab="results"]').click();
        }, 1000);

    } catch (error) {
        console.error('Error:', error);
        alert('분석 중 오류가 발생했습니다: ' + error.message);
        hideProgress();
    } finally {
        submitBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
});

// ============================================================
// 진행 상황 표시
// ============================================================

function showProgress() {
    document.getElementById('progress-section').style.display = 'block';

    let progress = 0;
    const steps = [
        { value: 20, text: '규제 검색 중...' },
        { value: 40, text: '규제 분류 중...' },
        { value: 60, text: '체크리스트 생성 중...' },
        { value: 80, text: 'PDF 보고서 생성 중...' },
        { value: 95, text: '최종 검토 중...' }
    ];

    let stepIndex = 0;
    const interval = setInterval(() => {
        if (stepIndex < steps.length) {
            const step = steps[stepIndex];
            updateProgress(step.value, step.text);
            stepIndex++;
        } else {
            clearInterval(interval);
        }
    }, 2000);
}

function updateProgress(percent, text) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

function hideProgress() {
    document.getElementById('progress-section').style.display = 'none';
    updateProgress(0, '');
}

// ============================================================
// 결과 표시
// ============================================================

function showResults(result) {
    const container = document.getElementById('results-container');
    const summary = result.summary || {};
    const regulations = result.regulations || [];
    const checklists = result.checklists || [];

    let html = `
        <div class="result-summary">
            <h3>분석 요약</h3>
            <div class="result-item">
                <span>분석 ID:</span>
                <strong>${result.analysis_id}</strong>
            </div>
            <div class="result-item">
                <span>적용 규제 수:</span>
                <strong>${summary.total_regulations || 0}개</strong>
            </div>
            <div class="result-item">
                <span>체크리스트 항목:</span>
                <strong>${summary.total_tasks || summary.total_checklist_items || 0}개</strong>
            </div>
        </div>

        <button class="btn btn-primary" onclick="downloadPDF('${result.analysis_id}')">
            📄 PDF 보고서 다운로드
        </button>

        <button class="btn btn-secondary" onclick="distributeTasks('${result.analysis_id}')">
            📧 담당자별 체크리스트 발송
        </button>

        <div class="regulation-list">
            <h3>적용 규제 목록 (${regulations.length}개)</h3>
    `;

    regulations.forEach(reg => {
        const priorityClass = `priority-${reg.priority.toLowerCase()}`;
        html += `
            <div class="regulation-item">
                <div class="regulation-header">
                    <div class="regulation-name">${reg.name}</div>
                    <span class="priority-badge ${priorityClass}">${reg.priority}</span>
                </div>
                <div class="regulation-detail">
                    <strong>카테고리:</strong> ${reg.category}<br>
                    <strong>관할 기관:</strong> ${reg.authority}<br>
                    <strong>적용 이유:</strong> ${reg.why_applicable}
                </div>
            </div>
        `;
    });

    html += '</div><div class="checklist-grid"><h3>실행 체크리스트 (' + checklists.length + '개)</h3>';

    checklists.forEach(item => {
        html += `
            <div class="checklist-item">
                <div style="margin-bottom: 8px;">
                    <strong>[ ] ${item.task_name}</strong>
                    <span class="priority-badge priority-${item.priority.toLowerCase()}" style="margin-left: 8px;">${item.priority}</span>
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    <div>📌 담당: ${item.responsible_dept || '-'}</div>
                    <div>⏰ 마감: ${item.deadline || '-'}</div>
                    <div>⏱️ 소요시간: ${item.estimated_time || '-'}</div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    container.innerHTML = html;
}

// ============================================================
// PDF 다운로드
// ============================================================

async function downloadPDF(analysisId) {
    try {
        window.location.href = `${API_BASE}/api/download/${analysisId}`;
    } catch (error) {
        console.error('Error:', error);
        alert('PDF 다운로드 실패');
    }
}

// ============================================================
// 담당자별 체크리스트 발송
// ============================================================

async function distributeTasks(analysisId) {
    if (!confirm('담당자별로 체크리스트를 분배하고 이메일을 발송하시겠습니까?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/distribute?analysis_id=${analysisId}&send_emails=true`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('분배 실패');
        }

        const result = await response.json();

        showModal(`
            <h2>체크리스트 분배 완료</h2>
            <div class="alert alert-success">
                ${result.emails_sent}건의 이메일이 발송되었습니다.
            </div>
            <div class="result-item">
                <span>업무 균형:</span>
                <strong>${result.report.workload_balance}</strong>
            </div>
            <h3>담당자별 분배 현황</h3>
            ${Object.entries(result.report.distribution).map(([assignee, info]) => `
                <div class="result-item">
                    <span>${assignee}:</span>
                    <strong>${info.count}개 작업 (${info.percentage}%)</strong>
                </div>
            `).join('')}
        `);

    } catch (error) {
        console.error('Error:', error);
        alert('체크리스트 분배 실패: ' + error.message);
    }
}

// ============================================================
// 통계 로드
// ============================================================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        if (!response.ok) throw new Error('통계 로드 실패');

        const stats = await response.json();

        document.getElementById('total-analyses').textContent = stats.total_analyses;
        document.getElementById('total-regulations').textContent = stats.total_regulations;
        document.getElementById('total-checklists').textContent = stats.total_checklists;

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ============================================================
// 모달
// ============================================================

function showModal(content) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');

    modalBody.innerHTML = content;
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('modal');
    modal.classList.remove('active');
}

// 모달 닫기 이벤트
document.querySelector('.modal-close').addEventListener('click', closeModal);
document.getElementById('modal').addEventListener('click', (e) => {
    if (e.target.id === 'modal') {
        closeModal();
    }
});

// ============================================================
// 초기화
// ============================================================

// 페이지 로드 시 통계 로드
window.addEventListener('load', () => {
    loadStats();

    // 샘플 데이터 입력 (데모용)
    if (window.location.search.includes('demo=1')) {
        document.getElementById('industry').value = '배터리 제조';
        document.getElementById('product_name').value = '리튬이온 배터리';
        document.getElementById('raw_materials').value = '리튬, 코발트, 니켈';
        document.getElementById('processes').value = '화학 처리, 고온 가공, 조립';
        document.getElementById('employee_count').value = '45';
        document.getElementById('sales_channels').value = 'B2B, 수출';
        document.getElementById('export_countries').value = '미국, 유럽, 일본';
    }
});
