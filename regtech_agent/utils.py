"""
RegTech Agent Helper 함수들
"""

import re
import json
from typing import List, Dict, Any, Iterable, Union
from pathlib import Path
from markdown import markdown
from weasyprint import HTML, CSS
from urllib.parse import urlparse

from langchain_tavily import TavilySearch

from .models import EvidenceItem, Milestone


def build_tavily_tool(max_results: int = 8, search_depth: str = "basic") -> TavilySearch:
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


def extract_results(payload: Any) -> List[Dict[str, Any]]:
    """Tavily API 응답에서 결과 목록을 추출합니다."""
    if isinstance(payload, dict) and "results" in payload:
        return payload.get("results", []) or []
    if isinstance(payload, dict) and {"title", "url"}.issubset(payload.keys()):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def truncate(text: str, limit: int = 300) -> str:
    """텍스트를 지정된 길이로 자릅니다."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def merge_evidence(evidence_lists: List[List[EvidenceItem]]) -> List[EvidenceItem]:
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


def normalize_evidence_payload(
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


def ensure_dict_list(payload: Any) -> List[Dict[str, Any]]:
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
        return ensure_dict_list(parsed)

    if isinstance(payload, dict):
        for key in ("items", "checklists", "tasks", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return ensure_dict_list(value)
        return [payload]

    if isinstance(payload, list):
        normalized_items: List[Dict[str, Any]] = []
        for entry in payload:
            if isinstance(entry, dict):
                normalized_items.append(entry)
                continue
            nested_items = ensure_dict_list(entry)
            if nested_items:
                normalized_items.extend(nested_items)
        return normalized_items

    return []


def normalize_task_ids(value: Any) -> List[str]:
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


def normalize_milestones(
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
        tasks = normalize_task_ids(entry.get("tasks"))
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


def normalize_dependencies(
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
        deps = normalize_task_ids(value)
        if allowable:
            deps = [dep for dep in deps if dep in allowable]
        normalized[dep_key] = deps

    return normalized


def normalize_parallel_tasks(
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
        group_items = normalize_task_ids(group)
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


def format_evidence_link(evidence: Dict[str, Any]) -> str:
    """근거 출처를 마크다운 링크 형식으로 포맷합니다.

    Args:
        evidence: 근거 출처 정보 (title, url, justification, snippet 포함)

    Returns:
        포맷된 마크다운 링크 문자열
    """
    # hostname 추출 및 표시 이름 정리
    url = (evidence.get('url') or '').strip()
    parsed = urlparse(url) if url else None
    hostname = parsed.hostname if parsed else None

    raw_title = (evidence.get('title') or '').strip()

    def _clean_hostname(candidate: str) -> str:
        if candidate:
            stripped = candidate.split('//')[-1].split('/')[0]
            return stripped or 'Unknown'
        if hostname:
            return hostname
        return 'Unknown'

    link_title = raw_title or hostname or _clean_hostname(url)
    if raw_title and url and raw_title.lower() == url.lower():
        link_title = hostname or _clean_hostname(url)
    if link_title.lower().startswith(('http://', 'https://')):
        link_title = _clean_hostname(link_title)
    if not link_title and hostname:
        link_title = hostname
    if not link_title:
        link_title = 'Unknown'
    # justification 우선 사용 (LLM 요약), 없으면 snippet 사용
    summary = evidence.get('justification') or (evidence.get('snippet') or "").replace('\n', ' ')

    if url:
        return f"**[<a href=\"{url}\">{link_title}</a>]**\t{summary}"
    else:
        return f"**[{link_title}]**\t{summary}"
