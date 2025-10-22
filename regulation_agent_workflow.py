"""
규제 AI Agent 서비스 - LangGraph Multi-Agent Workflow
8개의 Agent로 구성된 규제 분석 시스템
- Analyzer Agent: 사업 정보 분석 및 키워드 추출
- Search Agent: Tavily API를 통한 규제 정보 검색
- Classifier Agent: 검색된 규제 분류 및 적용성 판단
- Prioritizer Agent: 규제 우선순위 결정 (HIGH/MEDIUM/LOW)
- Checklist Generator Agent: 규제별 실행 가능한 체크리스트 생성
- Planning Agent: 체크리스트별 구체적인 실행 계획 수립
- Risk Assessment Agent: 미준수 시 리스크 평가 및 완화 방안 제시
- Report Generation Agent: 최종 보고서 작성 및 요약
"""

import os
import json
from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from enum import Enum
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client

# 환경 변수 로드
load_dotenv()

# LangSmith API 클라이언트 생성
client = Client()

# ============================================
# 데이터 모델 정의
# ============================================

class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(str, Enum):
    SAFETY_ENV = "안전/환경"
    PRODUCT_CERT = "제품 인증"
    FACTORY_OPS = "공장 운영"


class BusinessInfo(TypedDict, total=False):
    """사업 정보 데이터 구조"""
    industry: str
    product_name: str
    raw_materials: str
    processes: List[str]
    employee_count: int
    sales_channels: List[str]
    export_countries: List[str]


class Regulation(TypedDict):
    """규제 정보 데이터 구조"""
    id: str
    name: str
    category: str
    why_applicable: str
    authority: str
    priority: str
    key_requirements: List[str]
    reference_url: Optional[str]


class ChecklistItem(TypedDict):
    """체크리스트 항목 데이터 구조"""
    regulation_id: str          # 연결된 규제 ID
    regulation_name: str        # 규제명
    task_name: str              # 작업명
    responsible_dept: str       # 담당 부서
    deadline: str               # 마감 기한
    method: List[str]           # 실행 방법 (단계별)
    action_plan: List[str]      # 구체적인 실행 계획
    estimated_time: str         # 소요 시간
    priority: str               # 우선순위 (상위 규제와 동일)
    status: str                 # 상태 (pending/in_progress/completed)



class RiskItem(TypedDict):
    """리스크 항목 데이터 구조"""
    regulation_id: str          # 규제 ID
    regulation_name: str        # 규제명
    penalty_amount: str         # 벌금액
    penalty_type: str           # 벌칙 유형 (벌금/징역/과태료)
    business_impact: str        # 사업 영향 (영업정지/인허가 취소 등)
    risk_score: float           # 리스크 점수 (0-10)
    past_cases: List[str]       # 과거 처벌 사례
    mitigation: str             # 리스크 완화 방안


class RiskAssessment(TypedDict):
    """리스크 평가 결과 데이터 구조"""
    total_risk_score: float             # 전체 리스크 점수 (0-10)
    high_risk_items: List[RiskItem]     # 고위험 항목 (점수 7.0 이상)
    risk_matrix: Dict[str, Any]         # 리스크 매트릭스
    recommendations: List[str]          # 권장 사항


class AgentState(TypedDict, total=False):
    """LangGraph State - Agent 간 데이터 전달"""
    # 기존 필드
    business_info: BusinessInfo
    keywords: List[str]
    search_results: List[Dict[str, Any]]
    regulations: List[Regulation]
    final_output: Dict[str, Any]

    # 추가 필드 (3개 새로운 Agent)
    checklists: List[ChecklistItem]     # 체크리스트 목록
    risk_assessment: RiskAssessment     # 리스크 평가 결과


# ============================================
# Helper 함수들
# ============================================

def _build_tavily_tool(max_results: int = 8, search_depth: str = "basic") -> TavilySearch:
    """TavilySearch 인스턴스를 생성합니다."""
    try:
        return TavilySearch(
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            search_depth=search_depth,
        )
    except Exception as exc:
        raise RuntimeError(
            "TavilySearch 초기화에 실패했습니다. 환경 변수 'TAVILY_API_KEY'를 확인하세요."
        ) from exc


