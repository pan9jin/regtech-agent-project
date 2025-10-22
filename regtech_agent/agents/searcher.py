"""
Search Agent - Tavily API를 통한 규제 정보 검색
"""

from typing import Dict, Any, List
from langchain.tools import tool

from ..utils import build_tavily_tool, extract_results, truncate


@tool
def search_regulations(keywords: List[str], user_query: str='') -> Dict[str, Any]:
    """Tavily API를 사용하여 관련 규제 정보를 웹에서 검색합니다.

    Args:
        keywords: 검색 키워드 목록
        user_query: 사용자 지정 검색 쿼리 (선택 사항)

    Returns:
        검색된 규제 정보 목록
    """
    print("🌐 [Search Agent] Tavily로 규제 정보 검색 중...")
    print(f"   검색 키워드: {', '.join(keywords[:3])}...")

    # TavilySearch 도구 생성
    tavily_tool = build_tavily_tool(max_results=10, search_depth="advanced")

    # 검색 쿼리 생성
    if user_query:
        query = f"{' '.join(keywords)} {user_query}"
    else:
        query = f"{' '.join(keywords)} 제조업 규제 법률 안전 인증 한국"

    # Tavily 검색 실행
    raw = tavily_tool.invoke({"query": query})

    # 결과 추출
    search_results = extract_results(raw)

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
            "content": truncate(item.get("content", ""), 300),
            "score": item.get("score", 0.0),
        })

    return {"search_results": structured_results}
