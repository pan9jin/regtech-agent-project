# RegTech Assistant

**RegTech Assistant**는 중소 제조기업이 복잡한 규제 환경에서 안전하게 사업을 운영할 수 있도록 돕는 AI 기반 규제 준수 자동화 서비스입니다. 사업 정보를 입력하면 AI가 적용 가능한 규제를 자동으로 식별하고, 실행 가능한 체크리스트와 리스크 평가, 통합 보고서를 제공합니다.

### 핵심 가치

- **빠른 규제 파악**: 사업 정보 입력 후 5-10분 내 적용 규제 자동 식별
- **실행 가능한 체크리스트**: 규제별 구체적 준수 항목 자동 생성
- **체계적 실행 계획**: 의존성, 타임라인, 마일스톤 포함 실행 계획
- **리스크 평가**: 미준수 시 벌칙, 영향도 분석 및 완화 방안 제시
- **통합 보고서**: 경영진/실무진/법무팀용 맞춤 보고서 자동 생성 (PDF)
- **모듈화 구조**: 재사용 가능한 Agent 기반 아키텍처

---

## ✅ 주요 기능

- **다중 에이전트 규제 분석**: LangGraph 위에서 9개의 에이전트가 순차 · 병렬로 협업하여 규제를 수집, 분류, 우선순위화합니다.
- **실행 체크리스트 & 계획**: 각 규제에 대해 담당 부서, 마감일, 의존성을 포함한 실행 가능한 항목을 자동 생성합니다.
- **리스크 인텔리전스**: 미준수 시 벌칙·영향·완화 방안을 정량(점수)·정성 정보로 제공합니다.
- **보고서 생성 & 이메일 발송**: 마크다운/HTML/PDF 보고서를 만들고 지정한 수신자에게 Gmail SMTP를 통해 자동 전송합니다.
- **모듈형 구조**: `regtech_agent` 패키지 내부의 에이전트와 노드를 재사용하거나 교체해 확장할 수 있습니다.

---

## 🧠 에이전트 아키텍처

LangGraph 파이프라인은 다음 순서로 실행됩니다.

```
START → Analyzer → Searcher → Classifier → Prioritizer
     ↘︎                                        ↘︎
     Checklist Generator → Planning Agent → Report Generator → Email Notifier → END
                     ↘︎                      ↗
                       Risk Assessor --------
```

| 단계 | 에이전트            | 역할                                                          | 주요 출력           |
| ---- | ------------------- | ------------------------------------------------------------- | ------------------- |
| 1    | Analyzer            | 사업 정보를 분석해 규제 검색 키워드를 5~10개 도출             | 키워드 목록         |
| 2    | Searcher            | Tavily API로 한국 정부/공식 사이트 위주 규제 검색             | 문헌 요약 + 출처 ID |
| 3    | Classifier          | 규제 적용성 판단 및 카테고리화(안전/환경·제품 인증·공장 운영) | 규제 상세 + 근거    |
| 4    | Prioritizer         | 위반 위험도를 고려한 HIGH/MEDIUM/LOW 우선순위 부여            | 정렬된 규제 리스트  |
| 5    | Checklist Generator | 각 규제에 대한 실행 체크리스트(담당, 마감, 방법, 근거) 생성   | 체크리스트 항목     |
| 6    | Planning Agent      | 체크리스트 기반 일정·의존성·마일스톤 계획 작성                | 실행 계획           |
| 7    | Risk Assessor       | 벌칙, 영향도, 과거 사례, 완화 방안을 포함한 리스크 Score 산출 | 리스크 리포트       |
| 8    | Report Generator    | 모든 결과를 통합해 Markdown/HTML/PDF 보고서 작성              | 보고서 파일 경로    |
| 9    | Email Notifier      | 보고서를 Gmail SMTP로 전송 (수신자 CLI 인자/사업 정보)        | 이메일 전송 상태    |

> ⚡️ Checklist Generator ↔ Planning Agent와 Risk Assessor는 병렬 실행되어 전체 처리 시간을 단축합니다.

---

## 🧰 기술 스택

- **언어 & 런타임**: Python 3.11+
- **에이전트 프레임워크**: LangChain, LangGraph
- **LLM**: OpenAI `gpt-4o-mini`
- **검색**: Tavily API (`langchain-tavily`)
- **보고서/PDF**: `markdown`, `weasyprint`
- **환경 변수**: `python-dotenv`
- **메일 전송**: Gmail SMTP

---

## 📁 프로젝트 구조

```
regtech_agent/                     # LangGraph 기반 에이전트 패키지
├── agents/                        # LLM Tool 정의
├── email_utils.py
├── models.py
├── nodes.py
├── utils.py
└── workflow.py

api/                               # FastAPI 엔드포인트 (백엔드 API)
backend/                           # 서버 실행 스크립트
frontend/                          # Vue 3 웹 프론트엔드

run_regtech_agent.py               # CLI 엔트리 포인트
report/                            # 보고서 출력 디렉터리 (자동 생성)
```

