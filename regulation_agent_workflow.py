"""
규제 AI Agent 서비스 - LangGraph Multi-Agent Workflow
8개의 Agent로 구성된 규제 분석 시스템

1. Analyzer Agent: 사업 정보 분석 및 키워드 추출
2. Search Agent: Tavily API를 통한 규제 정보 검색
3. Classifier Agent: 검색된 규제 분류 및 적용성 판단
4. Prioritizer Agent: 규제 우선순위 결정 (HIGH/MEDIUM/LOW)
5. Checklist Generator Agent: 규제별 실행 가능한 체크리스트 생성
6. Planning Agent: 체크리스트 → 실행 계획 변환 (의존성, 타임라인, 마일스톤)
7. Risk Assessment Agent: 미준수 시 리스크 평가 및 완화 방안 제시
8. Report Generation Agent: 최종 통합 보고서 생성 (경영진/실무진/법무팀용)

워크플로우:
START → Analyzer → Searcher → Classifier → Prioritizer
→ Checklist Generator → Planning Agent → Risk Assessor
→ Report Generator → END
"""

import os
import json
from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv
from markdown import markdown
from pathlib import Path
from weasyprint import HTML, CSS

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
    estimated_cost: str         # 예상 비용
    estimated_time: str         # 소요 시간
    priority: str               # 우선순위 (상위 규제와 동일)
    status: str                 # 상태 (pending/in_progress/completed)


class Milestone(TypedDict):
    """마일스톤 데이터 구조"""
    name: str                           # 마일스톤명
    deadline: str                       # 마감일 (예: "1개월 내")
    tasks: List[str]                    # 포함된 작업 ID들
    completion_criteria: str            # 완료 기준


class ExecutionPlan(TypedDict):
    """실행 계획 데이터 구조"""
    plan_id: str                        # 계획 ID
    regulation_id: str                  # 연결된 규제 ID
    regulation_name: str                # 규제명
    checklist_items: List[str]          # 연결된 체크리스트 항목 ID들
    timeline: str                       # 예상 소요 기간 (예: "3개월")
    start_date: str                     # 시작 시점 (예: "즉시", "공장등록 후")
    milestones: List[Milestone]         # 마일스톤 목록
    dependencies: Dict[str, List[str]]  # 선행 작업 의존성 (작업ID: [선행작업ID들])
    parallel_tasks: List[List[str]]     # 병렬 처리 가능한 작업 그룹
    critical_path: List[str]            # 크리티컬 패스 (가장 긴 경로)


class FinalReport(TypedDict):
    """최종 보고서 데이터 구조"""
    executive_summary: str              # 경영진용 요약 (마크다운)
    detailed_report: str                # 실무진용 상세 보고서 (마크다운)
    legal_report: str                   # 법무팀용 규제 상세 (마크다운)
    key_insights: List[str]             # 핵심 인사이트 (3-5개)
    action_items: List[Dict[str, Any]]  # 즉시 조치 항목
    risk_highlights: List[str]          # 주요 리스크 하이라이트
    next_steps: List[str]               # 다음 단계 권장사항
    full_markdown: str                  # 통합 마크다운 보고서 (전체)
    report_pdf_path: str                # PDF 저장 경로


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

    # Agent 결과 필드
    checklists: List[ChecklistItem]     # 체크리스트 목록
    execution_plans: List[ExecutionPlan]  # 실행 계획 (Planning Agent)
    risk_assessment: RiskAssessment     # 리스크 평가 결과
    final_report: FinalReport           # 최종 보고서 (Report Generation Agent)


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


def _format_currency(amount: int) -> str:
    """금액을 한국 통화 형식으로 포맷팅합니다.

    Args:
        amount: 금액 (원)

    Returns:
        포맷된 문자열 (예: "15,000,000원")
    """
    return f"{amount:,}원"


def _parse_cost_from_text(text: str) -> int:
    """텍스트에서 숫자를 추출하여 정수로 변환합니다.

    Args:
        text: 비용이 포함된 텍스트 (예: "약 30만원", "500만원")

    Returns:
        추출된 금액 (원 단위)
    """
    import re

    # "만원" 패턴 추출
    match_man = re.search(r'(\d+(?:,\d+)?)\s*만원', text)
    if match_man:
        return int(match_man.group(1).replace(',', '')) * 10000

    # "원" 패턴 추출
    match_won = re.search(r'(\d+(?:,\d+)?)\s*원', text)
    if match_won:
        return int(match_won.group(1).replace(',', ''))

    # 숫자만 있는 경우
    match_num = re.search(r'(\d+(?:,\d+)?)', text)
    if match_num:
        return int(match_num.group(1).replace(',', ''))

    return 0


def save_report_pdf(markdown_text: str, output_dir: Path) -> Path:
    """Markdown 보고서를 HTML+CSS로 변환하여 PDF로 저장하고,
    원본 markdown도 .md 파일로 함께 저장합니다.

    Args:
        markdown_text: 마크다운 형식의 보고서 텍스트
        output_dir: PDF 저장 디렉토리 경로

    Returns:
        생성된 PDF 파일의 경로
    """
    if not markdown_text.strip():
        raise RuntimeError("생성된 보고서 내용이 비어 있어 PDF를 생성할 수 없습니다.")

    # 출력 디렉토리 생성
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 저장 파일 경로 정의 (동일 베이스 이름으로 md & pdf 생성)
    md_path = output_dir / "regulation_report.md"
    pdf_path = output_dir / "regulation_report.pdf"

    # 1) 원본 마크다운 저장 (존재 시 덮어쓰기)
    md_path.write_text(markdown_text, encoding="utf-8")

    # 2) Markdown → HTML 변환
    html_body = markdown(
        markdown_text,
        extensions=["extra", "toc", "tables", "fenced_code"],
    )

    # 3) PDF 스타일 정의
    css = CSS(
        string="""
        @page { size: A4; margin: 20mm; }
        body { font-family: 'Apple SD Gothic Neo', 'Nanum Gothic', 'Noto Sans CJK KR', sans-serif; font-size: 11pt; line-height: 1.6; }
        h1, h2, h3 { color: #1a237e; }
        h1 { border-bottom: 3px solid #1a237e; padding-bottom: 10px; }
        h2 { border-bottom: 1px solid #9fa8da; padding-bottom: 5px; margin-top: 20px; }
        ul { margin-left: 0; padding-left: 15px; }
        li { margin-bottom: 6px; }
        table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        th, td { border: 1px solid #bdbdbd; padding: 8px; text-align: left; }
        th { background-color: #e8eaf6; font-weight: bold; }
        code, pre { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
        blockquote { border-left: 4px solid #1a237e; padding-left: 10px; color: #555; }
        """
    )

    # 4) HTML 문서 완성 및 PDF 저장 (동일 이름 존재 시 자동 덮어쓰기)
    html_doc = f"""
    <html>
      <head>
        <meta charset='utf-8'>
        <title>규제 준수 분석 보고서</title>
      </head>
      <body>{html_body}</body>
    </html>
    """

    HTML(string=html_doc).write_pdf(target=str(pdf_path), stylesheets=[css])

    print(f"✓ PDF 보고서 저장: {pdf_path}")
    print(f"✓ Markdown 보고서 저장: {md_path}")

    return pdf_path


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
    "estimated_cost": "예상 비용 (예: 30만원, 100만원, 무료)",
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
                    "estimated_cost": item.get("estimated_cost", "미정"),
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
def plan_execution(
    regulations: List[Regulation],
    checklists: List[ChecklistItem]
) -> Dict[str, Any]:
    """체크리스트를 실행 가능한 계획으로 변환합니다.

    Args:
        regulations: 규제 목록
        checklists: 체크리스트 목록

    Returns:
        실행 계획 목록
    """
    print("📅 [Planning Agent] 실행 계획 수립 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 규제별로 체크리스트 그룹핑
    checklists_by_regulation = {}
    for item in checklists:
        reg_id = item['regulation_id']
        if reg_id not in checklists_by_regulation:
            checklists_by_regulation[reg_id] = []
        checklists_by_regulation[reg_id].append(item)

    all_execution_plans = []

    for reg in regulations:
        reg_id = reg['id']
        reg_name = reg['name']
        reg_priority = reg['priority']

        # 해당 규제의 체크리스트 항목들
        reg_checklists = checklists_by_regulation.get(reg_id, [])

        if not reg_checklists:
            continue

        print(f"   {reg_name} - 실행 계획 생성 중...")

        # 체크리스트 요약
        checklist_summary = "\n".join([
            f"{i+1}. {item['task_name']}\n   담당: {item['responsible_dept']}\n   마감: {item['deadline']}\n   기간: {item['estimated_time']}"
            for i, item in enumerate(reg_checklists)
        ])

        prompt = f"""
다음 규제의 체크리스트를 바탕으로 실행 계획을 수립하세요.

[규제 정보]
규제명: {reg_name}
우선순위: {reg_priority}

[체크리스트 항목들]
{checklist_summary}

다음 정보를 분석하여 JSON 형식으로 제공하세요:
1. 전체 예상 소요 기간 (timeline)
2. 시작 시점 (start_date: "즉시", "1개월 내", "공장등록 후" 등)
3. 마일스톤 (3-5개, 각 마일스톤마다 name, deadline, completion_criteria 포함)
4. 작업 간 의존성 (dependencies: 어떤 작업이 먼저 완료되어야 하는지)
5. 병렬 처리 가능한 작업 그룹 (parallel_tasks)
6. 크리티컬 패스 (critical_path: 가장 오래 걸리는 경로의 작업 번호들)

출력 형식:
{{
    "timeline": "3개월",
    "start_date": "즉시",
    "milestones": [
        {{
            "name": "1개월 차: 서류 준비 완료",
            "deadline": "30일 내",
            "tasks": ["1", "2"],
            "completion_criteria": "필요 서류 모두 준비"
        }}
    ],
    "dependencies": {{
        "2": ["1"],
        "3": ["1", "2"]
    }},
    "parallel_tasks": [
        ["1", "2"],
        ["3", "4"]
    ],
    "critical_path": ["1", "2", "5"]
}}

참고:
- 우선순위 HIGH는 즉시 시작
- 우선순위 MEDIUM은 1-3개월 내
- 우선순위 LOW는 6개월 내
- dependencies의 키는 작업 번호(문자열), 값은 선행 작업 번호 리스트
- parallel_tasks는 동시에 진행 가능한 작업 그룹들의 리스트

출력은 JSON 형식으로만 작성하세요.
"""

        response = llm.invoke(prompt)

        try:
            # JSON 파싱
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            plan_data = json.loads(content.strip())

            # ExecutionPlan 형식으로 변환
            execution_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": [str(i+1) for i in range(len(reg_checklists))],
                "timeline": plan_data.get("timeline", "3개월"),
                "start_date": plan_data.get("start_date", "즉시"),
                "milestones": plan_data.get("milestones", []),
                "dependencies": plan_data.get("dependencies", {}),
                "parallel_tasks": plan_data.get("parallel_tasks", []),
                "critical_path": plan_data.get("critical_path", [])
            }

            all_execution_plans.append(execution_plan)

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            # 기본 실행 계획 생성
            default_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": [str(i+1) for i in range(len(reg_checklists))],
                "timeline": "3개월",
                "start_date": "즉시" if reg_priority == "HIGH" else "1개월 내",
                "milestones": [],
                "dependencies": {},
                "parallel_tasks": [],
                "critical_path": []
            }
            all_execution_plans.append(default_plan)

    print(f"   ✓ 실행 계획 수립 완료: 총 {len(all_execution_plans)}개 계획\n")

    return {"execution_plans": all_execution_plans}


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


