"""
규제 AI Agent 서비스 - LangGraph Multi-Agent Workflow_v2
프롬프트 확장 버전
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
import sys
import json
from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from datetime import datetime
from dotenv import load_dotenv
from enum import Enum
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
    task_index: Dict[str, str]          # 작업 ID -> 작업명 매핑
    task_meta: Dict[str, Dict[str, Any]]  # 작업 메타데이터 (부서, 기간, 가정 등)


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
    md_path = output_dir / "regulation_report_v2.md"
    pdf_path = output_dir / "regulation_report_v2.pdf"

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
    당신은 '규제 검색 키워드 추출기'입니다. 아래 사업 정보를 바탕으로
    검색 효율이 높은 핵심 키워드를 생성하고, 지정된 JSON 스키마로만 출력하세요.

    [사업 정보]
    업종: {business_info.get('industry', '')}
    제품명: {business_info.get('product_name', '')}
    원자재: {business_info.get('raw_materials', '')}
    제조 공정: {', '.join(business_info.get('processes') or [])}
    직원 수: {business_info.get('employee_count', 0)}
    판매 방식: {', '.join(business_info.get('sales_channels') or [])}

    [생성 규칙]
    1) 총 5–7개 키워드. 다음 3개 카테고리에서 각각 최소 1개 이상 포함:
    - product_industry: 제품/산업/공정/원자재의 고유 용어·약어
    - safety_environment: 안전·보건·환경·화학물질·배출·폐기물 관련
    - certification_permit: KC, CE, RoHS, REACH, ISO 9001/14001 등
    2) 중복·동의어 제거: 의미가 겹치면 더 특이적인 하나만 유지.
    3) 일반어 금지(예: 제조, 생산, 공장, 제품, 규격, 인증 같은 포괄어 단독 사용 금지).
    4) 표기 규칙:
    - 약어는 대문자 유지(예: CE, KC, RoHS, REACH, ISO 9001/14001).
    - 한국 법령/제도명은 한글 표기(예: 산업안전보건법, 자율안전확인).
    - 불필요한 기호·조사·따옴표·괄호 제거.
    5) 아래 JSON 스키마를 '정확히' 따르며, 다른 텍스트를 절대 포함하지 말 것.

    [JSON 스키마]
    {{
    "csv": "문자열(키워드들을 ', '로 구분한 한 줄)",
    "keywords": ["문자열", "..."],  // 길이 5~7
    "by_category": {{
        "product_industry": ["문자열", "..."],      // ≥1
        "safety_environment": ["문자열", "..."],    // ≥1
        "certification_permit": ["문자열", "..."]   // ≥1
    }}
    }}

    JSON만 출력하세요. 설명/머리말/코드블록 금지.
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

        keywords_data = json.loads(content.strip())
        keywords = keywords_data.get("keywords", [])

        print(f"   ✓ 추출된 키워드 ({len(keywords)}개): {keywords}")
        print(f"   ✓ 카테고리별:")
        by_category = keywords_data.get("by_category", {})
        for category, items in by_category.items():
            print(f"      - {category}: {items}")
        print()

        return {"keywords": keywords}

    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON 파싱 오류: {e}")
        print(f"   응답 내용: {response.content[:200]}...")
        # Fallback: 쉼표로 split
        keywords = [k.strip() for k in response.content.split(',')]
        print(f"   ✓ Fallback - 추출된 키워드 ({len(keywords)}개): {keywords}\n")
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
    다음 정보를 바탕으로 '검색 근거 기반'으로 적용 가능한 주요 규제를 식별·분류하세요.
    JSON 배열만 출력하며, 설명/코드블록/여타 텍스트는 절대 포함하지 마세요.

    [사업 정보]
    업종: {business_info.get('industry', '')}
    제품: {business_info.get('product_name', '')}
    원자재: {business_info.get('raw_materials', '')}
    공정: {', '.join(business_info.get('processes') or [])}
    직원 수: {int(business_info.get('employee_count') or 0)}명

    [검색된 규제 정보]
    {search_summary}

    [생성 원칙]
    1) 반드시 '검색된 규제 정보'에 나타난 규제명/기관/URL만 사용하세요. 검색 결과로 근거가 확인되지 않는 규제는 포함하지 마세요.
    2) 5~8개를 목표로 하되, 신뢰할 수 있는 근거가 부족하면 그보다 적게 산출해도 됩니다(허용).
    3) 결과 배열은 (위반 영향도 × 적용 가능성) 기준 우선순위 내림차순으로 정렬하세요. 스코어는 출력하지 않습니다.
    4) 동일/동의 규제는 하나로 통합하세요. 정식 명칭을 우선 사용하고, 널리 쓰이는 약어가 있으면 "정식명 (약어)" 형태로 표기하세요.
    5) 각 항목의 category는 아래 3개 중 하나만 허용합니다(문자 그대로 사용):
    - 안전/환경
    - 제품 인증
    - 공장 운영
    6) key_requirements는 2~5개, 각 항목은 '명령형'으로 시작하는 구체적이고 실행 가능한 한 문장으로 작성하세요.
    - 예: "MSDS를 작성·비치하고 분기별 교육을 실시한다"
    - 금지: 모호어(적절히/필요 시/가능한/권장), 중복·상위개념 나열
    7) reference_url은 '검색된 규제 정보'에서 선택하며, 다음 우선순위를 따릅니다:
    정부/법령/표준 공식 사이트(예: *.go.kr, law.go.kr, korea.kr, iso.org, iec.ch, europa.eu)
    > 공공기관/협회 > 학술/신뢰 언론 > 기타. 다수일 경우 가장 공식적인 단일 URL만 사용하세요.
    8) JSON 이외의 텍스트(머리말, 설명, 코드블록, 주석)는 절대 출력하지 마세요. 모든 문자열은 따옴표로 감싸고, 쉼표 등 문법 오류가 없도록 하세요.

    [출력 형식(JSON 배열, 각 원소 스키마 고정)]
    {{
    "name": "규제명 (가능하면 정식명, 필요 시 약어 병기: 예 '유해물질 제한 지침 (RoHS)')",
    "category": "안전/환경 | 제품 인증 | 공장 운영 (3개 중 하나)",
    "why_applicable": "이 사업에 적용되는 구체적 근거(업종·제품·원자재·공정·규모 등) 1~2문장",
    "authority": "관할 기관(검색 결과에서 확인된 명칭만 사용)",
    "key_requirements": ["실행 가능한 요구사항 2~5개"],
    "reference_url": "검색 결과에서 선택한 단일 URL"
    }}
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
    판단은 반드시 [규제 목록] 텍스트에 근거하여 수행하세요. 외부 지식으로 보충하거나 추정하지 마세요.
    출력은 오직 대문자 라벨(HIGH/MEDIUM/LOW)만 줄바꿈으로 나열합니다. 설명·코드블록·빈 줄·공백은 금지합니다.
    출력 줄 수는 입력 규제 개수와 동일하며, 반드시 입력 규제의 순서를 그대로 따릅니다.

    [사업 정보]
    제품: {business_info.get('product_name', '')}
    직원 수: {int(business_info.get('employee_count') or 0)}명

    [규제 목록]
    {regulations_summary}

    [판단 절차]
    1) 각 규제에 대해 다음 신호를 [0~2] 점으로 평가합니다(근거가 있지 않으면 0점):
    - 위반 영향도(Impact): 영업정지/리콜/형사처벌/고액벌금/중대재해 언급 → 2, 중간 벌금/개선명령 → 1, 미기재/경미 → 0
    - 적용 확실성(Applicability): ‘필수/의무/적용 대상 명시’ → 2, 추정/일부 요건 → 1, 불명확 → 0
    - 시급성(Immediacy): ‘판매 전 인증/사전 허가/즉시 이행’ → 2, 기한/주기적 보고 → 1, 장기적/비상시 → 0
    - 시장진입 의존성(Market Access): ‘미이행 시 판매/유통 불가(예: KC/CE/품목허가)’ → 2, 입찰/특정 채널 제한 → 1, 무관 → 0
    - 적발 가능성(Enforcement): 상시점검/정기검사/신고·허가 갱신/감사 빈도 언급 → 2, 간헐적 → 1, 불명확 → 0
    2) 합계 점수로 우선순위를 매핑합니다(동점은 영향도 높은 쪽을 우선 고려하되 라벨만 출력):
    - 7~10점: HIGH
    - 4~6점: MEDIUM
    - 0~3점: LOW
    3) 다음 특수 규칙을 적용합니다:
    - ‘권장/가이드라인/자율’ 위주의 문구면 한 단계 하향.
    - ‘규모 기준/예외’가 본 사업에 해당할 가능성이 높게 서술되면 한 단계 하향.
    - ‘영업정지/형사처벌/판매 금지’가 명시되면 최소 MEDIUM, 근거가 강하면 HIGH.
    4) 최종 라벨만 출력합니다. 각 규제 1줄씩, 총 줄 수는 입력 규제 개수와 동일해야 합니다.

    [출력 형식 예]
    HIGH
    MEDIUM
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
다음 규제를 준수하기 위한 '실행 가능한' 체크리스트를 생성하세요.
JSON 배열만 출력하며, 설명/코드블록/기타 텍스트는 절대 포함하지 마세요.

[규제 정보]
규제명: {reg.get('name', '')}
카테고리: {reg.get('category', '')}   // (안전/환경 | 제품 인증 | 공장 운영 중 하나)
관할 기관: {reg.get('authority', '')}
우선순위: {reg.get('priority', '')}   // (HIGH | MEDIUM | LOW)
적용 이유: {reg.get('why_applicable', '')}
주요 요구사항:
{chr(10).join(f'- {req}' for req in reg.get('key_requirements', []))}

[생성 규칙]
1) 주어진 규제를 준수하기 위해 필요한 작업들을 생성합니다. 각 작업은 '주요 요구사항' 중 하나 이상과 1:1로 매핑되어야 합니다.
   - 각 작업의 method[0]에 반드시 "(매핑: 요구사항 N)" 형태로 어떤 요구사항을 구현하는지 명시하세요.
   - 동일 요구사항을 중복 작업으로 만들지 말고, 서로 다른 요구사항을 한 작업에 섞지 마세요.
2) 우선순위/카테고리 기반 지침:
   - 우선순위가 HIGH이면 deadline을 '사업 개시 전 필수' 또는 '30일 이내' 중 하나로 설정합니다.
   - 카테고리가 '제품 인증'이면 시험/기술문서/표시(라벨)/적합성평가 중 적어도 2개는 서로 다른 작업으로 분리하세요.
   - 카테고리가 '안전/환경'이면 위험성평가/교육/점검/보관·배출 관리 중 2개 이상을 포함하세요.
   - 카테고리가 '공장 운영'이면 설비점검/정기보수/운영상태 기록/훈련 중 2개 이상을 포함하세요.
3) 실행 가능성 기준:
   - task_name은 명령형으로, 단일 작업 단위로 작성합니다(예: "SDS 작성 및 교육 실시"는 2개 작업으로 분리 고려).
   - method는 3~5단계, 각 단계는 "1. 2. 3."으로 시작하고 정량 요소(빈도, 수량, 임계치, 검증 방법)를 포함하세요.
   - 마지막 단계에는 반드시 '증빙/기록'을 남기는 절차를 포함하세요(예: 교육 서명부, 검사성적서, 점검표).
4) 담당 부서와 마감 기한:
   - '제품 인증' 기본: 품질/인증팀 또는 법무팀, '안전/환경' 기본: 안전관리팀/환경관리팀,
     '공장 운영' 기본: 시설관리팀/생산팀. 필요 시 인사팀(교육/훈련)을 지정하세요.
   - MEDIUM은 '분기 1회/반기 1회/연 1회' 등 주기로, LOW는 '연 1회/필요 시' 등 완화된 주기를 사용하세요.
5) 비용/시간:
   - 근거가 부족하면 '무료' 또는 '30만~80만원'처럼 현실적 범위를 사용하세요.
   - 소요 시간은 'X일/주/개월' 중 하나로, 소규모(직원수 ≤ 50)는 짧은 기간을 우선 제시하세요.
6) 출력 형식: 아래 JSON 스키마만 사용합니다. 필드명/형태를 바꾸지 마세요.
{{
  "task_name": "구체적인 작업명(명령형, 단일 작업)",
  "responsible_dept": "담당 부서(예: 안전관리팀/법무팀/시설관리팀/인사팀/품질팀 등)",
  "deadline": "마감 기한(예: 사업 개시 전 필수, 30일 이내, 분기 1회, 연 1회, 3개월 내)",
  "method": [
    "1. (매핑: 요구사항 N) 첫 단계(정량/증빙 포함)",
    "2. 두 번째 단계(수량/빈도/임계치/검증 포함)",
    "3. 세 번째 단계(증빙/기록 남기기)",
    "4. (선택) 네 번째 단계",
    "5. (선택) 다섯 번째 단계"
  ],
  "estimated_cost": "예상 비용(예: 무료, 30만원, 30만~80만원)",
  "estimated_time": "소요 시간(예: 3일, 2주, 1개월)"
}}

[중요]
- JSON 배열만 출력하세요. 다른 텍스트/코드블록/설명은 절대 포함하지 마세요.
- 각 task_name은 서로 달라야 하며, 서로 다른 요구사항을 구현해야 합니다.
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
다음 규제의 체크리스트를 바탕으로 '근거 기반' 실행 계획을 수립하세요.
JSON만 출력하며, 설명/코드블록/여분 텍스트는 금지합니다.

[규제 정보]
규제명: {reg_name}
우선순위: {reg_priority}

[체크리스트 항목들]
{checklist_summary}

[규칙 요약]
- 체크리스트 항목을 위에서부터 "1".."N" ID로 부여(신규 작업 금지).
- 시간 정규화(주5일, 1주=5d, 1개월=20d), 외부 리드타임 +20% 버퍼.
- HIGH/ MEDIUM/ LOW에 따라 start_date/버퍼/상한을 조정.
- 동일 부서/의존성 충돌 시 병렬 금지.
- DAG 최장경로를 critical_path로 계산.
- 마일스톤 3~5개, completion_criteria는 검증 가능한 산출물로.

[출력 스키마]
{{
  "timeline": "문자열",
  "start_date": "문자열",
  "milestones": [{{"name":"문자열","deadline":"문자열","tasks":["ID"...],"completion_criteria":"문자열"}}],
  "dependencies": {{"ID": ["선행ID"...]}},
  "parallel_tasks": [["ID","ID"], ...],
  "critical_path": ["ID","ID", ...],
  "task_index": {{"ID": "작업명", ...}},
  "task_meta": {{
     "ID": {{
        "dept": "담당부서",
        "normalized_duration_days": 10,
        "assumptions": ["리드타임 +20%", "내부 검토 2일 포함"] 
     }},
     "...": {{ ... }}
  }}
}}
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

            raw_task_index = plan_data.get("task_index", {}) or {}
            task_index = {
                str(task_id): task_name
                for task_id, task_name in raw_task_index.items()
            }

            raw_task_meta = plan_data.get("task_meta", {}) or {}
            task_meta = {
                str(task_id): meta if isinstance(meta, dict) else {}
                for task_id, meta in raw_task_meta.items()
            }

            checklist_ids = list(task_index.keys())
            if not checklist_ids:
                checklist_ids = [str(i + 1) for i in range(len(reg_checklists))]

            # ExecutionPlan 형식으로 변환
            execution_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": checklist_ids,
                "timeline": plan_data.get("timeline", "3개월"),
                "start_date": plan_data.get("start_date", "즉시"),
                "milestones": plan_data.get("milestones", []),
                "dependencies": plan_data.get("dependencies", {}),
                "parallel_tasks": plan_data.get("parallel_tasks", []),
                "critical_path": plan_data.get("critical_path", []),
                "task_index": task_index,
                "task_meta": task_meta
            }

            all_execution_plans.append(execution_plan)

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            # 기본 실행 계획 생성
            fallback_task_index = {
                str(i + 1): item.get("task_name", f"작업 {i + 1}")
                for i, item in enumerate(reg_checklists)
            }
            fallback_task_meta = {
                task_id: {
                    "dept": reg_checklists[int(task_id) - 1].get("responsible_dept", "담당 부서"),
                    "normalized_duration_days": 5,
                    "assumptions": ["추정값: LLM 실행 계획 생성 실패 시 기본값 적용"]
                }
                for task_id in fallback_task_index.keys()
            }

            default_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": list(fallback_task_index.keys()),
                "timeline": "3개월",
                "start_date": "즉시" if reg_priority == "HIGH" else "1개월 내",
                "milestones": [],
                "dependencies": {},
                "parallel_tasks": [],
                "critical_path": [],
                "task_index": fallback_task_index,
                "task_meta": fallback_task_meta
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
반드시 입력된 정보와 '근거'에 명시된 내용만 사용하세요. 근거에 없는 수치·사례·기관·금액을 추정/창작하지 마세요.
JSON만 출력하고 설명·코드블록·여분 텍스트는 금지합니다.

[규제 정보]
규제명: {reg.get('name','')}
카테고리: {reg.get('category','')}
관할 기관: {reg.get('authority','')}
우선순위: {reg.get('priority','')}
적용 이유: {reg.get('why_applicable','')}

[사업 정보]
제품: {business_info.get('product_name','')}
직원 수: {int(business_info.get('employee_count') or 0)}명

[근거]
- 아래 항목(예: 검색 요약, 공식 URL, 법령 인용 등)에 명시된 내용만 사용하세요. 없으면 관련 필드는 빈 값으로 남깁니다.
{reg.get('reference_url','')}

[평가 절차]
1) 다음 5개 신호를 각 0~2점으로 채점합니다(근거 문구가 '명시'된 경우에만 가점, 없으면 0점):
   - Impact(영향도): 영업정지·리콜·형사처벌·허가취소·고액벌금 등 심각한 결과 = 2 / 중간 벌금·개선명령 = 1 / 경미·미기재 = 0
   - Applicability(적용 확실성): '의무/필수/대상 명시' = 2 / 일부·간접 언급 = 1 / 불명확 = 0
   - Enforcement(집행 강도): 상시점검·정기검사·신고/허가 갱신 등 집행 주기 명시 = 2 / 간헐·불명확 = 1~0
   - Immediacy/Market Access(시급성·시장진입): 판매 전 인증·사전 허가·출고 제한 = 2 / 기한·주기적 보고 = 1 / 장기·예외적 = 0
   - Exposure(노출 규모): 다수 작업장·대량 취급·광범위 판매 등 = 2 / 제한적 = 1 / 미기재 = 0
2) risk_score 계산: 위 5개 점수의 합(0~10)을 기본값으로 하되, 우선순위와의 일관성을 유지합니다.
   - 우선순위 HIGH이면 최소 6 이상이 되도록(근거가 매우 약하면 5까지 허용), LOW이면 최대 6 이하가 되도록 조정.
3) penalty_amount / penalty_type / business_impact / past_cases:
   - 근거에 금액이 '명시'된 경우에만 penalty_amount를 채우고, 없으면 빈 문자열("")로 남깁니다.
   - penalty_type은 다음 중 하나로만 기입: "형사처벌" | "과태료" | "행정처분" | "" (근거 없으면 빈 문자열)
   - business_impact는 근거 문구가 있는 가장 심각한 1가지를 요약(예: "영업정지 6개월"). 없으면 빈 문자열.
   - past_cases는 근거에 '구체적 사례(연도·기업·처벌 내용)'가 있을 때만 배열에 담고, 없으면 빈 배열([]).
4) JSON 외 텍스트를 출력하지 마세요. 모든 값은 따옴표로 감싸고, risk_score는 숫자만(정수 또는 소수 첫째 자리 반올림 정수)로 출력합니다.

[출력 스키마]
{{
  "penalty_amount": "벌금액(예: '최대 1억원', '300만원 이하', 근거 없으면 '')",
  "penalty_type": "형사처벌 | 과태료 | 행정처분 | ''",
  "business_impact": "근거가 있는 가장 심각한 영향 1가지(없으면 '')",
  "risk_score": 0-10의 숫자,
  "past_cases": [
    "과거 처벌 사례 1 (연도, 기업, 처벌 내용)",
    "과거 처벌 사례 2"
  ],
  "mitigation": "리스크 완화 방안 1~2문장(근거 범위 내에서 일반적 모범조치 제시)"
}}
"""


        response = llm.invoke(prompt)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            risk_data = json.loads(content.strip())

            raw_score = risk_data.get("risk_score", 5.0)
            try:
                risk_score = float(raw_score)
            except (TypeError, ValueError):
                risk_score = 5.0

            past_cases = risk_data.get("past_cases", [])
            if not isinstance(past_cases, list):
                past_cases = []

            risk_item: RiskItem = {
                "regulation_id": reg['id'],
                "regulation_name": reg['name'],
                "penalty_amount": risk_data.get("penalty_amount", "") or "",
                "penalty_type": risk_data.get("penalty_type", "") or "",
                "business_impact": risk_data.get("business_impact", "") or "",
                "risk_score": risk_score,
                "past_cases": past_cases,
                "mitigation": risk_data.get("mitigation", "")
            }

            risk_items.append(risk_item)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"      ⚠️  파싱 오류: {e}")
            # 기본 리스크 아이템 추가
            risk_items.append({
                "regulation_id": reg['id'],
                "regulation_name": reg['name'],
                "penalty_amount": "",
                "penalty_type": "",
                "business_impact": "",
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

        # 체크리스트 매핑
        task_index = plan.get('task_index', {})
        if task_index:
            full_markdown += "**체크리스트 매핑:**\n"
            for task_id, task_name in task_index.items():
                full_markdown += f"- `{task_id}`: {task_name}\n"
            full_markdown += "\n"

        # 작업 메타데이터
        task_meta = plan.get('task_meta', {})
        if task_meta:
            full_markdown += "**작업 메타데이터:**\n"
            for task_id, meta in task_meta.items():
                dept = meta.get("dept", "-")
                duration = meta.get("normalized_duration_days", "-")
                assumptions = meta.get("assumptions", [])
                assumption_text = ", ".join(assumptions) if isinstance(assumptions, list) else ""
                full_markdown += f"- `{task_id}`: 담당 {dept}, 기간 {duration}일"
                if assumption_text:
                    full_markdown += f" (가정: {assumption_text})"
                full_markdown += "\n"
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
다음 규제 분석 결과만을 바탕으로, 경영진용 핵심 요약을 작성하세요.
- 제공된 수치/목록 외의 새로운 통계·가정·사례를 만들지 마세요.
- 출력은 마크다운만 포함하며, 지정한 섹션/불렛 개수/형식을 지키세요.

[분석 결과]
- 총 규제: {len(regulations)}개
- HIGH: {priority_count['HIGH']}개, MEDIUM: {priority_count['MEDIUM']}개, LOW: {priority_count['LOW']}개
- 리스크 점수: {total_risk_score:.1f}/10
- 고위험 규제: {len(high_risk_items)}개

[작성 규칙]
1) '핵심 인사이트'는 정확히 3개 불렛로 작성하고, 각 불렛에 최소 하나의 수치를 포함합니다.
   - 예시 수치: HIGH 비중(= HIGH/총 규제 × 100, 정수 반올림 %), 고위험 규제 수/상위 3개 이름, 예상 대응 기간(즉시/1개월/3개월 기준).
2) '의사결정 포인트'는 정확히 3개 체크박스로 작성하며, 각 항목에 (결정자/마감)을 괄호로 병기합니다.
   - 예: [ ] KC 인증 예산 1,200만원 승인 (결정자: COO, 마감: 30일)
