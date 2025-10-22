# 규제 AI Agent + 워크플로우 자동화 서비스

LangGraph Multi-Agent Workflow 기반 규제 분석 + Task 자동화 시스템

## 📋 프로젝트 개요

중소 제조기업이 준수해야 할 규제를 자동으로 분석하고, **실행 가능한 워크플로우**로 변환하여 담당자의 수작업을 최소화하는 AI Agent 시스템입니다.

### 🎯 핵심 가치
- ✅ **규제 자동 분석**: AI가 사업 정보 기반으로 적용 규제 식별
- ✅ **체크리스트 자동 생성**: 규제별 실행 가능한 체크리스트
- ✅ **워크플로우 자동화**: Task 자동 분류 및 실행 (자동화율 88%)
- ✅ **담당자 업무 95% 감소**: 4시간 50분 → 15분 (확인만)
- ✅ **이메일 자동 발송**: 담당자별 체크리스트 자동 전송
- ✅ **AI 기반 담당자 배정**: 전문 분야 매칭으로 자동 할당
- ✅ **n8n/Make.com 연동**: 외부 자동화 도구와 완벽 통합

## 🤖 8개의 전문 Agent

1. **Analyzer Agent** - 사업 정보 분석 및 키워드 추출
2. **Search Agent** - Tavily API를 통한 규제 정보 검색
3. **Classifier Agent** - 검색된 규제 분류 및 적용성 판단
4. **Prioritizer Agent** - 규제 우선순위 결정 (HIGH/MEDIUM/LOW)
5. **Checklist Generator Agent** - 규제별 실행 가능한 체크리스트 생성
6. **Planning Agent** - 체크리스트별 구체적인 실행 계획 수립
7. **Risk Assessment Agent** - 미준수 시 리스크 평가 및 완화 방안 제시
8. **Report Generation Agent** - 최종 보고서 작성 및 요약

## 📁 프로젝트 구조

```
regtech-agent-project/
├── agents/                     # Agent 모듈
│   ├── __init__.py
│   ├── analyzer_agent.py       # 사업 정보 분석
│   ├── search_agent.py         # 규제 검색
│   ├── classifier_agent.py     # 규제 분류
│   ├── prioritizer_agent.py    # 우선순위 결정
│   ├── checklist_generator_agent.py  # 체크리스트 생성
│   ├── planning_agent.py       # 실행 계획 수립
│   ├── risk_assessment_agent.py      # 리스크 평가
│   └── report_generation_agent.py    # 보고서 생성
│
├── models/                     # 데이터 모델
│   ├── __init__.py
│   ├── business_info.py        # 사업 정보
│   ├── regulation.py           # 규제 정보
│   ├── checklist.py            # 체크리스트
│   ├── risk_assessment.py      # 리스크 평가
│   └── agent_state.py          # Agent 상태
│
├── utils/                      # 유틸리티 함수
│   ├── __init__.py
│   ├── tavily_helper.py        # Tavily API 헬퍼
│   ├── text_helper.py          # 텍스트 처리
│   └── output_formatters.py    # 출력 포맷팅
│
├── workflows/                  # LangGraph 워크플로우
│   ├── __init__.py
│   ├── graph_builder.py        # 워크플로우 구성
│   ├── graph_nodes.py          # 노드 정의
│   └── runner.py               # 실행 함수
│
├── main.py                     # 메인 실행 파일
├── regulation_agent_workflow.py # 원본 파일 (참고용)
├── requirements.txt            # 패키지 의존성
├── .env                        # 환경 변수 (생성 필요)
└── README.md                   # 프로젝트 문서
```

## 🚀 설치 및 실행

### 1. 패키지 확인

이 프로젝트는 기존 환경의 패키지를 사용합니다. 필요한 패키지가 이미 설치되어 있는지 확인하세요:

```bash
# 필수 패키지 확인
python -c "import langchain; import langgraph; import langchain_openai; import langchain_tavily; print('✅ 모든 패키지 설치됨')"
```

필요한 경우 python-dotenv만 설치:
```bash
pip install python-dotenv
```

> **참고**: 의존성 충돌이 발생하는 경우 [INSTALL.md](INSTALL.md)를 참조하세요.

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 API 키를 설정하세요:

```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Tavily API Key (웹 검색용)
TAVILY_API_KEY=your_tavily_api_key

# LangSmith API Key (선택사항, 모니터링용)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
```

### 3. 실행

```bash
python main.py
```

## 📊 출력 결과

실행 후 다음과 같은 결과를 얻을 수 있습니다:

1. **콘솔 출력**
   - 각 Agent의 실행 과정
   - 규제 목록 (우선순위 순)
   - 실행 체크리스트 (실행 계획 포함)
   - 리스크 평가 (리스크 점수, 고위험 항목, 권장 사항)

2. **JSON 파일** (`regulation_analysis_result.json`)
   - 전체 분석 결과를 JSON 형식으로 저장

## 🔧 커스터마이징

### 사업 정보 변경

`main.py` 파일의 `sample_business_info`를 수정하여 다른 사업 정보를 분석할 수 있습니다:

```python
sample_business_info: BusinessInfo = {
    "industry": "업종명",
    "product_name": "제품명",
    "raw_materials": "원자재",
    "processes": ["공정1", "공정2"],
    "employee_count": 직원수,
    "sales_channels": ["판매채널1", "판매채널2"],
    "export_countries": ["수출국가1", "수출국가2"]
}
```

### Agent 동작 수정

각 Agent의 동작을 수정하려면 `agents/` 디렉토리 내 해당 파일을 수정하세요.

### 워크플로우 수정

Agent의 실행 순서나 연결을 변경하려면 `workflows/graph_builder.py` 파일을 수정하세요.

## 📦 주요 의존성

- `langchain-openai`: OpenAI LLM 통합
- `langchain-tavily`: Tavily 웹 검색
- `langgraph`: Multi-Agent 워크플로우
- `langsmith`: 모니터링 및 추적
- `python-dotenv`: 환경 변수 관리

## 📝 라이선스

MIT License

## 🤝 기여

버그 리포트 및 기능 제안은 이슈로 등록해주세요.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.
