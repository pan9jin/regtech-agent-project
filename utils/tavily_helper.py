"""Tavily API 관련 헬퍼 함수"""

from typing import List, Dict, Any
from langchain_tavily import TavilySearch


def build_tavily_tool(max_results: int = 8, search_depth: str = "basic") -> TavilySearch:
    """TavilySearch 인스턴스를 생성합니다.

    Args:
        max_results: 최대 검색 결과 수
        search_depth: 검색 깊이 ('basic' 또는 'advanced')

    Returns:
        TavilySearch 인스턴스

    Raises:
        RuntimeError: TavilySearch 초기화 실패 시
    """
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


def extract_results(payload: Any) -> List[Dict[str, Any]]:
    """Tavily API 응답에서 결과 목록을 추출합니다.

    Args:
        payload: Tavily API 응답 데이터

    Returns:
        검색 결과 목록
    """
    if isinstance(payload, dict) and "results" in payload:
        return payload.get("results", []) or []
    if isinstance(payload, dict) and {"title", "url"}.issubset(payload.keys()):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []
