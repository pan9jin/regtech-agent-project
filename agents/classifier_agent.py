"""Classifier Agent - 검색된 규제 분류 및 적용성 판단"""

import json
from typing import List, Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from models import BusinessInfo, Regulation


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
