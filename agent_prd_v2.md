# 규제 AI Agent 서비스 - 제품 요구사항 명세서 (PRD)

**문서 버전**: 2.0 (3일 MVP)  
**작성일**: 2025년 10월 20일  
**개발 기간**: 3일  
**서비스명**: RegTech Assistant (가칭)  
**슬로건**: "규제를 이해하고, 준수를 자동화하다"
**PRD**: @agent_prd_v2.md

---

## 1. 개요 (Executive Summary)

### 1.1 서비스 설명
RegTech Assistant는 중소 제조기업이 복잡한 규제 환경에서 안전하게 사업을 운영할 수 있도록 돕는 AI 기반 규제 준수 보조 서비스입니다. 기업의 사업 정보를 입력하면 AI가 적용 가능한 규제를 자동으로 식별하고, 준수해야 할 항목을 체크리스트로 제공합니다.

### 1.2 핵심 가치 제안 (MVP)
- **빠른 규제 파악**: 사업 정보 입력 후 5분 내 적용 규제 확인
- **자동화된 체크리스트**: AI가 생성한 실행 가능한 준수 체크리스트
- **근거 기반 정보**: 웹 검색을 통한 최신 규제 정보 제공

### 1.3 MVP 범위
이 문서는 **3일 내 구현 가능한 최소 기능 제품(MVP)**을 정의합니다. 확장성, 보안, 대규모 사용자 지원은 향후 버전에서 고려합니다.

---

## 2. 목표 및 배경 (Goals & Background)

### 2.1 MVP 목표 (3일)
1. **Day 1**: 기본 UI 및 사업 정보 입력 폼 완성
2. **Day 2**: AI Agent 규제 매핑 로직 구현
3. **Day 3**: 체크리스트 생성 및 결과 화면 완성

**성공 기준**:
- 사업 정보 입력 → 규제 목록 출력까지 동작
- 최소 10개 주요 규제 커버
- 기본적인 체크리스트 생성 가능

### 2.2 문제 정의 (간소화)
- 중소 제조기업은 어떤 규제가 적용되는지 파악하기 어려움
- 규제 조사에 많은 시간 소요 (평균 2-3일)
- 전담 법무팀 없어 규제 위반 리스크 높음

### 2.3 핵심 해결 방안
AI Agent가 사업 정보를 분석하여 자동으로 적용 규제를 식별하고, 실행 가능한 체크리스트를 5분 내 제공

---

## 3. 타겟 사용자 (Target Users)

### 3.1 Primary User (MVP)
**중소 제조기업 담당자**
- CEO, 기획담당자, 법무담당자
- 목표: 사업에 적용되는 규제 빠르게 파악
- Pain Point: 규제 조사 시간 부족, 전문 지식 부족

### 3.2 User Scenario (MVP)
1. 웹사이트 접속
2. 사업 정보 입력 (5분)
   - 업종, 제품명, 원자재, 공정, 직원 수, 판매 방식
3. AI 분석 대기 (3-5분)
4. 결과 확인
   - 적용 규제 목록 (우선순위별)
   - 규제별 체크리스트
   - 관련 법령 링크

---

## 4. 핵심 기능 (Core Features - MVP)

### 4.1 Feature 1: 사업 정보 입력 폼 (Day 1)
**설명**: 간단한 웹 폼으로 사업 정보 수집

**입력 항목** (필수만):
```
- 업종 (드롭다운): 제조업 > 세부 업종 선택
- 제품명 (텍스트): 예) "리튬이온 배터리"
- 주요 원자재 (텍스트): 예) "리튬, 코발트"
- 제조 공정 (체크박스): 
  □ 화학 처리  □ 고온 가공  □ 절삭/가공  □ 조립
- 직원 수 (숫자): 예) 30명
- 판매 방식 (체크박스):
  □ B2B  □ B2C  □ 수출 (국가명)
```

**기술 구현**:
- Vue.js + Tailwind CSS로 반응형 폼
- 폼 유효성 검사 (클라이언트 사이드)
- FastAPI로 데이터 수신 및 JSON 저장

**Success Criteria**:
- 폼 완성 시간 5분 이내
- 모바일/데스크톱 모두 작동

---

### 4.2 Feature 2: AI Agent 규제 매핑 (Day 2)
**설명**: LangGraph 기반 Multi-Agent가 규제를 식별하고 분석

**Agent 구조**:
```python
# LangGraph Workflow
1. Analyzer Agent: 입력 데이터 분석 및 키워드 추출
2. Search Agent: Tavily API로 관련 규제 웹 검색
3. Classifier Agent: 규제를 3개 영역으로 분류
   - 안전/환경
   - 제품 인증  
   - 공장 운영
4. Prioritizer Agent: 위험도 기반 우선순위 결정
```

