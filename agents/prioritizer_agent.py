"""Prioritizer Agent - 규제 우선순위 결정 (HIGH/MEDIUM/LOW)"""

from typing import List, Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from models import BusinessInfo, Regulation


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
