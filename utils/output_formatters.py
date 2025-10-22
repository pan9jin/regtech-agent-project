"""출력 포맷팅 헬퍼 함수"""

from typing import List

from models import ChecklistItem, RiskAssessment


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