**처리 로직**:
```python
# 규제 매핑 규칙 (간소화)
REGULATION_KEYWORDS = {
    "배터리": ["전기용품안전관리법", "자원순환법"],
    "화학": ["화학물질관리법", "산업안전보건법"],
    "리튬": ["화학물질관리법", "위험물안전관리법"],
    "50인이상": ["중대재해처벌법"],
    "수출": ["대외무역법"]
}

# Tavily 검색 쿼리 생성
def generate_search_query(product, materials, process):
    return f"{product} {materials} 제조업 규제 법률 안전 인증"
```

**출력 형식**:
```json
{
  "regulations": [
    {
      "id": "REG-001",
      "name": "화학물질관리법",
      "category": "안전/환경",
      "why_applicable": "리튬, 코발트 등 유해화학물질 사용",
      "authority": "환경부",
      "priority": "HIGH",
      "key_requirements": [
        "유해화학물질 영업허가 필요",
        "화학물질 취급시설 기준 준수"
      ],
      "reference_url": "https://..."
    }
  ],
  "total_count": 8,
  "processing_time": "4.2초"
}
```

**기술 구현**:
- LangChain + LangGraph로 Agent Workflow 구성
- OpenAI GPT-4 사용 (분석 및 분류)
- Tavily API로 최신 규제 정보 검색
- 결과를 JSON으로 반환

**Success Criteria**:
- 처리 시간 5분 이내
- 최소 5개 이상 규제 식별
- 카테고리 분류 정확도 80% 이상

---

### 4.3 Feature 3: 체크리스트 생성 (Day 3)
**설명**: 식별된 규제별로 실행 가능한 체크리스트 자동 생성

**체크리스트 구성**:
```markdown
## [HIGH] 화학물질관리법

### 필수 조치사항
- [ ] 유해화학물질 영업허가 취득
  - 담당: 안전관리팀
  - 마감: 사업 개시 전 필수
  - 방법: 화학물질안전원 온라인 신청
  - 비용: 약 30만원
  - 소요기간: 약 20일

- [ ] 화학물질 취급시설 기준 준수
  - 담당: 시설관리팀
  - 마감: 영업허가 신청 전
  - 방법: 시설 자체 점검 후 적합 확인서 발급

- [ ] 정기 안전교육 실시
  - 담당: 인사팀
  - 마감: 연 1회 이상
  - 방법: 한국산업안전보건공단 교육 신청

### 관련 법령
- 화학물질관리법 제28조 (영업허가)
- 화학물질관리법 시행규칙 제29조 (시설기준)

### 위반 시 벌칙
- 영업허가 없이 영업: 5년 이하 징역 또는 1억원 이하 벌금
- 정기교육 미실시: 300만원 이하 과태료
```

**AI 생성 프롬프트**:
```python
prompt = f"""
규제명: {regulation_name}
적용 사유: {why_applicable}
주요 요구사항: {key_requirements}

위 정보를 바탕으로 중소 제조기업이 실행할 수 있는 
구체적인 체크리스트를 생성해주세요.

각 항목은 다음을 포함해야 합니다:
- 구체적인 조치사항
- 담당 부서 (권장)
- 마감 기한
- 실행 방법 (단계별)
- 예상 비용
- 소요 시간

출력 형식은 마크다운으로 작성하세요.
"""
```

**기술 구현**:
- OpenAI GPT-4로 체크리스트 자동 생성
- 마크다운 형식으로 저장
- Vue.js로 체크리스트 렌더링

**Success Criteria**:
- 규제당 평균 3-5개 항목 생성
- 실행 가능한 구체적인 내용 포함
- 마크다운 형식으로 다운로드 가능

---

### 4.4 Feature 4: 결과 화면 (Day 3)
**설명**: 분석 결과를 보기 쉽게 표시

**화면 구성**:
1. **요약 카드**
   - 총 규제 개수
   - 위험도별 분포 (HIGH/MEDIUM/LOW)
   - 예상 준수 기간

2. **규제 목록**
   - 카테고리별 탭 (안전/환경, 제품 인증, 공장 운영)
   - 우선순위 순 정렬
   - 각 규제 클릭 시 상세 정보 표시

3. **체크리스트 뷰어**
   - 규제별 체크리스트 표시
   - 마크다운 렌더링
   - 전체 다운로드 버튼 (PDF/Markdown)