def _extract_results(payload: Any) -> List[Dict[str, Any]]:
    """Tavily API 응답에서 결과 목록을 추출합니다."""
    if isinstance(payload, dict) and "results" in payload:
        return payload.get("results", []) or []
    if isinstance(payload, dict) and {"title", "url"}.issubset(payload.keys()):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def _truncate(text: str, limit: int = 300) -> str:
    """텍스트를 지정된 길이로 자릅니다."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."



# ============================================
# Tool 정의 (기존 4개 + 신규 3개 Agent)
# ============================================

@tool
def analyze_business(business_info: BusinessInfo) -> Dict[str, Any]:
    """사업 정보를 분석하여 규제 검색용 키워드를 추출합니다.

    Args:
        business_info: 사업 정보 (업종, 제품명, 원자재 등)

    Returns:
        추출된 키워드 목록
    """
    print("🔍 [Analyzer Agent] 사업 정보 분석 중...")
    print(f"   업종: {business_info['industry']}")
    print(f"   제품: {business_info['product_name']}")
    print(f"   원자재: {business_info['raw_materials']}")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
다음 사업 정보를 분석하여 규제 검색에 필요한 핵심 키워드를 추출하세요.

업종: {business_info['industry']}
제품명: {business_info['product_name']}
원자재: {business_info['raw_materials']}
제조 공정: {', '.join(business_info.get('processes', []))}
직원 수: {business_info.get('employee_count', 0)}
판매 방식: {', '.join(business_info.get('sales_channels', []))}

규제와 관련된 키워드를 5-7개 추출하되, 다음을 포함해야 합니다:
- 제품/산업 관련 키워드
- 안전/환경 관련 키워드
- 인증/허가 관련 키워드

출력 형식: 키워드를 쉼표로 구분하여 나열하세요.
예시: 배터리, 화학물질, 산업안전, 제품인증, 유해물질
"""

    response = llm.invoke(prompt)
    keywords = [k.strip() for k in response.content.split(',')]

    print(f"   ✓ 추출된 키워드 ({len(keywords)}개): {keywords}\n")

    return {"keywords": keywords}


@tool
def search_regulations(keywords: List[str]) -> Dict[str, Any]:
    """Tavily API를 사용하여 관련 규제 정보를 웹에서 검색합니다.

    Args:
        keywords: 검색 키워드 목록

    Returns:
        검색된 규제 정보 목록
    """
    print("🌐 [Search Agent] Tavily로 규제 정보 검색 중...")
    print(f"   검색 키워드: {', '.join(keywords[:3])}...")

    # TavilySearch 도구 생성
    tavily_tool = _build_tavily_tool(max_results=8, search_depth="advanced")

    # 검색 쿼리 생성
    query = f"{' '.join(keywords)} 제조업 규제 법률 안전 인증 한국"

    # Tavily 검색 실행
    raw = tavily_tool.invoke({"query": query})

    # 결과 추출
    search_results = _extract_results(raw)

    print(f"   ✓ 검색 결과: {len(search_results)}개 문서 발견")
    for idx, result in enumerate(search_results[:3], 1):
        print(f"      {idx}. {result.get('title', 'N/A')[:60]}...")
    if len(search_results) > 3:
        print(f"      ... 외 {len(search_results) - 3}개\n")
    else:
        print()

    # 검색 결과 구조화
    structured_results = []
    for item in search_results:
        structured_results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": _truncate(item.get("content", ""), 300),
            "score": item.get("score", 0.0),
        })

    return {"search_results": structured_results}


