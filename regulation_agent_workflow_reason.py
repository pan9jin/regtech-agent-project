"""
규제 AI Agent 서비스 - LangGraph Multi-Agent Workflow (병렬 처리 최적화)
8개의 Agent로 구성된 규제 분석 시스템

1. Analyzer Agent: 사업 정보 분석 및 키워드 추출
2. Search Agent: Tavily API를 통한 규제 정보 검색
3. Classifier Agent: 검색된 규제 분류 및 적용성 판단
4. Prioritizer Agent: 규제 우선순위 결정 (HIGH/MEDIUM/LOW)
5. Checklist Generator Agent: 규제별 실행 가능한 체크리스트 생성 [병렬]
6. Risk Assessment Agent: 미준수 시 리스크 평가 및 완화 방안 제시 [병렬]
7. Planning Agent: 체크리스트 → 실행 계획 변환 (의존성, 타임라인, 마일스톤)
8. Report Generation Agent: 최종 통합 보고서 생성 (경영진/실무진/법무팀용)
"""

import re
import sys
import json
import time
from typing import List, Optional, Dict, Any, Iterable, Union
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


class EvidenceItem(TypedDict, total=False):
    """LLM 답변에 포함되는 근거/출처 정보"""
    source_id: str                   # 검색 결과 식별자 (예: SRC-001)
    title: str                       # 문서 제목
    url: str                         # 문서 URL
    snippet: str                     # 발췌 내용 (원본, 생략 가능)
    justification: str               # LLM이 생성한 concise 요약 (우선 사용)


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
    sources: List[EvidenceItem]


class ChecklistItem(TypedDict):
    """체크리스트 항목 데이터 구조"""
    regulation_id: str          # 연결된 규제 ID
    regulation_name: str        # 규제명
    task_name: str              # 작업명
    responsible_dept: str       # 담당 부서
    deadline: str               # 마감 기한 (YYYY-MM-DD 형식)
    method: List[str]           # 실행 방법 (단계별)
    estimated_time: str         # 소요 시간
    priority: str               # 우선순위 (상위 규제와 동일)
    status: str                 # 상태 (pending/in_progress/completed)
    evidence: List[EvidenceItem]


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
    evidence: List[EvidenceItem]


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
    citations: List[EvidenceItem]       # 전체 보고서에 포함된 주요 출처


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
    evidence: List[EvidenceItem]


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
            include_domains=["go.kr", "or.kr", "law.go.kr", "korea.kr"]
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


def _merge_evidence(evidence_lists: List[List[EvidenceItem]]) -> List[EvidenceItem]:
    """여러 Evidence 목록을 병합하고 중복을 제거합니다."""
    merged: List[EvidenceItem] = []
    seen: set = set()
    for items in evidence_lists:
        for item in items or []:
            key = (item.get("source_id"), item.get("url"))
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                "source_id": item.get("source_id", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", "")
            })
    return merged


def _normalize_evidence_payload(
    raw_evidence: Union[str, Dict[str, Any], Iterable[Any], None],
    source_lookup: Dict[str, Dict[str, Any]]
) -> List[EvidenceItem]:
    """LLM이 반환한 evidence 필드를 표준 EvidenceItem 리스트로 변환합니다."""
    normalized: List[EvidenceItem] = []
    if not raw_evidence:
        return normalized

    if isinstance(raw_evidence, dict):
        raw_iterable = [raw_evidence]
    elif isinstance(raw_evidence, str):
        raw_iterable = [raw_evidence]
    elif isinstance(raw_evidence, Iterable):
        raw_iterable = list(raw_evidence)
    else:
        raw_iterable = [raw_evidence]

    for entry in raw_iterable:
        if isinstance(entry, dict):
            src_id = entry.get("source_id") or ""
            justification_text = entry.get("justification") or entry.get("excerpt") or ""
        else:
            text = str(entry)
            match = re.match(r"(SRC-\d+)", text.strip())
            src_id = match.group(1) if match else ""
            justification_text = text

        source_meta = source_lookup.get(src_id, {}) if src_id else {}
        # snippet은 원본 유지 (fallback용), justification은 LLM 요약 (우선 사용)
        normalized.append({
            "source_id": src_id,
            "title": source_meta.get("title", ""),
            "url": source_meta.get("url", ""),
            "snippet": source_meta.get("snippet", "")[:300],  # 원본 snippet (fallback)
            "justification": justification_text  # LLM이 생성한 요약 (생략 없음)
        })

    return normalized