**기술 구현**:
- Vue.js + Tailwind CSS
- Chart.js로 간단한 차트 (선택)
- Markdown 렌더러 (vue-markdown)

**Success Criteria**:
- 직관적인 UI
- 모든 정보를 한 화면에서 확인 가능
- 결과 다운로드 가능

---

## 5. 기술 스택 및 아키텍처 (Tech Stack - MVP)

### 5.1 기술 스택
**Frontend**:
- **Framework**: Vue.js 3 (Composition API)
- **UI Library**: Tailwind CSS
- **빌드 도구**: Vite
- **HTTP Client**: Axios
- **마크다운 렌더러**: marked.js 또는 vue-markdown

**Backend**:
- **Framework**: FastAPI (Python 3.10+)
- **AI/ML**:
  - LangChain: LLM 체이닝 및 프롬프트 관리
  - LangGraph: Multi-Agent Workflow 구성
  - OpenAI API: GPT-4 (분석, 분류, 체크리스트 생성)
- **웹 검색**: Tavily API
- **기타**: Pydantic (데이터 검증), python-dotenv

**Database** (간소화):
- **개발용**: SQLite (로컬)
- **배포용**: PostgreSQL (Railway/Supabase 무료 티어)
- 대안: JSON 파일로 임시 저장 (DB 없이도 가능)

**배포**:
- Frontend: Vercel 또는 Netlify
- Backend: Railway, Render, 또는 fly.io
- 환경변수: .env 파일 관리

### 5.2 시스템 아키텍처 (간소화)

```
┌─────────────────┐
│   Vue.js        │  ← 사용자 인터페이스
│   + Tailwind    │
└────────┬────────┘
         │ HTTP (Axios)
         ↓
┌─────────────────┐
│   FastAPI       │  ← REST API
│   - /analyze    │     (사업 정보 받아 분석)
│   - /checklist  │     (체크리스트 생성)
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────┐
│      LangGraph Workflow          │
│                                  │
│  ┌──────────┐   ┌──────────┐   │
│  │ Analyzer │→→→│ Searcher │   │
│  │  Agent   │   │  Agent   │   │
│  └──────────┘   └────┬─────┘   │
│                      ↓          │
│  ┌──────────┐   ┌──────────┐   │
│  │Priority  │←←←│Classifier│   │
│  │  Agent   │   │  Agent   │   │
│  └──────────┘   └──────────┘   │
│                                  │
│  Powered by: OpenAI + Tavily    │
└─────────────────────────────────┘
         │
         ↓
┌─────────────────┐
│   SQLite/JSON   │  ← 분석 결과 저장 (선택)
└─────────────────┘
```

### 5.3 LangGraph Agent Workflow

```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

# State 정의
class AgentState(TypedDict):
    business_info: dict
    keywords: List[str]
    search_results: List[dict]
    regulations: List[dict]
    checklists: List[dict]

# Agent 노드 정의
def analyzer_agent(state: AgentState):
    """사업 정보 분석 및 키워드 추출"""
    llm = ChatOpenAI(model="gpt-4")
    # ... 분석 로직
    return {"keywords": extracted_keywords}

def search_agent(state: AgentState):
    """Tavily로 규제 정보 검색"""
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    results = tavily.search(
        query=f"{state['keywords']} 제조업 규제 법률",
        max_results=10
    )
    return {"search_results": results}

def classifier_agent(state: AgentState):
    """규제 분류 및 적용성 판단"""
    llm = ChatOpenAI(model="gpt-4")
    # ... 분류 로직
    return {"regulations": classified_regulations}

def prioritizer_agent(state: AgentState):
    """우선순위 결정"""
    # ... 우선순위 로직
    return {"regulations": prioritized_regulations}

# Workflow 구성
workflow = StateGraph(AgentState)
workflow.add_node("analyzer", analyzer_agent)
workflow.add_node("searcher", search_agent)
workflow.add_node("classifier", classifier_agent)
workflow.add_node("prioritizer", prioritizer_agent)

workflow.set_entry_point("analyzer")
workflow.add_edge("analyzer", "searcher")
workflow.add_edge("searcher", "classifier")
workflow.add_edge("classifier", "prioritizer")
workflow.add_edge("prioritizer", END)

app = workflow.compile()
```

### 5.4 API 엔드포인트

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class BusinessInfo(BaseModel):
    industry: str
    product_name: str
    raw_materials: str
    processes: List[str]
    employee_count: int
    sales_channels: List[str]
    export_countries: List[str] = []