@tool
def classify_regulations(
    business_info: BusinessInfo,
    search_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """검색 결과를 분석하여 적용 가능한 규제를 3개 카테고리로 분류합니다.

    Args:
        business_info: 사업 정보
        search_results: 검색된 규제 정보

    Returns:
        분류된 규제 목록
    """
    print("📋 [Classifier Agent] 규제 분류 및 적용성 판단 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    # 검색 결과를 텍스트로 정리
    search_summary = "\n\n".join([
        f"문서 {i+1}: {r.get('title', '')}\n{r.get('content', '')[:300]}..."
        for i, r in enumerate(search_results[:5])
    ])

    prompt = f"""
다음 사업 정보에 적용될 수 있는 규제를 분석하여 분류하세요.

[사업 정보]
업종: {business_info['industry']}
제품: {business_info['product_name']}
원자재: {business_info['raw_materials']}
공정: {', '.join(business_info.get('processes', []))}
직원 수: {business_info.get('employee_count', 0)}명

[검색된 규제 정보]
{search_summary}

위 정보를 바탕으로 적용 가능한 주요 규제 5-8개를 식별하고, 다음 3가지 카테고리로 분류하세요:
1. 안전/환경
2. 제품 인증
3. 공장 운영

각 규제는 다음 JSON 형식으로 출력하세요:
{{
    "name": "규제명 (예: 화학물질관리법)",
    "category": "카테고리 (안전/환경, 제품 인증, 공장 운영 중 하나)",
    "why_applicable": "이 사업에 적용되는 이유를 1-2문장으로 설명",
    "authority": "관할 기관 (예: 환경부)",
    "key_requirements": ["필수 요구사항 1", "필수 요구사항 2"],
    "reference_url": "관련 URL (검색 결과에서 가져오거나 없으면 빈 문자열)"
}}

출력은 JSON 배열 형식으로만 작성하세요. 설명은 포함하지 마세요.
"""

    response = llm.invoke(prompt)

    try:
        # JSON 파싱
        content = response.content.strip()
        # 마크다운 코드블록 제거
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        regulations_data = json.loads(content.strip())

        # Regulation 형식으로 변환
        regulations = []
        for idx, reg in enumerate(regulations_data, 1):
            regulations.append({
                "id": f"REG-{idx:03d}",
                "name": reg.get("name", "미지정"),
                "category": reg.get("category", "안전/환경"),
                "why_applicable": reg.get("why_applicable", ""),
                "authority": reg.get("authority", "미지정"),
                "priority": "MEDIUM",  # 기본값, Prioritizer에서 결정
                "key_requirements": reg.get("key_requirements", []),
                "reference_url": reg.get("reference_url", "")
            })

        # 카테고리별 개수 계산
        category_count = {}
        for reg in regulations:
            cat = reg['category']
            category_count[cat] = category_count.get(cat, 0) + 1

        print(f"   ✓ 규제 분류 완료: 총 {len(regulations)}개")
        for cat, count in category_count.items():
            print(f"      - {cat}: {count}개")
        print()

        return {"regulations": regulations}

    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON 파싱 오류: {e}")
        print(f"   응답 내용: {response.content[:200]}...")
        return {"regulations": []}


@tool
def prioritize_regulations(
    business_info: BusinessInfo,
    regulations: List[Regulation]
) -> Dict[str, Any]:
    """규제의 위험도를 분석하여 우선순위를 결정합니다 (HIGH/MEDIUM/LOW).

    Args:
        business_info: 사업 정보
        regulations: 분류된 규제 목록

    Returns:
        우선순위가 지정된 규제 목록
    """
    print("⚡ [Prioritizer Agent] 우선순위 결정 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 규제 목록을 텍스트로 정리
    regulations_summary = "\n".join([
        f"{i+1}. {r['name']} ({r['category']})\n   이유: {r['why_applicable']}\n   요구사항: {', '.join(r['key_requirements'][:2])}"
        for i, r in enumerate(regulations)
    ])

    prompt = f"""
다음 규제들의 우선순위를 HIGH, MEDIUM, LOW로 결정하세요.

[사업 정보]
제품: {business_info['product_name']}
직원 수: {business_info.get('employee_count', 0)}명

[규제 목록]
{regulations_summary}

우선순위 기준:
- HIGH: 법정 필수 요구사항, 위반 시 사업 중단/고액 벌금, 즉시 준수 필요
- MEDIUM: 중요하지만 일정 기간 유예 가능, 중간 수준 벌금
- LOW: 권장 사항, 선택적 준수, 낮은 벌금

출력 형식: 각 규제의 우선순위만 줄바꿈으로 구분하여 나열하세요.
예시:
HIGH
MEDIUM
HIGH
LOW
"""

    response = llm.invoke(prompt)
    priorities = [p.strip() for p in response.content.strip().split('\n') if p.strip()]

    # 우선순위 할당
    prioritized_regulations = []
    for idx, reg in enumerate(regulations):
        updated_reg = reg.copy()
        if idx < len(priorities):
            priority = priorities[idx]
            if priority in ["HIGH", "MEDIUM", "LOW"]:
                updated_reg['priority'] = priority
            else:
                updated_reg['priority'] = "MEDIUM"
        else:
            updated_reg['priority'] = "MEDIUM"
        prioritized_regulations.append(updated_reg)

    # 우선순위별 개수 계산
    priority_count = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for reg in prioritized_regulations:
        priority_count[reg['priority']] += 1

    print(f"   ✓ 우선순위 결정 완료:")
    print(f"      - HIGH: {priority_count['HIGH']}개")
    print(f"      - MEDIUM: {priority_count['MEDIUM']}개")
    print(f"      - LOW: {priority_count['LOW']}개\n")

    # 최종 결과 정리
    final_output = {
        "business_info": business_info,
        "total_count": len(prioritized_regulations),
        "regulations": prioritized_regulations,
        "priority_distribution": priority_count
    }

    return {"regulations": prioritized_regulations, "final_output": final_output}


@tool
def generate_checklists(regulations: List[Regulation]) -> Dict[str, Any]:
    """각 규제에 대한 실행 가능한 체크리스트를 생성합니다.

    Args:
        regulations: 우선순위가 결정된 규제 목록

    Returns:
        체크리스트 항목 목록
    """
    print("📝 [Checklist Generator Agent] 규제별 체크리스트 생성 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    all_checklists = []

    for reg in regulations:
        print(f"   {reg['name']} - 체크리스트 생성 중...")

        prompt = f"""
다음 규제를 준수하기 위한 실행 가능한 체크리스트를 생성하세요.

[규제 정보]
규제명: {reg['name']}
카테고리: {reg['category']}
관할 기관: {reg['authority']}
우선순위: {reg['priority']}
적용 이유: {reg['why_applicable']}
주요 요구사항:
{chr(10).join(f'- {req}' for req in reg['key_requirements'])}

중소 제조기업이 실행할 수 있는 구체적인 체크리스트 3-5개 항목을 생성하세요.

각 항목은 다음 JSON 형식으로 작성하세요:
{{
    "task_name": "구체적인 작업명",
    "responsible_dept": "담당 부서 (예: 안전관리팀, 법무팀, 시설관리팀, 인사팀)",
    "deadline": "마감 기한 (예: 사업 개시 전 필수, 연 1회, 분기 1회, 3개월 내)",
    "method": [
        "1. 첫 번째 단계",
        "2. 두 번째 단계",
        "3. 세 번째 단계"
    ],
    "estimated_time": "소요 시간 (예: 20일, 1개월, 3일)"
}}

출력은 JSON 배열 형식으로만 작성하세요. 설명은 포함하지 마세요.
"""

        response = llm.invoke(prompt)

        try:
            # JSON 파싱
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            checklist_items = json.loads(content.strip())

            # ChecklistItem 형식으로 변환
            for item in checklist_items:
                all_checklists.append({
                    "regulation_id": reg['id'],
                    "regulation_name": reg['name'],
                    "task_name": item.get("task_name", ""),
                    "responsible_dept": item.get("responsible_dept", "담당 부서"),
                    "deadline": item.get("deadline", "미정"),
                    "method": item.get("method", []),
                    "action_plan": [],
                    "estimated_time": item.get("estimated_time", "미정"),
                    "priority": reg['priority'],
                    "status": "pending"
                })

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            continue

    print(f"   ✓ 체크리스트 생성 완료: 총 {len(all_checklists)}개 항목\n")

    return {"checklists": all_checklists}


@tool
def create_action_plan(checklist_item: ChecklistItem) -> Dict[str, Any]:
    """체크리스트 항목을 실행하기 위한 구체적인 행동 계획을 생성합니다.

    Args:
        checklist_item: 계획을 수립할 체크리스트 항목

    Returns:
        행동 계획이 포함된 딕셔너리
    """
    print(f"📝 [Planning Agent] '{checklist_item['task_name']}'에 대한 실행 계획 수립 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    prompt = f"""
다음 체크리스트 항목을 이행하기 위한 구체적이고 실행 가능한 단계별 계획을 3~5단계로 작성하세요.

[체크리스트 항목]
- 작업명: {checklist_item['task_name']}
- 담당 부서: {checklist_item['responsible_dept']}
- 마감 기한: {checklist_item['deadline']}
- 규제명: {checklist_item['regulation_name']}

[실행 방법 개요]
{chr(10).join(f'- {m}' for m in checklist_item['method'])}

[출력 형식]
각 단계를 명확하고 간결한 문장으로 작성하세요. 각 단계는 실행 가능한 행동이어야 합니다.

예시:
- 1단계: 관련 법규 및 최신 개정안 확인 (국가법령정보센터 활용)
- 2단계: 내부 규정 및 절차서 현행화
- 3단계: 변경 사항에 대한 전 직원 대상 교육 실시
- 4단계: 교육 이수 현황 및 효과성 점검
- 5단계: 관련 기록 및 문서 보관

출력은 단계별 계획 목록만 포함해야 합니다. (JSON 형식이 아님)
"""

    response = llm.invoke(prompt)
    plan = [p.strip() for p in response.content.strip().split('\n') if p.strip()]

    print(f"   ✓ 실행 계획 수립 완료: {len(plan)} 단계")

    return {"action_plan": plan}



@tool
def assess_risks(
    regulations: List[Regulation],
    business_info: BusinessInfo
) -> Dict[str, Any]:
    """규제 미준수 시 리스크를 평가합니다.

    Args:
        regulations: 규제 목록
        business_info: 사업 정보

    Returns:
        리스크 평가 결과
    """
    print("⚠️  [Risk Assessment Agent] 리스크 평가 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    risk_items = []

    for reg in regulations:
        print(f"   {reg['name']} - 리스크 분석 중...")

        prompt = f"""
다음 규제를 준수하지 않았을 때의 리스크를 평가하세요.

[규제 정보]
규제명: {reg['name']}
카테고리: {reg['category']}
관할 기관: {reg['authority']}
우선순위: {reg['priority']}
적용 이유: {reg['why_applicable']}

[사업 정보]
제품: {business_info['product_name']}
직원 수: {business_info.get('employee_count', 0)}명

다음 정보를 JSON 형식으로 제공하세요:
{{
    "penalty_amount": "벌금액 (예: 최대 1억원, 300만원 이하)",
    "penalty_type": "벌칙 유형 (예: 형사처벌, 과태료, 행정처분)",
    "business_impact": "사업 영향 (예: 영업정지 6개월, 인허가 취소, 입찰 제한)",
    "risk_score": 리스크 점수 (0-10, 숫자만),
    "past_cases": [
        "과거 처벌 사례 1 (연도, 기업, 처벌 내용)",
        "과거 처벌 사례 2"
    ],
    "mitigation": "리스크 완화 방안 (1-2문장)"
}}

출력은 JSON 형식으로만 작성하세요.
"""

        response = llm.invoke(prompt)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            risk_data = json.loads(content.strip())

            risk_item: RiskItem = {
                "regulation_id": reg['id'],
                "regulation_name": reg['name'],
                "penalty_amount": risk_data.get("penalty_amount", "미상"),
                "penalty_type": risk_data.get("penalty_type", "미상"),
                "business_impact": risk_data.get("business_impact", "미상"),
                "risk_score": float(risk_data.get("risk_score", 5.0)),
                "past_cases": risk_data.get("past_cases", []),
                "mitigation": risk_data.get("mitigation", "")
            }

            risk_items.append(risk_item)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"      ⚠️  파싱 오류: {e}")
            # 기본 리스크 아이템 추가
            risk_items.append({
                "regulation_id": reg['id'],
                "regulation_name": reg['name'],
                "penalty_amount": "미상",
                "penalty_type": "미상",
                "business_impact": "미상",
                "risk_score": 5.0,
                "past_cases": [],
                "mitigation": "전문가 상담 권장"
            })

    # 전체 리스크 점수 계산 (가중 평균)
    if risk_items:
        total_risk_score = sum(item['risk_score'] for item in risk_items) / len(risk_items)
    else:
        total_risk_score = 0.0

    # 고위험 항목 필터링 (7.0 이상)
    high_risk_items = [item for item in risk_items if item['risk_score'] >= 7.0]

    # 권장 사항 생성
    recommendations = []
    if high_risk_items:
        recommendations.append(f"고위험 규제 {len(high_risk_items)}개 - 즉시 준수 조치 시작 필요")
    if total_risk_score >= 7.0:
        recommendations.append("배상책임보험 가입 강력 권장")

    # regulations에서 HIGH 우선순위 확인
    high_priority_count = sum(1 for reg in regulations if reg.get('priority') == 'HIGH')
    if high_priority_count > 0:
        recommendations.append(f"HIGH 우선순위 규제 {high_priority_count}개 - 사업 개시 전 필수 완료")

    recommendations.append("월 1회 준수 현황 점검 체계 수립 권장")

    # 리스크 매트릭스 (우선순위 x 리스크 점수)
    risk_matrix = {
        "HIGH": [item for item in risk_items if item['risk_score'] >= 7.0],
        "MEDIUM": [item for item in risk_items if 4.0 <= item['risk_score'] < 7.0],
        "LOW": [item for item in risk_items if item['risk_score'] < 4.0]
    }

    risk_assessment: RiskAssessment = {
        "total_risk_score": round(total_risk_score, 2),
        "high_risk_items": high_risk_items,
        "risk_matrix": risk_matrix,
        "recommendations": recommendations
    }

    print(f"   ✓ 리스크 평가 완료: 전체 점수 {total_risk_score:.1f}/10")
    print(f"      - 고위험 항목: {len(high_risk_items)}개\n")

    return {"risk_assessment": risk_assessment}


# ============================================
# LangGraph 노드 - 각 Tool을 호출하고 상태를 업데이트
# ============================================

def analyzer_node(state: AgentState) -> Dict[str, Any]:
    """분석 노드: 사업 정보를 분석하여 키워드를 추출합니다."""
    result = analyze_business.invoke({"business_info": state["business_info"]})
    return {"keywords": result["keywords"]}


def search_node(state: AgentState) -> Dict[str, Any]:
    """검색 노드: 키워드를 사용하여 규제 정보를 검색합니다."""
    result = search_regulations.invoke({"keywords": state["keywords"]})
    return {"search_results": result["search_results"]}


def classifier_node(state: AgentState) -> Dict[str, Any]:
    """분류 노드: 검색 결과를 분석하여 규제를 분류합니다."""
    result = classify_regulations.invoke({
        "business_info": state["business_info"],
        "search_results": state["search_results"]
    })
    return {"regulations": result["regulations"]}


def prioritizer_node(state: AgentState) -> Dict[str, Any]:
    """우선순위 노드: 규제의 우선순위를 결정합니다."""
    result = prioritize_regulations.invoke({
        "business_info": state["business_info"],
        "regulations": state["regulations"]
    })
    return {
        "regulations": result["regulations"],
        "final_output": result["final_output"]
    }


def checklist_generator_node(state: AgentState) -> Dict[str, Any]:


    """체크리스트 생성 노드: 규제별 실행 체크리스트를 생성합니다."""


    result = generate_checklists.invoke({"regulations": state["regulations"]})


    return {"checklists": result["checklists"]}








def planning_node(state: AgentState) -> Dict[str, Any]:


    """계획 노드: 각 체크리스트 항목에 대한 실행 계획을 수립합니다."""


    updated_checklists = []


    for item in state["checklists"]:


        result = create_action_plan.invoke({"checklist_item": item})


        item["action_plan"] = result["action_plan"]


        updated_checklists.append(item)


    return {"checklists": updated_checklists}








def risk_assessor_node(state: AgentState) -> Dict[str, Any]:
    """리스크 평가 노드: 미준수 시 리스크를 평가합니다."""
    result = assess_risks.invoke({
        "regulations": state["regulations"],
        "business_info": state["business_info"]
    })
    return {"risk_assessment": result["risk_assessment"]}


# ============================================
# 그래프 빌드 및 실행
# ============================================

def build_workflow() -> StateGraph:
    """LangGraph 워크플로우를 구성합니다.

    실행 순서:
    1. analyzer: 사업 정보 분석 및 키워드 추출
    2. searcher: Tavily로 규제 검색
    3. classifier: 규제 분류
    4. prioritizer: 우선순위 결정
    5. checklist_generator: 규제별 체크리스트 생성
    6. planner: 체크리스트별 실행 계획 수립
    7. risk_assessor: 리스크 평가
    """
    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("searcher", search_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("prioritizer", prioritizer_node)
    graph.add_node("checklist_generator", checklist_generator_node)
    graph.add_node("planner", planning_node)
    graph.add_node("risk_assessor", risk_assessor_node)

    # 엣지 추가: 순차 실행
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "searcher")
    graph.add_edge("searcher", "classifier")
    graph.add_edge("classifier", "prioritizer")
    graph.add_edge("prioritizer", "checklist_generator")
    graph.add_edge("checklist_generator", "planner")
    graph.add_edge("planner", "risk_assessor")
    graph.add_edge("risk_assessor", END)

    return graph


def run_regulation_agent(business_info: BusinessInfo) -> AgentState:
    """규제 AI Agent를 실행합니다.

    Args:
        business_info: 사업 정보

    Returns:
        최종 상태 객체 (분석 결과 포함)
    """
    # 워크플로우 빌드 및 컴파일
    workflow = build_workflow()
    app = workflow.compile(checkpointer=MemorySaver())

    # 초기 상태 설정
    initial_state: AgentState = {
        "business_info": business_info,
        "keywords": [],
        "search_results": [],
        "regulations": [],
        "final_output": {},
        # 새로운 필드 초기화
        "checklists": [],
        "risk_assessment": {
            "total_risk_score": 0.0,
            "high_risk_items": [],
            "risk_matrix": {},
            "recommendations": []
        }
    }

    # 워크플로우 실행
    config = {"configurable": {"thread_id": "regulation_agent_v3"}}
    return app.invoke(initial_state, config=config)


# ============================================
# 출력 헬퍼 함수들
# ============================================

def print_checklists(checklists: List[ChecklistItem]):
    """체크리스트를 보기 좋게 출력합니다."""
    print("📋 실행 체크리스트")
    print("=" * 60)
    print(f"총 {len(checklists)}개 항목\n")

    # 규제별로 그룹핑
    checklists_by_regulation = {}
    for item in checklists:
        reg_id = item['regulation_id']
        if reg_id not in checklists_by_regulation:
            checklists_by_regulation[reg_id] = []
        checklists_by_regulation[reg_id].append(item)

    # 출력
    for reg_id, items in checklists_by_regulation.items():
        regulation_name = items[0]['regulation_name']
        priority = items[0]['priority']

        priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        emoji = priority_emoji.get(priority, "⚪")

        print(f"{emoji} [{priority}] {regulation_name}")
        print("-" * 60)

        for idx, item in enumerate(items, 1):
            print(f"\n   {idx}. {item['task_name']}")
            print(f"      담당: {item['responsible_dept']}")
            print(f"      마감: {item['deadline']}")
            print(f"      기간: {item['estimated_time']}")
            if item.get('action_plan'):
                print(f"      실행 계획:")
                for step in item['action_plan']:
                    print(f"         - {step}")
            elif item['method']:
                print(f"      실행 방법:")
                for method in item['method'][:3]:  # 최대 3단계만 표시
                    print(f"         {method}")

        print()



def print_risk_assessment(risk_assessment: RiskAssessment):
    """리스크 평가 결과를 보기 좋게 출력합니다."""
    print("⚠️  리스크 평가")
    print("=" * 60)
    print()

    total_score = risk_assessment.get('total_risk_score', 0)
    risk_level = "낮음" if total_score < 4.0 else "보통" if total_score < 7.0 else "높음"
    risk_emoji = "🟢" if total_score < 4.0 else "🟡" if total_score < 7.0 else "🔴"

    print(f"{risk_emoji} 전체 리스크 점수: {total_score:.1f}/10 ({risk_level})\n")

    # 고위험 항목
    high_risk_items = risk_assessment.get('high_risk_items', [])
    if high_risk_items:
        print(f"🚨 고위험 규제 ({len(high_risk_items)}개):")
        print("-" * 60)
        for item in high_risk_items:
            print(f"\n   [{item['risk_score']:.1f}] {item['regulation_name']}")
            print(f"      벌칙: {item['penalty_type']} - {item['penalty_amount']}")
            print(f"      영향: {item['business_impact']}")
            if item['past_cases']:
                print(f"      과거 사례:")
                for case in item['past_cases'][:2]:
                    print(f"         - {case}")
            if item['mitigation']:
                print(f"      완화 방안: {item['mitigation']}")
        print()

    # 권장 사항
    recommendations = risk_assessment.get('recommendations', [])
    if recommendations:
        print("💡 권장 사항:")
        for rec in recommendations:
            print(f"   • {rec}")
        print()


# ============================================
# Main 실행 함수
# ============================================

def main():
    """샘플 데이터로 Workflow 실행"""

    print("=" * 60)
    print("🤖 규제 AI Agent 시스템 시작")
    print("=" * 60)
    print()

    # 샘플 사업 정보 (배터리 제조업)
    sample_business_info: BusinessInfo = {
        "industry": "배터리 제조",
        "product_name": "리튬이온 배터리",
        "raw_materials": "리튬, 코발트, 니켈",
        "processes": ["화학 처리", "고온 가공", "조립"],
        "employee_count": 45,
        "sales_channels": ["B2B", "수출"],
        "export_countries": ["미국", "유럽"]
    }

    print("📝 입력된 사업 정보:")
    print(json.dumps(sample_business_info, indent=2, ensure_ascii=False))
    print()
    print("-" * 60)
    print()

    # Workflow 실행
    try:
        result = run_regulation_agent(sample_business_info)
    except Exception as exc:
        print(f"[ERROR] 분석 파이프라인이 실패했습니다: {exc}")
        raise

    # 최종 결과 출력
    print("=" * 60)
    print("✅ 분석 완료 - 최종 결과")
    print("=" * 60)
    print()

    final_output = result.get('final_output', {})

    print(f"📊 요약")
    print(f"   총 규제 개수: {final_output.get('total_count', 0)}개")
    print(f"   우선순위 분포:")
    priority_dist = final_output.get('priority_distribution', {})
    print(f"      - HIGH: {priority_dist.get('HIGH', 0)}개")
    print(f"      - MEDIUM: {priority_dist.get('MEDIUM', 0)}개")
    print(f"      - LOW: {priority_dist.get('LOW', 0)}개")
    print()

    print("📋 규제 목록 (우선순위 순):")
    print()

    # 우선순위별로 정렬
    regulations = final_output.get('regulations', [])
    priority_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_regulations = sorted(
        regulations,
        key=lambda x: priority_order.get(x['priority'], 2)
    )

    for reg in sorted_regulations:
        priority_emoji = {
            "HIGH": "🔴",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }
        emoji = priority_emoji.get(reg['priority'], "⚪")

        print(f"{emoji} [{reg['priority']}] {reg['name']}")
        print(f"   카테고리: {reg['category']}")
        print(f"   관할: {reg['authority']}")
        print(f"   적용 이유: {reg['why_applicable']}")
        print(f"   주요 요구사항:")
        for req in reg['key_requirements']:
            print(f"      - {req}")
        if reg['reference_url']:
            print(f"   참고: {reg['reference_url']}")
        print()

    print()

    # 새로운 2개 섹션 출력
    print_checklists(result.get('checklists', []))
    print()

    print_risk_assessment(result.get('risk_assessment', {}))

    # JSON 파일로 저장 (모든 데이터 포함)
    complete_output = {
        "business_info": result.get('business_info', {}),
        "summary": {
            "total_regulations": final_output.get('total_count', 0),
            "priority_distribution": priority_dist,
            "total_checklist_items": len(result.get('checklists', [])),
            "risk_score": result.get('risk_assessment', {}).get('total_risk_score', 0.0)
        },
        "regulations": regulations,
        "checklists": result.get('checklists', []),
        "risk_assessment": result.get('risk_assessment', {})
    }

    output_file = "regulation_analysis_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_output, f, indent=2, ensure_ascii=False)

    print(f"💾 전체 결과가 '{output_file}' 파일로 저장되었습니다.")
    print()


if __name__ == "__main__":
    main()
