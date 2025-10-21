# RegTech Assistant - AI 규제 준수 자동화 시스템

> 중소 제조기업의 규제 준수를 돕는 8-Agent LangGraph 기반 AI 시스템

## 📋 프로젝트 개요

**RegTech Assistant**는 중소 제조기업이 복잡한 규제 환경에서 안전하게 사업을 운영할 수 있도록 돕는 AI 기반 규제 준수 자동화 서비스입니다. 사업 정보를 입력하면 AI가 적용 가능한 규제를 자동으로 식별하고, 실행 가능한 체크리스트와 리스크 평가, 통합 보고서를 제공합니다.

### 핵심 가치

- **빠른 규제 파악**: 사업 정보 입력 후 5-10분 내 적용 규제 자동 식별
- **실행 가능한 체크리스트**: 규제별 구체적 준수 항목 자동 생성
- **체계적 실행 계획**: 의존성, 타임라인, 마일스톤 포함 실행 계획
- **리스크 평가**: 미준수 시 벌칙, 영향도 분석 및 완화 방안 제시
- **통합 보고서**: 경영진/실무진/법무팀용 맞춤 보고서 자동 생성 (PDF)

---

## 🤖 8-Agent 시스템 아키텍처

### LangGraph Multi-Agent Workflow

```
START → Analyzer → Searcher → Classifier → Prioritizer
     → Checklist Generator → Planning Agent → Risk Assessor
     → Report Generator → END
```

### Agent 상세 설명

| Agent | 역할 | 입력 | 출력 |
|-------|------|------|------|
| **1. Analyzer** | 사업 정보 분석 및 키워드 추출 | 사업 정보 (업종, 제품, 원자재 등) | 규제 검색용 키워드 5-10개 |
| **2. Searcher** | Tavily API로 규제 정보 웹 검색 | 키워드 목록 | 검색 결과 8개 |
| **3. Classifier** | 규제 분류 및 적용성 판단 | 사업 정보 + 검색 결과 | 3개 카테고리로 분류된 규제 목록 |
| **4. Prioritizer** | 규제 우선순위 결정 | 분류된 규제 목록 | HIGH/MEDIUM/LOW 우선순위 부여 |
| **5. Checklist Generator** | 규제별 실행 체크리스트 생성 | 우선순위 규제 목록 | 규제별 3-5개 실행 항목 |
| **6. Planning Agent** | 실행 계획 수립 | 체크리스트 | 타임라인, 의존성, 마일스톤 포함 계획 |
| **7. Risk Assessor** | 리스크 평가 및 완화 방안 | 규제 목록 + 사업 정보 | 리스크 점수, 벌칙, 과거 사례, 완화 방안 |
| **8. Report Generator** | 통합 보고서 생성 | 모든 Agent 결과 | 마크다운 + PDF 통합 보고서 |

---

## 🛠️ 기술 스택

- **AI/ML**: LangChain, LangGraph, OpenAI GPT-4o-mini
- **Web Search**: Tavily API
- **Python**: 3.11+
- **핵심 라이브러리**:
  - `langchain-openai`: OpenAI LLM 연동
  - `langchain-tavily`: Tavily 검색 API
  - `langgraph`: Multi-Agent Workflow 구성
  - `markdown`: Markdown → HTML 변환
  - `weasyprint`: PDF 생성
  - `python-dotenv`: 환경변수 관리

---

## 🚀 설치 및 실행 방법

### 1. 환경 요구사항

- Python 3.11 이상
- OpenAI API 키
- Tavily API 키

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd regulation_agent

# 가상환경 생성 및 활성화
python -m venv regtech
source regtech/bin/activate  # Windows: regtech\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```bash
OPENAI_API_KEY=sk-proj-...
TAVILY_API_KEY=tvly-...
LANGSMITH_API_KEY=lsv2_pt_...  # 선택사항 (LangSmith 추적)
LANGSMITH_TRACING=true         # 선택사항
```

### 4. 실행

```bash
python regulation_agent_workflow.py
```

**예상 소요 시간**: 5-10분 (8개 Agent 순차 실행)

### 5. 결과 확인

실행 완료 시 다음 파일이 생성됩니다:

- `regulation_analysis_result.json`: 전체 분석 결과 (JSON)
- `report/regulation_report.md`: 통합 보고서 (Markdown)
- `report/regulation_report.pdf`: 통합 보고서 (PDF)

---

## 📊 출력 예시

### 콘솔 출력 (요약)

```
🤖 규제 AI Agent 시스템 시작
========================================

🔍 [Analyzer Agent] 사업 정보 분석 중...
   ✓ 추출된 키워드 (7개): ['배터리', '리튬', '화학물질', ...]

🌐 [Search Agent] Tavily로 규제 정보 검색 중...
   ✓ 검색 결과: 8개 문서 발견

📋 [Classifier Agent] 규제 분류 및 적용성 판단 중...
   ✓ 규제 분류 완료: 총 8개
      - 안전/환경: 4개
      - 제품 인증: 2개
      - 공장 운영: 2개

⚡ [Prioritizer Agent] 우선순위 결정 중...
   ✓ 우선순위 결정 완료:
      - HIGH: 3개
      - MEDIUM: 3개
      - LOW: 2개

📝 [Checklist Generator Agent] 규제별 체크리스트 생성 중...
   ✓ 체크리스트 생성 완료: 총 24개 항목