@tool
def generate_final_report(
    business_info: BusinessInfo,
    regulations: List[Regulation],
    checklists: List[ChecklistItem],
    execution_plans: List[ExecutionPlan],
    risk_assessment: RiskAssessment
) -> Dict[str, Any]:
    """전체 분석 결과를 통합 마크다운 보고서로 작성하고 PDF로 저장합니다.

    Args:
        business_info: 사업 정보
        regulations: 규제 목록
        checklists: 체크리스트
        execution_plans: 실행 계획
        risk_assessment: 리스크 평가

    Returns:
        최종 보고서 (통합 마크다운 + PDF 경로)
    """
    print("📄 [Report Generation Agent] 통합 보고서 생성 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    # === 1. 기본 통계 계산 ===
    priority_count = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    category_count = {}
    for reg in regulations:
        priority_count[reg['priority']] += 1
        cat = reg['category']
        category_count[cat] = category_count.get(cat, 0) + 1

    high_risk_items = risk_assessment.get('high_risk_items', [])
    total_risk_score = risk_assessment.get('total_risk_score', 0)
    immediate_actions = [reg for reg in regulations if reg['priority'] == 'HIGH']

    # === 2. 통합 마크다운 보고서 생성 ===
    print("   통합 마크다운 보고서 작성 중...")

    # 2-1. 헤더 및 사업 정보
    full_markdown = f"""# 규제 준수 분석 통합 보고서

> 생성일: {datetime.now().strftime('%Y년 %m월 %d일')}

---

## 1. 사업 정보

| 항목 | 내용 |
|------|------|
| **업종** | {business_info.get('industry', 'N/A')} |
| **제품명** | {business_info.get('product_name', 'N/A')} |
| **원자재** | {business_info.get('raw_materials', 'N/A')} |
| **제조 공정** | {', '.join(business_info.get('processes', []))} |
| **직원 수** | {business_info.get('employee_count', 0)}명 |
| **판매 방식** | {', '.join(business_info.get('sales_channels', []))} |

---

## 2. 분석 요약

### 2.1 규제 현황
- **총 규제 개수**: {len(regulations)}개
- **우선순위 분포**:
  - 🔴 HIGH: {priority_count['HIGH']}개 (즉시 조치 필요)
  - 🟡 MEDIUM: {priority_count['MEDIUM']}개 (1-3개월 내 조치)
  - 🟢 LOW: {priority_count['LOW']}개 (6개월 내 조치)
- **카테고리 분포**:
{chr(10).join(f'  - {cat}: {count}개' for cat, count in category_count.items())}

### 2.2 리스크 평가
- **전체 리스크 점수**: {total_risk_score:.1f}/10
- **고위험 규제**: {len(high_risk_items)}개
- **즉시 조치 필요**: {len(immediate_actions)}개

---

## 3. 규제 목록 및 분류
"""

    # 2-2. 카테고리별 규제 목록
    categories = list(set(reg['category'] for reg in regulations))
    for i, category in enumerate(categories, 1):
        full_markdown += f"\n### 3.{i} {category}\n\n"

        category_regs = [reg for reg in regulations if reg['category'] == category]
        for j, reg in enumerate(category_regs, 1):
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[reg['priority']]
            full_markdown += f"""#### 3.{i}.{j} {priority_icon} {reg['name']}

**우선순위:** {reg['priority']}
**관할 기관:** {reg['authority']}
**적용 이유:** {reg['why_applicable']}

**주요 요구사항:**
{chr(10).join(f'- {req}' for req in reg.get('key_requirements', []))}

"""
            if reg.get('penalty'):
                full_markdown += f"**벌칙:** {reg['penalty']}\n\n"

    # 2-3. 실행 체크리스트
    full_markdown += "\n---\n\n## 4. 실행 체크리스트\n\n"

    for reg in regulations:
        reg_checklists = [c for c in checklists if c['regulation_id'] == reg['id']]
        if reg_checklists:
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[reg['priority']]
            full_markdown += f"### 4.{regulations.index(reg)+1} {priority_icon} {reg['name']}\n\n"

            for item in reg_checklists:
                full_markdown += f"- [ ] **{item['task_name']}**\n"
                full_markdown += f"  - 담당: {item['responsible_dept']}\n"
                full_markdown += f"  - 마감: {item['deadline']}\n"
                if item.get('estimated_cost'):
                    full_markdown += f"  - 예상 비용: {item['estimated_cost']}\n"
                full_markdown += "\n"

    # 2-4. 실행 계획 및 타임라인
    full_markdown += "\n---\n\n## 5. 실행 계획 및 타임라인\n\n"

    for plan in execution_plans:
        reg_name = plan['regulation_name']
        priority = next((r['priority'] for r in regulations if r['id'] == plan['regulation_id']), 'MEDIUM')
        priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[priority]

        full_markdown += f"### 5.{execution_plans.index(plan)+1} {priority_icon} {reg_name}\n\n"
        full_markdown += f"**타임라인:** {plan['timeline']}  \n"
        full_markdown += f"**시작 예정:** {plan['start_date']}  \n\n"

        # 마일스톤
        if plan.get('milestones'):
            full_markdown += "**주요 마일스톤:**\n"
            for milestone in plan['milestones']:
                full_markdown += f"- {milestone['name']} (완료 목표: {milestone['deadline']})\n"
            full_markdown += "\n"

        # 의존성
        if plan.get('dependencies') and any(plan['dependencies'].values()):
            full_markdown += "**의존성:**\n"
            for task, deps in plan['dependencies'].items():
                if deps:
                    full_markdown += f"- `{task}` ← {', '.join(f'`{d}`' for d in deps)}\n"
            full_markdown += "\n"

        # 병렬 작업
        if plan.get('parallel_tasks'):
            full_markdown += "**병렬 수행 가능:**\n"
            for group in plan['parallel_tasks']:
                full_markdown += f"- {', '.join(f'`{t}`' for t in group)}\n"
            full_markdown += "\n"

        # 크리티컬 패스
        if plan.get('critical_path'):
            full_markdown += f"**크리티컬 패스:** {' → '.join(f'`{t}`' for t in plan['critical_path'])}\n\n"

    # 2-5. 리스크 평가
    full_markdown += "\n---\n\n## 6. 리스크 평가\n\n"
    full_markdown += f"### 6.1 전체 리스크 평가\n\n"
    full_markdown += f"**전체 리스크 점수:** {total_risk_score:.1f}/10\n\n"

    risk_level = "매우 높음" if total_risk_score >= 8 else "높음" if total_risk_score >= 6 else "중간"
    full_markdown += f"**리스크 수준:** {risk_level}\n\n"

    if high_risk_items:
        full_markdown += "### 6.2 고위험 규제 (상위 5개)\n\n"
        for item in high_risk_items[:5]:
            full_markdown += f"#### {item['regulation_name']}\n\n"
            full_markdown += f"**리스크 점수:** {item['risk_score']}/10\n\n"
            full_markdown += f"**처벌 유형:** {item['penalty_type']}\n\n"
            full_markdown += f"**사업 영향:** {item['business_impact']}\n\n"

            if item.get('mitigation_priority'):
                full_markdown += f"**완화 우선순위:** {item['mitigation_priority']}\n\n"

    # 2-6. 경영진 요약 (LLM으로 생성)
    print("   경영진 요약 생성 중...")

    exec_summary_prompt = f"""
다음 규제 분석 결과를 바탕으로 경영진을 위한 핵심 요약을 작성하세요.

[분석 결과]
- 총 규제: {len(regulations)}개
- HIGH: {priority_count['HIGH']}개, MEDIUM: {priority_count['MEDIUM']}개, LOW: {priority_count['LOW']}개
- 리스크 점수: {total_risk_score:.1f}/10
- 고위험 규제: {len(high_risk_items)}개

다음 형식으로 작성하세요 (마크다운):

### 핵심 인사이트
- 인사이트 1 (구체적 숫자 포함)
- 인사이트 2
- 인사이트 3

### 의사결정 포인트
- [ ] 결정 사항 1
- [ ] 결정 사항 2
- [ ] 결정 사항 3

### 권장 조치 (우선순위 순)
1. **즉시:** [조치 내용]
2. **1개월 내:** [조치 내용]
3. **3개월 내:** [조치 내용]

간결하고 명확하게 작성하세요.
"""

    exec_response = llm.invoke(exec_summary_prompt)
    executive_summary = exec_response.content.strip()

    full_markdown += f"\n---\n\n## 7. 경영진 요약\n\n{executive_summary}\n"

    # 2-7. Next Steps
    full_markdown += "\n---\n\n## 8. 다음 단계\n\n"

    next_steps = [
        f"**1단계 (즉시):** HIGH 우선순위 {priority_count['HIGH']}개 규제 착수",
        "**2단계 (1주일 내):** 담당 부서 및 책임자 지정",
        "**3단계 (2주일 내):** 상세 실행 일정 확정 및 예산 승인",
        "**4단계 (1개월):** 월 단위 진행 상황 모니터링 체계 구축",
        "**5단계 (분기별):** 전문가 검토 및 보완"
    ]

    for step in next_steps:
        full_markdown += f"- {step}\n"

    # 2-8. 면책 조항
    full_markdown += "\n---\n\n## 면책 조항\n\n"
    full_markdown += "> 본 보고서는 AI 기반 분석 도구로 생성된 참고 자료입니다. "
    full_markdown += "실제 규제 준수 여부는 반드시 전문가의 검토를 받으시기 바랍니다. "
    full_markdown += "본 보고서 내용으로 인한 법적 책임은 사용자에게 있습니다.\n"

    # === 3. 인사이트 및 액션 아이템 추출 (구조화된 데이터) ===
    print("   핵심 데이터 추출 중...")

    key_insights = [
        f"총 {len(regulations)}개 규제 적용 대상 - 체계적 준수 관리 필요",
        f"HIGH 우선순위 {priority_count['HIGH']}개 규제는 사업 개시 전 필수 완료",
        f"전체 리스크 점수 {total_risk_score:.1f}/10 - {'즉각 대응 필요' if total_risk_score >= 7 else '전문가 컨설팅 권장'}"
    ]

    action_items = []
    for reg in immediate_actions[:3]:
        action_items.append({
            "name": f"{reg['name']} 준수 조치 시작",
            "deadline": "즉시",
            "priority": "HIGH"
        })

    risk_highlights = []
    for item in high_risk_items[:3]:
        risk_highlights.append(
            f"{item['regulation_name']} 미준수 시 {item['penalty_type']} - {item['business_impact']}"
        )

    # === 4. PDF 저장 ===
    print("   PDF 파일 생성 중...")

    try:
        pdf_path = save_report_pdf(full_markdown, Path("report"))
        report_pdf_path = str(pdf_path)
        print(f"   ✓ PDF 저장 완료: {report_pdf_path}")
    except Exception as e:
        print(f"   ⚠ PDF 생성 실패: {e}")
        report_pdf_path = "PDF 생성 실패"

    # === 5. 최종 보고서 반환 ===
    final_report: FinalReport = {
        "executive_summary": executive_summary,
        "detailed_report": "",  # 통합 보고서로 대체
        "legal_report": "",     # 통합 보고서로 대체
        "key_insights": key_insights,
        "action_items": action_items,
        "risk_highlights": risk_highlights,
        "next_steps": next_steps,
        "full_markdown": full_markdown,
        "report_pdf_path": report_pdf_path
    }

    print(f"   ✓ 통합 보고서 생성 완료\n")

    return {"final_report": final_report}


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


def planning_agent_node(state: AgentState) -> Dict[str, Any]:
    """실행 계획 노드: 체크리스트를 실행 계획으로 변환합니다."""
    result = plan_execution.invoke({
        "regulations": state["regulations"],
        "checklists": state["checklists"]
    })
    return {"execution_plans": result["execution_plans"]}


def risk_assessor_node(state: AgentState) -> Dict[str, Any]:
    """리스크 평가 노드: 미준수 시 리스크를 평가합니다."""
    result = assess_risks.invoke({
        "regulations": state["regulations"],
        "business_info": state["business_info"]
    })
    return {"risk_assessment": result["risk_assessment"]}


def report_generator_node(state: AgentState) -> Dict[str, Any]:
    """보고서 생성 노드: 전체 분석 결과를 통합 보고서로 작성합니다."""
    result = generate_final_report.invoke({
        "business_info": state["business_info"],
        "regulations": state["regulations"],
        "checklists": state["checklists"],
        "execution_plans": state["execution_plans"],
        "risk_assessment": state["risk_assessment"]
    })
    return {"final_report": result["final_report"]}


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
    6. planning_agent: 실행 계획 수립
    7. risk_assessor: 리스크 평가
    8. report_generator: 최종 보고서 생성
    """
    graph = StateGraph(AgentState)

    # 기존 Agent 노드
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("searcher", search_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("prioritizer", prioritizer_node)
    graph.add_node("checklist_generator", checklist_generator_node)
    graph.add_node("risk_assessor", risk_assessor_node)

    # 신규 Agent 노드
    graph.add_node("planning_agent", planning_agent_node)
    graph.add_node("report_generator", report_generator_node)

    # 엣지 추가: 순차 실행
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "searcher")
    graph.add_edge("searcher", "classifier")
    graph.add_edge("classifier", "prioritizer")
    graph.add_edge("prioritizer", "checklist_generator")
    graph.add_edge("checklist_generator", "planning_agent")
    graph.add_edge("planning_agent", "risk_assessor")
    graph.add_edge("risk_assessor", "report_generator")
    graph.add_edge("report_generator", END)

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
        # Agent 결과 필드 초기화
        "checklists": [],
        "execution_plans": [],
        "risk_assessment": {
            "total_risk_score": 0.0,
            "high_risk_items": [],
            "risk_matrix": {},
            "recommendations": []
        },
        "final_report": {
            "executive_summary": "",
            "detailed_report": "",
            "legal_report": "",
            "key_insights": [],
            "action_items": [],
            "risk_highlights": [],
            "next_steps": []
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
            print(f"      비용: {item['estimated_cost']}")
            print(f"      기간: {item['estimated_time']}")
            if item['method']:
                print(f"      실행 방법:")
                for method in item['method'][:3]:  # 최대 3단계만 표시
                    print(f"         {method}")

        print()


def print_execution_plans(execution_plans: List[ExecutionPlan]):
    """실행 계획을 보기 좋게 출력합니다."""
    print("📅 실행 계획")
    print("=" * 60)
    print(f"총 {len(execution_plans)}개 계획\n")

    for plan in execution_plans:
        print(f"🎯 {plan['regulation_name']}")
        print(f"   계획 ID: {plan['plan_id']}")
        print(f"   예상 기간: {plan['timeline']}")
        print(f"   시작 시점: {plan['start_date']}")
        print()

        # 마일스톤
        milestones = plan.get('milestones', [])
        if milestones:
            print(f"   📌 마일스톤:")
            for milestone in milestones:
                print(f"      • {milestone.get('name', '')} ({milestone.get('deadline', '')})")
                print(f"        완료 기준: {milestone.get('completion_criteria', '')}")
        print()

        # 의존성
        dependencies = plan.get('dependencies', {})
        if dependencies:
            print(f"   🔗 작업 의존성:")
            for task, prereqs in list(dependencies.items())[:3]:
                print(f"      작업 {task}는 작업 {', '.join(prereqs)} 완료 후")
        print()

        # 병렬 작업
        parallel_tasks = plan.get('parallel_tasks', [])
        if parallel_tasks:
            print(f"   ⚡ 병렬 처리 가능:")
            for group in parallel_tasks[:2]:
                print(f"      작업 {', '.join(group)}는 동시 진행 가능")
        print()

        # 크리티컬 패스
        critical_path = plan.get('critical_path', [])
        if critical_path:
            print(f"   🛤️  크리티컬 패스: {' → '.join(critical_path)}")
        print("-" * 60)
        print()


def print_final_report(final_report: FinalReport):
    """최종 보고서를 출력합니다."""
    print("📄 최종 보고서")
    print("=" * 60)
    print()

    # 핵심 인사이트
    key_insights = final_report.get('key_insights', [])
    if key_insights:
        print("📌 핵심 인사이트:")
        for idx, insight in enumerate(key_insights, 1):
            print(f"   {idx}. {insight}")
        print()

    # 즉시 조치 항목
    action_items = final_report.get('action_items', [])
    if action_items:
        print("🎯 즉시 조치 필요:")
        for item in action_items:
            print(f"   • {item.get('name', '')} (마감: {item.get('deadline', '')})")
        print()

    # 주요 리스크
    risk_highlights = final_report.get('risk_highlights', [])
    if risk_highlights:
        print("⚠️  주요 리스크:")
        for risk in risk_highlights:
            print(f"   • {risk}")
        print()

    # 다음 단계
    next_steps = final_report.get('next_steps', [])
    if next_steps:
        print("📋 다음 단계 권장사항:")
        for step in next_steps:
            print(f"   {step}")
        print()

    # 경영진용 요약 (일부만 표시)
    exec_summary = final_report.get('executive_summary', '')
    if exec_summary:
        print("📊 경영진 요약 보고서 (미리보기):")
        lines = exec_summary.split('\n')[:10]
        print('\n'.join(f"   {line}" for line in lines))
        if len(exec_summary.split('\n')) > 10:
            print("   ... (전체 내용은 JSON 파일 참조)")
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

    # 새로운 Agent 결과 출력
    print_checklists(result.get('checklists', []))
    print()

    print_execution_plans(result.get('execution_plans', []))
    print()

    print_risk_assessment(result.get('risk_assessment', {}))
    print()

    print_final_report(result.get('final_report', {}))

    # JSON 파일로 저장 (모든 데이터 포함)
    complete_output = {
        "business_info": result.get('business_info', {}),
        "summary": {
            "total_regulations": final_output.get('total_count', 0),
            "priority_distribution": priority_dist,
            "total_checklist_items": len(result.get('checklists', [])),
            "total_execution_plans": len(result.get('execution_plans', [])),
            "risk_score": result.get('risk_assessment', {}).get('total_risk_score', 0.0)
        },
        "regulations": regulations,
        "checklists": result.get('checklists', []),
        "execution_plans": result.get('execution_plans', []),
        "risk_assessment": result.get('risk_assessment', {}),
        "final_report": result.get('final_report', {})
    }

    output_file = "regulation_analysis_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_output, f, indent=2, ensure_ascii=False)

    print(f"💾 전체 결과가 '{output_file}' 파일로 저장되었습니다.")
    print()


if __name__ == "__main__":
    main()
