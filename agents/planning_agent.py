"""Planning Agent: 체크리스트 항목에 대한 구체적인 실행 계획을 수립합니다."""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from models import ChecklistItem

@tool
def create_action_plan(checklist_item: ChecklistItem) -> Dict[str, Any]:
    """체크리스트 항목을 실행하기 위한 구체적인 행동 계획을 생성합니다.

    Args:
        checklist_item: 계획을 수립할 체크리스트 항목

    Returns:
        행동 계획이 포함된 딕셔너리
    """
    print(f"📝 [Planning Agent] '{checklist_item['task_name']}'에 대한 실행 계획 수립 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    prompt = f"""
다음 체크리스트 항목을 이행하기 위한 구체적이고 실행 가능한 단계별 계획을 3~5단계로 작성하세요.

[체크리스트 항목]
- 작업명: {checklist_item['task_name']}
- 담당 부서: {checklist_item['responsible_dept']}
- 마감 기한: {checklist_item['deadline']}
- 규제명: {checklist_item['regulation_name']}

[실행 방법 개요]
{chr(10).join(f'- {m}' for m in checklist_item['method'])}

[출력 형식]
각 단계를 명확하고 간결한 문장으로 작성하세요. 각 단계는 실행 가능한 행동이어야 합니다.

예시:
- 1단계: 관련 법규 및 최신 개정안 확인 (국가법령정보센터 활용)
- 2단계: 내부 규정 및 절차서 현행화
- 3단계: 변경 사항에 대한 전 직원 대상 교육 실시
- 4단계: 교육 이수 현황 및 효과성 점검
- 5단계: 관련 기록 및 문서 보관

출력은 단계별 계획 목록만 포함해야 합니다. (JSON 형식이 아님)
    """

    response = llm.invoke(prompt)
    plan = [p.strip() for p in response.content.strip().split('\n') if p.strip()]

    print(f"   ✓ 실행 계획 수립 완료: {len(plan)} 단계")

    return {"action_plan": plan}