def _ensure_dict_list(payload: Any) -> List[Dict[str, Any]]:
    """LLM 응답(payload)을 Dict 리스트 형태로 강제 변환합니다."""
    if payload is None:
        return []

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        return _ensure_dict_list(parsed)

    if isinstance(payload, dict):
        for key in ("items", "checklists", "tasks", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return _ensure_dict_list(value)
        return [payload]

    if isinstance(payload, list):
        normalized_items: List[Dict[str, Any]] = []
        for entry in payload:
            if isinstance(entry, dict):
                normalized_items.append(entry)
                continue
            nested_items = _ensure_dict_list(entry)
            if nested_items:
                normalized_items.extend(nested_items)
        return normalized_items

    return []


def _normalize_task_ids(value: Any) -> List[str]:
    """작업 ID 필드를 문자열 리스트로 변환합니다."""
    if value is None:
        return []

    if isinstance(value, str):
        tokens = [token.strip() for token in re.split(r"[,\s]+", value) if token.strip()]
        return tokens

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        result: List[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
            else:
                text = str(item).strip()
            if text:
                result.append(text)
        return result

    return []


def _normalize_milestones(
    raw_milestones: Any,
    default_task_ids: List[str]
) -> List[Milestone]:
    """마일스톤 목록을 Milestone 스키마에 맞춰 정리합니다."""
    if not isinstance(raw_milestones, Iterable) or isinstance(raw_milestones, (str, bytes, bytearray)):
        return []

    normalized: List[Milestone] = []
    remaining = list(default_task_ids)

    for entry in raw_milestones:
        if not isinstance(entry, dict):
            continue

        name = str(entry.get("name", "")).strip() or "마일스톤"
        deadline = str(entry.get("deadline", "")).strip()
        tasks = _normalize_task_ids(entry.get("tasks"))
        if not tasks:
            if remaining:
                tasks = [remaining.pop(0)]
            else:
                tasks = default_task_ids[:] or []
        else:
            remaining = [task for task in remaining if task not in tasks]

        completion = str(entry.get("completion_criteria", "")).strip()

        normalized.append({
            "name": name,
            "deadline": deadline,
            "tasks": tasks,
            "completion_criteria": completion
        })

    return normalized


def _normalize_dependencies(
    raw_dependencies: Any,
    allowable_tasks: List[str]
) -> Dict[str, List[str]]:
    """의존성 정보를 Dict[str, List[str]] 형태로 정리합니다."""
    normalized: Dict[str, List[str]] = {}
    if not isinstance(raw_dependencies, dict):
        return normalized

    allowable = set(allowable_tasks)

    for key, value in raw_dependencies.items():
        dep_key = str(key).strip()
        if not dep_key:
            continue
        deps = _normalize_task_ids(value)
        if allowable:
            deps = [dep for dep in deps if dep in allowable]
        normalized[dep_key] = deps

    return normalized


def _normalize_parallel_tasks(
    raw_parallel: Any,
    allowable_tasks: List[str]
) -> List[List[str]]:
    """병렬 작업 그룹을 정규화합니다."""
    normalized: List[List[str]] = []
    allowable = set(allowable_tasks)

    if raw_parallel is None:
        return normalized

    candidates: Iterable[Any]
    if isinstance(raw_parallel, str):
        candidates = [raw_parallel]
    elif isinstance(raw_parallel, Iterable) and not isinstance(raw_parallel, (bytes, bytearray)):
        candidates = raw_parallel
    else:
        return normalized

    for group in candidates:
        group_items = _normalize_task_ids(group)
        if allowable:
            group_items = [item for item in group_items if item in allowable]
        if group_items:
            normalized.append(group_items)

    return normalized


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
    md_path = output_dir / "regulation_report_reason.md"
    pdf_path = output_dir / "regulation_report_reason.pdf"

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
    tavily_tool = _build_tavily_tool(max_results=10, search_depth="advanced")

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
    for idx, item in enumerate(search_results, 1):
        structured_results.append({
            "source_id": f"SRC-{idx:03d}",
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

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 검색 결과를 텍스트로 정리
    search_summary = "\n\n".join([
        f"{r.get('source_id', f'DOC-{i+1}')} | {r.get('title', '제목 없음')}\nURL: {r.get('url', '미기재')}\n요약: {r.get('content', '')[:300]}..."
        for i, r in enumerate(search_results[:5])
    ])

    prompt = f"""
다음 정보를 바탕으로 '검색 근거 기반' 규제 분류를 수행하세요.
검색 요약은 [문서ID]로 표기되며, 반드시 해당 ID를 사용해 출처를 지정해야 합니다.

[사업 정보]
업종: {business_info['industry']}
제품: {business_info['product_name']}
원자재: {business_info['raw_materials']}
공정: {', '.join(business_info.get('processes', []))}
직원 수: {business_info.get('employee_count', 0)}명

[검색 요약]
{search_summary}

[생성 지침]
1) 검색 요약에 명시된 문서만 근거로 사용하고, 각 규제마다 1개 이상 출처를 연결합니다.
2) 5~7개의 규제를 제안하되, 신뢰할 수 있는 근거가 없으면 제외하세요.
3) category는 '안전/환경' | '제품 인증' | '공장 운영' 중 하나입니다.
4) key_requirements는 실행형 문장 2~4개.
5) reference_url은 선택한 출처 중 가장 공식적인 URL을 사용합니다.
6) 출력은 JSON 배열이며, 각 항목은 아래 스키마를 따릅니다.

[
  {{
    "name": "규제명",
    "category": "안전/환경|제품 인증|공장 운영",
    "why_applicable": "이 사업에 적용되는 이유",
    "authority": "관할 기관",
    "key_requirements": ["요구사항1", "요구사항2"],
    "reference_url": "https://...",
    "sources": [
      {{
        "source_id": "SRC-001",
        "excerpt": "출처에서 인용한 근거 문장"
      }}
    ]
  }}
]

JSON 이외 텍스트를 출력하지 말고, sources 배열은 최대 3개까지 포함하세요.
"""

    response = llm.invoke(prompt)

    source_lookup = {item.get("source_id"): item for item in search_results if item.get("source_id")}

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
            source_entries = []
            for src in reg.get("sources", []) or []:
                src_id = src.get("source_id")
                matched = source_lookup.get(src_id, {})
                source_entries.append({
                    "source_id": src_id or f"SRC-{idx:03d}",
                    "title": matched.get("title", ""),
                    "url": matched.get("url", ""),
                    "snippet": src.get("excerpt", matched.get("content", ""))[:300]
                })

            primary_url = reg.get("reference_url") or (source_entries[0]["url"] if source_entries else "")

            if not source_entries and primary_url:
                matched = next(
                    (src for src in source_lookup.values() if src.get("url") == primary_url),
                    {}
                )
                source_entries.append({
                    "source_id": matched.get("source_id", f"SRC-{idx:03d}"),
                    "title": matched.get("title", ""),
                    "url": primary_url,
                    "snippet": matched.get("content", "")[:300]
                })

            regulations.append({
                "id": f"REG-{idx:03d}",
                "name": reg.get("name", "미지정"),
                "category": reg.get("category", "안전/환경"),
                "why_applicable": reg.get("why_applicable", ""),
                "authority": reg.get("authority", "미지정"),
                "priority": "MEDIUM",  # 기본값, Prioritizer에서 결정
                "key_requirements": reg.get("key_requirements", []),
                "reference_url": primary_url,
                "sources": source_entries
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

    # 현재 시스템 시간 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")

    for reg in regulations:
        source_summary = "\n".join([
            f"{src.get('source_id','-')} | {src.get('title','제목 없음')}\nURL: {src.get('url','')}\n발췌: {src.get('snippet','')}"
            for src in reg.get('sources', [])
        ]) or "등록된 출처 없음"

        prompt = f"""
다음 규제를 준수하기 위한 실행 가능한 체크리스트를 생성하세요.
각 작업마다 실제 인터넷 출처(source_id)를 evidence 배열에 포함해야 합니다.

[규제 정보]
규제명: {reg['name']}
카테고리: {reg['category']}
관할 기관: {reg['authority']}
우선순위: {reg['priority']}
적용 이유: {reg['why_applicable']}
주요 요구사항:
{chr(10).join('  - ' + req for req in reg['key_requirements'])}

[사용 가능한 출처]
{source_summary}

[현재 날짜]
{current_date}

[생성 지침]
1) 작업 수: 3~5개.
2) method[0]에는 "(매핑: 요구사항 N)" 형식으로 매핑 정보를 기재합니다.
3) evidence에는 [사용 가능한 출처]에서 선택한 source_id와 해당 출처의 핵심 문장을 1~2개 포함합니다.
4) method 단계는 3~5개, 마지막 단계에는 증빙/기록 확보를 포함합니다.
5) deadline은 현재 날짜({current_date})를 기준으로 우선순위에 맞게 YYYY-MM-DD 형식으로 계산합니다.
   - HIGH: 현재일 + 1~3개월
   - MEDIUM: 현재일 + 3~6개월
   - LOW: 현재일 + 6~12개월
6) estimated_time은 실제 소요 시간을 구체적으로 작성합니다 (예: "2주", "1개월").
7) JSON 배열 외 텍스트는 금지합니다.

[출력 스키마]
{{
  "task_name": "구체적인 작업명(명령형)",
  "responsible_dept": "담당 부서",
  "deadline": "YYYY-MM-DD",
  "method": [
    "1. (매핑: 요구사항 N) ...",
    "2. ...",
    "3. ...",
    "4. ...",
    "5. ..."
  ],
  "estimated_time": "소요 시간",
  "evidence": [
    {{
      "source_id": "SRC-001",
      "justification": "출처에서 확인한 핵심 문장"
    }}
  ]
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

            raw_payload = json.loads(content.strip())
            checklist_items = _ensure_dict_list(raw_payload)

            if not checklist_items:
                print("      ⚠️  체크리스트 응답이 비어 있거나 형식이 올바르지 않습니다.")
                continue

            source_lookup = {
                src.get("source_id"): src for src in reg.get("sources", [])
                if src.get("source_id")
            }

            # ChecklistItem 형식으로 변환
            for item in checklist_items:
                if not isinstance(item, dict):
                    continue

                evidence_entries = _normalize_evidence_payload(
                    item.get("evidence"),
                    source_lookup
                )

                method_steps = item.get("method") or []
                if isinstance(method_steps, str):
                    method_steps = [method_steps]

                all_checklists.append({
                    "regulation_id": reg['id'],
                    "regulation_name": reg['name'],
                    "task_name": item.get("task_name", ""),
                    "responsible_dept": item.get("responsible_dept", "담당 부서"),
                    "deadline": item.get("deadline", "미정"),
                    "method": method_steps,
                    "estimated_time": item.get("estimated_time", "미정"),
                    "priority": reg['priority'],
                    "status": "pending",
                    "evidence": evidence_entries
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

        task_ids = [str(i + 1) for i in range(len(reg_checklists))]

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
            if isinstance(plan_data, list):
                plan_data = plan_data[0] if plan_data else {}
            if not isinstance(plan_data, dict):
                plan_data = {}

            plan_evidence = _merge_evidence([item.get("evidence", []) for item in reg_checklists])

            milestones = _normalize_milestones(
                plan_data.get("milestones"),
                task_ids
            )

            dependencies = _normalize_dependencies(
                plan_data.get("dependencies"),
                task_ids
            )

            parallel_tasks = _normalize_parallel_tasks(
                plan_data.get("parallel_tasks"),
                task_ids
            )

            critical_path = _normalize_task_ids(plan_data.get("critical_path"))
            if task_ids:
                critical_path = [cp for cp in critical_path if cp in task_ids]
                if not critical_path:
                    critical_path = task_ids[:]

            default_start = (
                "즉시" if reg_priority == "HIGH"
                else "1개월 내" if reg_priority == "MEDIUM"
                else "3개월 내"
            )

            execution_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": task_ids,
                "timeline": str(plan_data.get("timeline") or "3개월"),
                "start_date": str(plan_data.get("start_date") or default_start),
                "milestones": milestones,
                "dependencies": dependencies,
                "parallel_tasks": parallel_tasks,
                "critical_path": critical_path,
                "evidence": plan_evidence
            }

            all_execution_plans.append(execution_plan)

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            # 기본 실행 계획 생성
            plan_evidence = _merge_evidence([item.get("evidence", []) for item in reg_checklists])

            default_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": task_ids,
                "timeline": "3개월",
                "start_date": "즉시" if reg_priority == "HIGH" else "1개월 내",
                "milestones": [],
                "dependencies": {},
                "parallel_tasks": [],
                "critical_path": task_ids,
                "evidence": plan_evidence
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

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    risk_items = []

    for reg in regulations:
        source_summary = "\n".join([
            f"{src.get('source_id','-')} | {src.get('title','제목 없음')}\nURL: {src.get('url','')}\n발췌: {src.get('snippet','')}"
            for src in reg.get('sources', [])
        ]) or "등록된 출처 없음"

        prompt = f"""
다음 규제를 준수하지 않았을 때의 리스크를 평가하세요.
근거는 [사용 가능한 출처]에서 선택한 항목만 활용하고 evidence 배열에 포함하세요.

[규제 정보]
규제명: {reg['name']}
카테고리: {reg['category']}
관할 기관: {reg['authority']}
우선순위: {reg['priority']}
적용 이유: {reg['why_applicable']}

[사업 정보]
제품: {business_info['product_name']}
직원 수: {business_info.get('employee_count', 0)}명

[사용 가능한 출처]
{source_summary}

[출력 스키마]
{{
  "penalty_amount": "벌금액 (예: 최대 1억원, 300만원 이하, 없으면 \"\")",
  "penalty_type": "벌칙 유형 (형사처벌|과태료|행정처분|\"\" )",
  "business_impact": "사업 영향 (예: 영업정지 6개월, 인허가 취소, 없으면 \"\")",
  "risk_score": 0-10 사이 숫자,
  "past_cases": [
    "과거 처벌 사례 1 (연도, 기업, 처벌 내용)"
  ],
  "mitigation": "리스크 완화 방안 (1-2문장)",
  "evidence": [
    {{
      "source_id": "SRC-001",
      "justification": "출처에서 인용한 핵심 문장"
    }}
  ]
}}

JSON 이외 텍스트는 금지합니다.
"""

        response = llm.invoke(prompt)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            risk_data = json.loads(content.strip())

            source_lookup = {
                src.get("source_id"): src for src in reg.get("sources", [])
                if src.get("source_id")
            }

            raw_score = risk_data.get("risk_score", 5.0)
            try:
                risk_score = float(raw_score)
            except (TypeError, ValueError):
                risk_score = 5.0

            evidence_entries = _normalize_evidence_payload(
                risk_data.get("evidence"),
                source_lookup
            )

            risk_item: RiskItem = {
                "regulation_id": reg['id'],
                "regulation_name": reg['name'],
                "penalty_amount": risk_data.get("penalty_amount", "") or "",
                "penalty_type": risk_data.get("penalty_type", "") or "",
                "business_impact": risk_data.get("business_impact", "") or "",
                "risk_score": risk_score,
                "past_cases": risk_data.get("past_cases", []),
                "mitigation": risk_data.get("mitigation", ""),
                "evidence": evidence_entries
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
                "mitigation": "전문가 상담 권장",
                "evidence": []
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

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

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

    regulation_evidence = _merge_evidence([reg.get('sources', []) for reg in regulations])
    checklist_evidence = _merge_evidence([item.get('evidence', []) for item in checklists])
    execution_plan_evidence = _merge_evidence([plan.get('evidence', []) for plan in execution_plans])
    risk_evidence = _merge_evidence([
        item.get('evidence', []) for bucket in risk_assessment.get('risk_matrix', {}).values()
        for item in bucket
    ] if isinstance(risk_assessment.get('risk_matrix'), dict) else [])
    all_citations = _merge_evidence([
        regulation_evidence,
        checklist_evidence,
        execution_plan_evidence,
        risk_evidence
    ])

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

"""
            # 주요 요구사항을 list 형식으로 출력 (각 항목 사이에 빈 줄 추가)
            key_reqs = reg.get('key_requirements', [])
            for idx, req in enumerate(key_reqs):
                full_markdown += f"- {req}"
                # 마지막 항목이 아니면 줄바꿈 추가
                if idx < len(key_reqs) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"
            if reg.get('penalty'):
                full_markdown += f"**벌칙:** {reg['penalty']}\n\n"

            if reg.get('sources'):
                full_markdown += "**근거 출처:**\n\n"
                for idx, src in enumerate(reg['sources']):
                    link_title = src.get('title') or src.get('url', '').split('/')[2]
                    url = src.get('url', '')
                    # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
                    summary = src.get('justification') or (src.get('snippet') or "").replace('\n', ' ')
                    full_markdown += "  - "
                    if url:
                        full_markdown += f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
                    else:
                        full_markdown += f"**[{link_title}]**\t{summary}"
                    # 마지막 항목이 아니면 줄바꿈 추가
                    if idx < len(reg['sources']) - 1:
                        full_markdown += "\n\n"
                    else:
                        full_markdown += "\n"
                full_markdown += "\n"

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
                full_markdown += "\n"
                if item.get('evidence'):
                    full_markdown += "  **근거 출처:**\n\n"
                    for idx, ev in enumerate(item['evidence']):
                        link_title = ev.get('title') or ev.get('url', '').split('/')[2]
                        url = ev.get('url', '')
                        # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
                        summary = ev.get('justification') or (ev.get('snippet') or "").replace('\n', ' ')
                        full_markdown += "  - "
                        if url:
                            full_markdown += f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
                        else:
                            full_markdown += f"**[{link_title}]**\t{summary}"
                        # 마지막 항목이 아니면 줄바꿈 추가
                        if idx < len(item['evidence']) - 1:
                            full_markdown += "\n\n  "
                        else:
                            full_markdown += "\n"
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
            full_markdown += "**주요 마일스톤:**\n\n"
            milestones = plan['milestones']
            for idx, milestone in enumerate(milestones):
                full_markdown += f"- {milestone['name']} (완료 목표: {milestone['deadline']})"
                # 마지막 항목이 아니면 줄바꿈 추가
                if idx < len(milestones) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"

        if plan.get('evidence'):
            full_markdown += "**근거 출처:**\n\n"
            for idx, ev in enumerate(plan['evidence']):
                link_title = ev.get('title') or ev.get('url', '').split('/')[2]
                url = ev.get('url', '')
                # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
                summary = ev.get('justification') or (ev.get('snippet') or "").replace('\n', ' ')
                full_markdown += "  - "
                if url:
                    full_markdown += f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
                else:
                    full_markdown += f"**[{link_title}]**\t{summary}"
                # 마지막 항목이 아니면 줄바꿈 추가
                if idx < len(plan['evidence']) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"

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

            if item.get('evidence'):
                full_markdown += "**근거 출처:**\n\n"
                for idx, ev in enumerate(item['evidence']):
                    link_title = ev.get('title') or ev.get('url', '').split('/')[2]
                    url = ev.get('url', '')
                    # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
                    summary = ev.get('justification') or (ev.get('snippet') or "").replace('\n', ' ')
                    full_markdown += "  - "
                    if url:
                        full_markdown += f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
                    else:
                        full_markdown += f"**[{link_title}]**\t{summary}"
                    # 마지막 항목이 아니면 줄바꿈 추가
                    if idx < len(item['evidence']) - 1:
                        full_markdown += "\n\n"
                    else:
                        full_markdown += "\n"
                full_markdown += "\n"

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

    if all_citations:
        full_markdown += "\n---\n\n## 9. 근거 출처 모음\n\n"
        for idx, citation in enumerate(all_citations, 1):
            link_title = citation.get('title') or citation.get('url', '').split('/')[2]
            url = citation.get('url', '')
            # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
            summary = citation.get('justification') or (citation.get('snippet') or "").replace('\n', ' ')
            full_markdown += "  - "
            if url:
                full_markdown += f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
            else:
                full_markdown += f"**[{link_title}]**\t{summary}"
            # 마지막 항목이 아니면 줄바꿈 추가
            if idx < len(all_citations):
                full_markdown += "\n\n"
            else:
                full_markdown += "\n"

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
        penalty = item.get('penalty_type') or "제재 정보 없음"
        impact = item.get('business_impact') or "영향 정보 미기재"
        risk_highlights.append(
            f"{item['regulation_name']} 미준수 시 {penalty} - {impact}"
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
        "report_pdf_path": report_pdf_path,
        "citations": all_citations
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

    실행 순서 (병렬 처리 최적화):
    1. analyzer: 사업 정보 분석 및 키워드 추출
    2. searcher: Tavily로 규제 검색
    3. classifier: 규제 분류
    4. prioritizer: 우선순위 결정
    5-6. [병렬 실행]
         - checklist_generator: 규제별 체크리스트 생성
         - risk_assessor: 리스크 평가
    7. planning_agent: 실행 계획 수립 (checklist_generator 완료 후)
    8. report_generator: 최종 보고서 생성 (planning_agent + risk_assessor 완료 후)

    병렬화 이점: Risk Assessment Agent가 Checklist Generator/Planning Agent와
                동시 실행되어 전체 소요 시간 약 30초~1분 단축
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

    # 엣지 추가: 순차 실행 (Prioritizer까지)
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "searcher")
    graph.add_edge("searcher", "classifier")
    graph.add_edge("classifier", "prioritizer")

    # 병렬 실행: Prioritizer 이후 Checklist Generator와 Risk Assessor 동시 시작
    graph.add_edge("prioritizer", "checklist_generator")
    graph.add_edge("prioritizer", "risk_assessor")

    # Checklist Generator → Planning Agent (순차)
    graph.add_edge("checklist_generator", "planning_agent")

    # Report Generator는 Planning Agent와 Risk Assessor 모두 완료 후 실행
    graph.add_edge("planning_agent", "report_generator")
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
            "next_steps": [],
            "full_markdown": "",
            "report_pdf_path": "",
            "citations": []
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
            if item['method']:
                print(f"      실행 방법:")
                for method in item['method'][:3]:  # 최대 3단계만 표시
                    print(f"         {method}")
            if item.get('evidence'):
                print("      근거:")
                for ev in item['evidence'][:2]:
                    title = ev.get("title") or ev.get("url", "")
                    url = ev.get("url", "")
                    print(f"         - {title} ({url})")

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

        evidence = plan.get('evidence', [])
        if evidence:
            print("   📎 근거:")
            for ev in evidence[:3]:
                title = ev.get("title") or ev.get("url", "")
                url = ev.get("url", "")
                print(f"      - {title} ({url})")
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

    citations = final_report.get('citations', [])
    if citations:
        print("🔗 주요 출처:")
        for ev in citations[:5]:
            title = ev.get("title") or ev.get("url", "")
            url = ev.get("url", "")
            print(f"   - {title} ({url})")
        if len(citations) > 5:
            print("   ...")
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
            if item.get('evidence'):
                print("      근거:")
                for ev in item['evidence'][:2]:
                    title = ev.get("title") or ev.get("url", "")
                    url = ev.get("url", "")
                    print(f"         - {title} ({url})")
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
    start_time = time.time()

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
        if reg.get('sources'):
            print("   근거:")
            for src in reg['sources'][:3]:
                title = src.get("title") or src.get("url", "")
                url = src.get("url", "")
                print(f"      - {title} ({url})")
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
    end_time = time.time()
    print(f"⏱️ 총 처리 시간: {end_time - start_time:.2f}초")

    # JSON 파일로 저장 (모든 데이터 포함)
    # complete_output = {
    #     "business_info": result.get('business_info', {}),
    #     "summary": {
    #         "total_regulations": final_output.get('total_count', 0),
    #         "priority_distribution": priority_dist,
    #         "total_checklist_items": len(result.get('checklists', [])),
    #         "total_execution_plans": len(result.get('execution_plans', [])),
    #         "risk_score": result.get('risk_assessment', {}).get('total_risk_score', 0.0)
    #     },
    #     "regulations": regulations,
    #     "checklists": result.get('checklists', []),
    #     "execution_plans": result.get('execution_plans', []),
    #     "risk_assessment": result.get('risk_assessment', {}),
    #     "final_report": result.get('final_report', {})
    # }

    # output_file = "regulation_analysis_result.json"
    # with open(output_file, 'w', encoding='utf-8') as f:
    #     json.dump(complete_output, f, indent=2, ensure_ascii=False)

    # print(f"💾 전체 결과가 '{output_file}' 파일로 저장되었습니다.")
    # print()


if __name__ == "__main__":
    main()
