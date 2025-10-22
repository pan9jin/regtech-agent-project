"""Risk Assessment Agent - 미준수 시 리스크 평가 및 완화 방안 제시"""

import json
from typing import List, Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from models import BusinessInfo, Regulation, RiskAssessment, RiskItem


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