---

## ⚙️ 설치 & 실행

1. **필수 조건**

   - Python 3.11 이상
   - OpenAI API 키 (`gpt-4o-mini` 사용 권장)
   - Tavily API 키
   - Gmail 계정 + 앱 비밀번호 (2단계 인증 시 필요)

2. **설치 절차**

   ```bash
   git clone <repository-url>
    cd regulation_agent

   python -m venv regtech
   source regtech/bin/activate  # Windows: regtech\Scripts\activate

   pip install -r requirements.txt
   ```

3. **환경 변수 설정** (`.env`)

   ```bash
   OPENAI_API_KEY=sk-proj-...
   TAVILY_API_KEY=tvly-...
   GMAIL_SENDER_EMAIL=your.account@gmail.com
   GMAIL_APP_PASSWORD=your_app_password  # 앱 비밀번호 또는 SMTP 전용 비밀번호
   # 선택 사항
   REPORT_RECIPIENT_EMAIL=default@company.com
   LANGSMITH_API_KEY=...
   LANGSMITH_TRACING=true
   ```

4. **실행 방법**

   ```bash
   python run_regtech_agent.py [recipient_email]
   ```

   - `recipient_email`을 생략하면 `.env`의 `REPORT_RECIPIENT_EMAIL` 또는 사업 정보의 `contact_email`을 사용합니다.
   - CLI 인자로 전달하면 해당 수신자에게 보고서를 1회 발송합니다.

5. **출력 결과**
   - `regulation_analysis_result.json` : 전체 상태(State) 스냅샷
   - `report/regulation_report_reason.md` : Markdown 보고서
   - `report/regulation_report_reason.pdf` : PDF 보고서
   - 콘솔 로그 : 각 에이전트 진행 상황 및 `email_status`

---

## 📬 이메일 전송 동작

- 메일 본문은 체크리스트/실행 계획 요약, 핵심 인사이트, 다음 단계 제안을 포함한 HTML 템플릿으로 구성됩니다.
- 첨부 파일로 PDF 보고서를 포함하며, 파일이 없을 경우 안내 메시지와 함께 본문만 전송합니다.
- API 요청 시 `email_recipients` 필드 또는 프론트엔드의 쉼표 구분 입력을 통해 여러 수신자에게 동시에 보고서를 전송할 수 있습니다.
- 동일 워크플로에서 중복 발송을 방지하기 위해 `email_status.attempted` 플래그로 1회만 전송합니다.
- Gmail SMTP 정책으로 인해 TLS(587) 연결이 차단되면 `.env`에 `SMTP_USE_SSL=1`, `SMTP_PORT=465`를 추가해 SSL 모드로 전환할 수 있습니다.

---

## 📦 JSON 결과 개요

```json
{
  "business_info": { ... },
  "keywords": [ ... ],
  "regulations": [ ... ],
  "checklists": [ ... ],
  "execution_plans": [ ... ],
  "risk_assessment": {
    "total_risk_score": 7.6,
    "high_risk_items": [ ... ],
    "recommendations": [ ... ]
  },
  "final_report": {
    "executive_summary": "...",
    "report_pdf_path": "report/regulation_report_reason.pdf"
  },
  "email_status": {
    "attempted": true,
    "success": true,
    "recipients": ["user@example.com", "ops@example.com"],
    "details": [
      {"recipient": "user@example.com", "success": true},
      {"recipient": "ops@example.com", "success": true}
    ],
    "attachments": ["regulation_report_reason.pdf"]
  }
}
```

---

## 🔧 커스터마이징 가이드

- **모델 교체**: 각 에이전트 모듈에서 `ChatOpenAI(model=...)` 값을 변경합니다.
- **검색 범위 조정**: `regtech_agent/utils.py`의 `build_tavily_tool()`에서 검색 도메인과 결과 수를 수정합니다.
- **에이전트 확장**: `regtech_agent/workflow.py`의 그래프 정의에 새 노드를 추가하고 `nodes.py`에 대응 함수를 구현합니다.
- **CLI 확장**: `run_regtech_agent.py`에서 사업 정보를 외부 파일/DB 입력으로 교체하거나 결과 경로를 인자로 받을 수 있습니다.

---

## 🧪 운영 팁

- `.env`가 로드되지 않으면 LLM·검색·SMTP 호출이 실패하므로 실행 전 `print(os.environ.get(...))` 등으로 값을 확인하세요.
- LangSmith를 활성화하면 각 에이전트의 프롬프트와 응답을 추적할 수 있습니다.
- PDF 생성 시 시스템에 한글 폰트(Noto Sans CJK 등)가 설치되어 있어야 올바르게 렌더링됩니다.

---

## 🎨 Vue 프론트엔드

`frontend/`는 Vite 기반 Vue 3 애플리케이션으로, FastAPI와 연동해 규제 분석을 시각화합니다.

### 기술 스택

- Vue 3 (Composition API)
- Vite 7
- Pinia (상태 관리)
- Vue Router
- Axios