📅 [Planning Agent] 실행 계획 수립 중...
   ✓ 실행 계획 수립 완료: 총 8개 계획

⚠️  [Risk Assessment Agent] 리스크 평가 중...
   ✓ 리스크 평가 완료: 전체 점수 7.2/10
      - 고위험 항목: 3개

📄 [Report Generation Agent] 통합 보고서 생성 중...
   ✓ PDF 보고서 저장: report/regulation_report.pdf
   ✓ Markdown 보고서 저장: report/regulation_report.md
   ✓ 통합 보고서 생성 완료
```

### JSON 결과 구조

```json
{
  "business_info": { ... },
  "summary": {
    "total_regulations": 8,
    "priority_distribution": { "HIGH": 3, "MEDIUM": 3, "LOW": 2 },
    "total_checklist_items": 24,
    "total_execution_plans": 8,
    "risk_score": 7.2
  },
  "regulations": [ ... ],
  "checklists": [ ... ],
  "execution_plans": [ ... ],
  "risk_assessment": { ... },
  "final_report": {
    "executive_summary": "...",
    "key_insights": [ ... ],
    "action_items": [ ... ],
    "risk_highlights": [ ... ],
    "next_steps": [ ... ],
    "full_markdown": "...",
    "report_pdf_path": "report/regulation_report.pdf"
  }
}
```

---

## 📁 프로젝트 구조

```
regulation_agent/
├── regulation_agent_workflow.py  # 8-Agent 워크플로우 메인 파일
├── requirements.txt               # Python 패키지 의존성
├── .env                           # 환경변수 (API 키)
├── .gitignore                     # Git 무시 파일 목록
├── README.md                      # 프로젝트 소개 (본 문서)
├── CLAUDE.md                      # Claude Code 개발 가이드
├── agent_prd_v2.md                # 제품 요구사항 명세서 (PRD)
├── regulation_analysis_result.json # 분석 결과 (JSON)
└── report/
    ├── regulation_report.md       # 통합 보고서 (Markdown)
    └── regulation_report.pdf      # 통합 보고서 (PDF)
```

---

## 🎯 사용 예시

### 샘플 입력 (배터리 제조업)

```python
sample_business_info = {
    "industry": "배터리 제조",
    "product_name": "리튬이온 배터리",
    "raw_materials": "리튬, 코발트, 니켈",
    "processes": ["화학 처리", "고온 가공", "조립"],
    "employee_count": 45,
    "sales_channels": ["B2B", "수출"],
    "export_countries": ["미국", "유럽"]
}
```

### 예상 출력

- **총 규제**: 8개 (HIGH 3개, MEDIUM 3개, LOW 2개)
- **카테고리**: 안전/환경 4개, 제품 인증 2개, 공장 운영 2개
- **체크리스트**: 24개 항목 (규제당 평균 3개)
- **리스크 점수**: 7.2/10 (높음)
- **고위험 규제**: 화학물질관리법, 중대재해처벌법, 산업안전보건법
- **보고서**: 8페이지 PDF (경영진 요약, 상세 분석, 실행 계획 포함)

---

## 🔧 커스터마이징

### 다른 산업 적용

`main()` 함수의 `sample_business_info`를 수정하여 다양한 산업에 적용 가능:

```python
# 화학 제품 제조업
sample_business_info = {
    "industry": "화학 제품 제조",
    "product_name": "산업용 세정제",
    "raw_materials": "황산, 염화수소, 계면활성제",
    "processes": ["화학 반응", "혼합", "포장"],
    "employee_count": 30,
    "sales_channels": ["B2B"],
    "export_countries": []
}
```

### Agent 설정 조정

- **검색 결과 수 조정**: `_build_tavily_tool(max_results=8)` → 원하는 개수로 변경
- **LLM 모델 변경**: `ChatOpenAI(model="gpt-4o-mini")` → `"gpt-4o"` 등으로 변경
- **Temperature 조정**: `temperature=0` (정확성) ↔ `temperature=0.7` (창의성)

---

## ⚠️ 주의사항

### API 비용

- **OpenAI API**: 8개 Agent 실행 시 약 $0.50-$1.00 소요 (입력 토큰 약 20K, 출력 약 10K)
- **Tavily API**: 검색 1회당 1 크레딧 (무료 티어: 월 1,000회)

### 실행 시간

- **정상**: 5-10분 (네트워크 속도, API 응답 시간에 따라 변동)
- **지연 발생 시**: Tavily 검색 결과 수 감소 (`max_results=5`)

### 정확도

- **AI 기반 분석**: 100% 정확성 보장 불가
- **권장 사항**: 전문가 검토 필수, 참고용으로만 사용
- **면책 조항**: 보고서에 자동 포함

---

## 📚 참고 문서

- [agent_prd_v2.md](./agent_prd_v2.md): 제품 요구사항 명세서 (8-Agent 상세 설명)
- [CLAUDE.md](./CLAUDE.md): Claude Code 개발 가이드 (Agent 구현 방법)
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain 공식 문서](https://python.langchain.com/)
- [Tavily API 문서](https://docs.tavily.com/)

---

## 🤝 기여

이슈 및 PR 환영합니다!

---

## 📄 라이선스

MIT License

---

## 📞 문의

프로젝트 관련 문의 사항은 Issues에 등록해주세요.

---

**생성일**: 2025년 10월 21일
**버전**: 2.0 (8-Agent System)
