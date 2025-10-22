"""Checklist Generator Agent - 규제별 실행 가능한 체크리스트 생성"""

import json
from typing import List, Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from models import Regulation


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
                    "estimated_time": item.get("estimated_time", "미정"),
                    "priority": reg['priority'],
                    "status": "pending"
                })

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            continue

    print(f"   ✓ 체크리스트 생성 완료: 총 {len(all_checklists)}개 항목\n")

    return {"checklists": all_checklists}
