"""
Classifier Agent - 규제 분류 및 적용성 판단
"""

from typing import Dict, Any, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import json

from ..models import BusinessInfo


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
