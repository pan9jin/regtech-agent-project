# 프로젝트 아키텍처

## 시스템 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                    (실행 진입점)                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    workflows/runner.py                           │
│              run_regulation_agent()                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              workflows/graph_builder.py                          │
│                LangGraph Workflow                                │
│                                                                  │
│  START → Analyzer → Search → Classifier → Prioritizer           │
│          → Checklist → Planner → Risk → END                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   agents/    │    │   models/    │    │    utils/    │
│              │    │              │    │              │
│ 8개 Agent    │◄───┤ 데이터 모델   │    │ 헬퍼 함수    │
│ 모듈         │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Agent 실행 흐름

```
1️⃣  Analyzer Agent
    ├─ 입력: BusinessInfo
    ├─ 처리: GPT-4o-mini로 키워드 추출
    └─ 출력: keywords[]

         ↓

2️⃣  Search Agent
    ├─ 입력: keywords[]
    ├─ 처리: Tavily API로 웹 검색
    └─ 출력: search_results[]

         ↓

3️⃣  Classifier Agent
    ├─ 입력: BusinessInfo + search_results[]
    ├─ 처리: GPT-4o-mini로 규제 분류
    └─ 출력: regulations[] (3개 카테고리)

         ↓

4️⃣  Prioritizer Agent
    ├─ 입력: BusinessInfo + regulations[]
    ├─ 처리: GPT-4o-mini로 우선순위 결정
    └─ 출력: regulations[] (HIGH/MEDIUM/LOW)

         ↓

5️⃣  Checklist Generator Agent
    ├─ 입력: regulations[]
    ├─ 처리: GPT-4o-mini로 체크리스트 생성
    └─ 출력: checklists[]

         ↓

6️⃣  Planning Agent
    ├─ 입력: checklists[]
    ├─ 처리: GPT-4o-mini로 실행 계획 수립
    └─ 출력: checklists[] (action_plan 추가)

         ↓

7️⃣  Risk Assessment Agent
    ├─ 입력: regulations[] + BusinessInfo
    ├─ 처리: GPT-4o-mini로 리스크 평가
    └─ 출력: risk_assessment{}

         ↓

8️⃣  Report Generation Agent
    ├─ 입력: 전체 AgentState
    ├─ 처리: 데이터 통합 및 정리
    └─ 출력: final_report{}
```

## 데이터 모델 관계도

```
BusinessInfo
    │
    ├─→ Analyzer → keywords[]
    │
    ├─→ Search → search_results[]
    │
    ├─→ Classifier → Regulation[]
    │                   │
    │                   ├─ id: str
    │                   ├─ name: str
    │                   ├─ category: Category (Enum)
    │                   ├─ priority: Priority (Enum)
    │                   ├─ key_requirements: List[str]
    │                   └─ reference_url: str
    │
    ├─→ Checklist Generator → ChecklistItem[]
    │                             │
    │                             ├─ regulation_id: str
    │                             ├─ task_name: str
    │                             ├─ responsible_dept: str
    │                             ├─ deadline: str
    │                             ├─ method: List[str]
    │                             ├─ action_plan: List[str]
    │                             └─ status: str
    │
    └─→ Risk Assessment → RiskAssessment
                             │
                             ├─ total_risk_score: float
                             ├─ high_risk_items: List[RiskItem]
                             ├─ risk_matrix: Dict
                             └─ recommendations: List[str]
```

## 모듈 의존성

```
main.py
  │
  ├─→ models
  │     ├─ business_info
  │     ├─ regulation
  │     ├─ checklist
  │     ├─ risk_assessment
  │     └─ agent_state
  │
  ├─→ workflows
  │     ├─ runner
  │     ├─ graph_builder
  │     └─ graph_nodes
  │           │
  │           └─→ agents
  │                 ├─ analyzer_agent
  │                 ├─ search_agent
  │                 ├─ classifier_agent
  │                 ├─ prioritizer_agent
  │                 ├─ checklist_generator_agent
  │                 ├─ planning_agent
  │                 ├─ risk_assessment_agent
  │                 └─ report_generation_agent
  │
  └─→ utils
        ├─ tavily_helper
        ├─ text_helper
        └─ output_formatters
```

## 기술 스택

- **LangChain**: LLM 통합 프레임워크
- **LangGraph**: Multi-Agent Workflow 구성
- **OpenAI GPT-4o-mini**: 자연어 처리 및 분석
- **Tavily API**: 실시간 웹 검색
- **LangSmith**: 추적 및 모니터링

## 확장 가능성

### 새로운 Agent 추가
1. `agents/` 디렉토리에 새 Agent 파일 생성
2. `@tool` 데코레이터로 함수 정의
3. `workflows/graph_nodes.py`에 노드 함수 추가
4. `workflows/graph_builder.py`에서 그래프에 노드 및 엣지 추가

### 새로운 데이터 모델 추가
1. `models/` 디렉토리에 TypedDict 정의
2. `models/__init__.py`에 export 추가
3. `models/agent_state.py`의 AgentState에 필드 추가

### 커스텀 분석 로직 추가
각 Agent 파일의 LLM 프롬프트를 수정하여 분석 방식 변경 가능

## 성능 최적화

- **병렬 처리**: 독립적인 Agent는 병렬 실행 가능
- **캐싱**: LangGraph의 MemorySaver로 상태 캐싱
- **토큰 최적화**: 검색 결과 truncate로 토큰 사용량 감소

## 보안 고려사항

- API 키는 `.env` 파일에서 관리
- `.gitignore`에 `.env` 추가 필수
- 민감한 사업 정보는 로그에서 제외