### 주요 경로

```
frontend/
├── src/
│   ├── api/               # Axios 인스턴스 및 엔드포인트 함수
│   ├── components/        # UI 컴포넌트
│   ├── stores/            # Pinia 스토어
│   ├── views/             # 페이지 뷰 (Analyze/Results/Dashboard)
│   └── main.js            # 앱 진입점
├── public/                # 정적 리소스
├── vite.config.js         # 개발 서버 및 빌드 설정
└── package.json
```

### 환경 설정

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

### 실행 및 빌드

- 개발 서버: `npm run dev` (기본 포트 `http://localhost:5173`)
- 프리뷰: `npm run preview`
- 프로덕션 빌드: `npm run build` (출력은 `frontend/dist/`)

### 주요 화면

1. **규제 분석**(`/analyze`) – 사업 정보 입력, 이메일 옵션, 진행률 표시  
2. **분석 결과**(`/results`) – 우선순위/카테고리별 규제, 체크리스트, PDF 다운로드  
3. **대시보드**(`/dashboard`) – 최근 분석 통계, 시스템 상태 모니터링

> 데모 데이터를 빠르게 확인하려면 `http://localhost:5173/?demo=1`로 접속하세요.

프론트엔드가 백엔드 API를 호출할 수 있도록 `backend/run_server.py`로 FastAPI 서버를 먼저 실행한 뒤 프론트엔드를 띄우는 순서로 개발환경을 구성하면 됩니다.

---

## 🐳 Docker 배포

루트에는 백엔드(`backend/Dockerfile`)와 프론트엔드(`frontend/Dockerfile`)용 멀티 스테이지 Dockerfile이 있으며, WeasyPrint 의존성( cairo/pango/폰트 등)을 포함하도록 구성되어 있습니다. 루트 `.dockerignore`와 `frontend/.dockerignore`로 빌드 컨텍스트를 최소화합니다.

### docker compose로 통합 실행

`docker-compose.yaml`에 두 서비스와 공용 네트워크가 정의되어 있어 한 번의 명령으로 빌드·기동할 수 있습니다.

```bash
docker compose up --build -d
```

- 프로젝트 이름은 `regtech-agent`로 설정되어 컨테이너가 `regtech-backend`, `regtech-frontend`로 생성됩니다.
- `.env` 파일에 OpenAI, Tavily, SMTP 등 필수 환경 변수를 미리 설정해 두세요.
- 백엔드는 `http://localhost:8000`(Swagger UI: `/docs`), 프론트엔드는 `http://localhost:8080`으로 접근합니다.

종료할 때는 `docker compose down`을 사용합니다.

### 수동 빌드·실행(선택)

개별 이미지를 직접 빌드하고 실행하고 싶다면 다음을 참고하세요.

```bash
docker build -f backend/Dockerfile -t regtech-backend .
docker build -f frontend/Dockerfile -t regtech-frontend .

docker network create regtech-net

docker run --rm -d --name regtech-backend --network regtech-net \
  -p 8000:8000 --env-file .env regtech-backend

docker run --rm -d --name regtech-frontend --network regtech-net \
  -p 8080:80 regtech-frontend
```

프론트엔드는 `default.conf`를 통해 `/api/` 호출을 자동으로 `regtech-backend:8000`에 프록시합니다.

---

## 🌐 FastAPI 백엔드

에이전트 워크플로우를 HTTP API 형태로 제공하기 위해 `api/`와 `backend/` 모듈을 추가했습니다. FastAPI는 Swagger UI를 기본 제공하므로, 브라우저에서 엔드포인트를 바로 확인하고 테스트할 수 있습니다.

### 디렉터리 구성

```
api/
├── __init__.py            # FastAPI 애플리케이션 export
├── main.py                # 엔드포인트 정의 및 워크플로우 호출
└── schemas.py             # 요청/응답용 Pydantic 모델

backend/
├── main.py                # FastAPI 앱 진입점 (uvicorn reload 대응)
└── run_server.py          # 개발서버 실행 스크립트
```

### 실행 방법

```bash
python backend/run_server.py
```

- 기본 포트: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc 문서: `http://localhost:8000/redoc`

### 핵심 엔드포인트

- `POST /api/analyze` : `regtech_agent` 워크플로우를 실행하고 규제 분석을 수행합니다.
- `GET /api/analysis/{analysis_id}` : 저장된 분석 결과를 조회합니다.
- `GET /api/download/{analysis_id}` : 분석에서 생성된 PDF 보고서를 다운로드합니다.
- `GET /api/stats` : 최근 분석 결과 기반 통계를 반환합니다.
- `GET /health` : 서비스 상태를 확인합니다.

> ⚠️ 이메일 발송을 사용하려면 `.env`에 Gmail SMTP 정보 또는 다른 SMTP 설정을 반드시 입력해야 합니다. 수신자는 API 요청의 `email_recipients`(쉼표 구분 가능) 또는 사업 정보의 `contact_email` 값을 사용합니다.