@app.post("/api/analyze")
async def analyze_regulations(info: BusinessInfo):
    """
    사업 정보를 받아 규제 분석
    """
    try:
        # LangGraph workflow 실행
        result = await app.ainvoke({
            "business_info": info.dict()
        })
        
        return {
            "success": True,
            "regulations": result["regulations"],
            "processing_time": "4.2초"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/checklist")
async def generate_checklist(regulation_id: str):
    """
    특정 규제의 체크리스트 생성
    """
    # GPT-4로 체크리스트 생성
    # ...
    return {"checklist": checklist_markdown}
```

### 5.5 데이터 모델 (간소화)

```python
# models.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Category(str, Enum):
    SAFETY_ENV = "안전/환경"
    PRODUCT_CERT = "제품 인증"
    FACTORY_OPS = "공장 운영"

class Regulation(BaseModel):
    id: str
    name: str
    category: Category
    why_applicable: str
    authority: str
    priority: Priority
    key_requirements: List[str]
    reference_url: Optional[str]
    penalty: Optional[str]

class ChecklistItem(BaseModel):
    regulation_id: str
    item_name: str
    priority: Priority
    deadline: str
    responsible_dept: str
    method: str
    estimated_cost: Optional[str]
    estimated_time: Optional[str]

class AnalysisResult(BaseModel):
    business_info: dict
    regulations: List[Regulation]
    total_count: int
    processing_time: str
```

---

## 6. 개발 일정 (3일 스프린트)

### Day 1: Frontend 기본 구조 및 입력 폼
**목표**: 사용자가 정보를 입력할 수 있는 UI 완성

**작업 항목**:
- [ ] Vue.js 프로젝트 초기화 (Vite)
- [ ] Tailwind CSS 설정
- [ ] 라우팅 설정 (홈, 입력, 결과 페이지)
- [ ] 사업 정보 입력 폼 UI 구현
  - 업종 선택 드롭다운
  - 제품명, 원자재 입력 필드
  - 제조 공정 체크박스
  - 직원 수, 판매 방식 입력
- [ ] 폼 유효성 검사
- [ ] 로딩 상태 UI (스켈레톤)

**Deliverable**: 동작하는 입력 폼 (로컬)

---

### Day 2: Backend API 및 AI Agent 구현
**목표**: LangGraph 기반 규제 분석 로직 완성

**작업 항목**:
- [ ] FastAPI 프로젝트 초기화
- [ ] 환경변수 설정 (.env)
  - OPENAI_API_KEY
  - TAVILY_API_KEY
- [ ] Pydantic 모델 정의
- [ ] LangGraph Workflow 구현
  - Analyzer Agent
  - Search Agent (Tavily 연동)
  - Classifier Agent
  - Prioritizer Agent
- [ ] API 엔드포인트 구현
  - POST /api/analyze
  - POST /api/checklist
- [ ] CORS 설정 (Frontend 연동)
- [ ] 로컬 테스트

**Deliverable**: 동작하는 API 서버

---

### Day 3: Frontend-Backend 연동 및 결과 화면
**목표**: 전체 플로우 완성 및 배포

**작업 항목**:
- [ ] Frontend-Backend 연동
  - Axios로 API 호출
  - 로딩 상태 처리
  - 에러 핸들링
- [ ] 결과 화면 UI 구현
  - 규제 목록 카드
  - 카테고리별 탭
  - 우선순위 뱃지
- [ ] 체크리스트 뷰어 구현
  - 마크다운 렌더링
  - 다운로드 버튼
- [ ] 반응형 디자인 확인
- [ ] 배포
  - Frontend: Vercel
  - Backend: Railway
- [ ] 최종 테스트

**Deliverable**: 배포된 MVP 서비스

---

## 7. 성공 지표 (MVP)

### 7.1 기능적 지표
- [ ] 사용자가 정보 입력 후 5분 내 결과 확인 가능
- [ ] 최소 10개 주요 제조업 규제 커버
- [ ] 체크리스트 자동 생성 성공
- [ ] 결과 다운로드 가능 (Markdown)

### 7.2 기술적 지표
- [ ] API 응답 시간 < 10초 (규제 분석)
- [ ] Frontend 빌드 성공
- [ ] 배포 완료 (접속 가능한 URL)
- [ ] 모바일/데스크톱 반응형 동작

### 7.3 사용성 지표
- [ ] 내부 팀원 3명 이상 테스트 완료
- [ ] 입력부터 결과 확인까지 끊김 없이 동작
- [ ] 명확한 에러 메시지 표시

---

## 8. 제약사항 및 가정 (MVP)

### 8.1 MVP 제약사항
**범위 제약**:
- 문서 업로드 기능 제외 (향후 구현)
- 사용자 인증/로그인 제외
- 데이터 저장 최소화 (세션 기반 또는 미저장)
- 결과 히스토리 관리 제외

**기술적 제약**:
- AI 모델 정확도 한계 (100% 보장 불가)
- Tavily API 무료 티어 제한 (월 1,000건)
- OpenAI API 비용 (테스트용 크레딧 사용)

**시간 제약**:
- 3일 내 완성이 목표이므로 완벽한 품질보다 동작하는 제품 우선
- 버그는 치명적이지 않으면 차순위

### 8.2 가정
- 사용자는 한국어 사용자
- 제조업 중심 (타 산업은 향후 확장)
- 인터넷 연결 환경
- 최신 브라우저 사용 (Chrome, Safari, Firefox)
- OpenAI API 및 Tavily API 접근 가능

---

## 9. 리스크 및 대응 (MVP)

### 9.1 주요 리스크

**Risk 1: API 응답 시간 초과**
- 영향: 사용자 대기 시간 길어짐
- 대응: 
  - 로딩 애니메이션으로 대기감 완화
  - Tavily 검색 결과 수 제한 (5-10개)
  - 타임아웃 설정 (30초)

**Risk 2: AI 결과 부정확**
- 영향: 잘못된 규제 정보 제공
- 대응:
  - 면책 조항 명시 ("참고용 정보")
  - 출처 링크 제공
  - 사용자 피드백 수집 (향후)

**Risk 3: API 키 비용 초과**
- 영향: 서비스 중단
- 대응:
  - API 호출 수 모니터링
  - 캐싱 전략 (동일 입력 시 재사용)
  - 무료 티어 한도 체크

**Risk 4: 배포 실패**
- 영향: 온라인 접근 불가
- 대응:
  - 로컬에서 완전히 동작 확인 후 배포
  - Vercel/Railway 대신 다른 플랫폼 준비

---

## 10. 향후 개선 사항 (Post-MVP)

### Phase 2: 기능 확장
- 문서 업로드 및 OCR 분석
- 사용자 계정 및 히스토리 관리
- 체크리스트 진행 상황 추적
- 규제 데이터베이스 자체 구축

### Phase 3: 고도화
- 실시간 규제 변경 알림
- AI 챗봇 상담 기능
- 규제 전문가 매칭
- 대시보드 시각화 강화

### Phase 4: 시장 확장
- 타 산업 지원 (건설, 유통, 서비스)
- 다국어 지원 (영어)
- 모바일 앱 개발

---

## 11. 부록

### 11.1 환경 변수 (.env)
```bash
# Backend (.env)
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
FRONTEND_URL=http://localhost:5173
DATABASE_URL=sqlite:///./regtech.db  # 선택사항
```

### 11.2 필수 설치 패키지

**Frontend**:
```bash
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npm install axios marked
```

**Backend**:
```bash
pip install fastapi uvicorn
pip install langchain langchain-openai langgraph
pip install tavily-python
pip install python-dotenv pydantic
```

### 11.3 실행 명령어

**Frontend**:
```bash
npm run dev  # http://localhost:5173
```

**Backend**:
```bash
uvicorn main:app --reload  # http://localhost:8000
```

### 11.4 참고 자료
- Vue.js 공식 문서: https://vuejs.org
- Tailwind CSS: https://tailwindcss.com
- FastAPI 공식 문서: https://fastapi.tiangolo.com
- LangChain 공식 문서: https://python.langchain.com
- LangGraph 튜토리얼: https://langchain-ai.github.io/langgraph
- Tavily API: https://tavily.com
- OpenAI API: https://platform.openai.com

---

## 12. 체크리스트 (개발 전 준비사항)

### 개발 시작 전
- [ ] OpenAI API 키 발급 및 크레딧 확인
- [ ] Tavily API 키 발급
- [ ] Git 저장소 생성
- [ ] 개발 환경 설정 (Node.js, Python)
- [ ] 팀 커뮤니케이션 채널 설정

### Day 1 종료 전
- [ ] 입력 폼 UI 완성
- [ ] 로컬에서 정상 동작 확인
- [ ] Git 커밋 및 푸시

### Day 2 종료 전
- [ ] API 엔드포인트 테스트 완료
- [ ] LangGraph Workflow 동작 확인
- [ ] Postman/Thunder Client로 API 테스트

### Day 3 종료 전
- [ ] Frontend-Backend 연동 완료
- [ ] 배포 완료
- [ ] 팀원 테스트 완료
- [ ] README 작성