3) '권장 조치'는 정확히 3개 항목을 '즉시 / 1개월 내 / 3개월 내' 순서로 작성합니다.
   - HIGH 우선 과제는 '즉시', MEDIUM은 '1개월 내', LOW는 '3개월 내'에 배치합니다.
4) 톤과 길이:
   - 각 불렛은 10~20단어(또는 한글 20자 내외)로 간결하게, 모호어(적절히/가능한/권장) 금지.
   - 고유명(규제명/기관명)은 그대로 사용하고 축약하지 않습니다.
5) 결측 처리:
   - 필요한 정보가 없으면 '-'로 표기합니다(예: 상위 3개를 뽑을 수 없는 경우).
6) 마크다운 외 텍스트 금지. 섹션 제목과 순서는 아래 형식을 '정확히' 따르세요.

### 핵심 인사이트
- (여기에 1개 불렛: 반드시 수치 포함)
- (여기에 1개 불렛: 반드시 수치 포함)
- (여기에 1개 불렛: 반드시 수치 포함)

### 의사결정 포인트
- [ ] (결정 항목 1: 결정자/마감 포함)
- [ ] (결정 항목 2: 결정자/마감 포함)
- [ ] (결정 항목 3: 결정자/마감 포함)

### 권장 조치 (우선순위 순)
1. **즉시:** (HIGH 과제 중심, 한 문장)
2. **1개월 내:** (MEDIUM 과제 중심, 한 문장)
3. **3개월 내:** (LOW 과제 중심, 한 문장)
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

        # 체크리스트 매핑
        task_index = plan.get('task_index', {})
        if task_index:
            print("   📋 체크리스트 매핑:")
            for task_id, task_name in list(task_index.items())[:4]:
                print(f"      {task_id} → {task_name}")
            if len(task_index) > 4:
                print("      ...")
        print()

        # 작업 메타데이터
        task_meta = plan.get('task_meta', {})
        if task_meta:
            print("   🧩 작업 메타:")
            for task_id, meta in list(task_meta.items())[:3]:
                dept = meta.get("dept", "-")
                duration = meta.get("normalized_duration_days", "-")
                assumptions = meta.get("assumptions", [])
                assumption_text = ", ".join(assumptions[:2]) if isinstance(assumptions, list) else ""
                print(f"      {task_id}: 부서={dept}, 기간={duration}일")
                if assumption_text:
                    print(f"         가정: {assumption_text}")
            if len(task_meta) > 3:
                print("      ...")
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
    
    # 다른 샘플 사업 정보 (전자제품 제조)
    sample_business_info2: BusinessInfo = {
    "industry": "전자제품 제조",
    "product_name": "스마트 LED 전구 (Wi-Fi)",
    "raw_materials": "ABS 수지, PCB, 구리, LED 칩, 주석-은 납땜 합금",
    "processes": ["사출 성형", "SMT(표면실장)", "납땜 리플로우", "펌웨어 플래싱", "최종 조립", "기능/안전 시험"],
    "employee_count": 80,
    "sales_channels": ["B2C", "온라인", "오프라인 리테일", "수출"],
    "export_countries": ["미국", "유럽연합(EU)", "일본"]
    }

    select = sys.argv[1] if len(sys.argv) > 1 else "1"
    
    print("📝 입력된 사업 정보:")
    print(json.dumps(sample_business_info if select == "1" else sample_business_info2, indent=2, ensure_ascii=False))
    print()
    print("-" * 60)
    print()

    # Workflow 실행
    try:
        result = run_regulation_agent(sample_business_info if select == "1" else sample_business_info2)
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
