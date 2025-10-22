"""
Planning Agent - 실행 계획 수립
"""

from typing import Dict, Any, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import json

from ..models import Regulation, ChecklistItem, ExecutionPlan, Milestone
from ..utils import (
    normalize_evidence_payload,
    normalize_milestones,
    normalize_dependencies,
    normalize_parallel_tasks,
    normalize_task_ids,
    ensure_dict_list,
    merge_evidence
)


@tool
def plan_execution(
    regulations: List[Regulation],
    checklists: List[ChecklistItem]
) -> Dict[str, Any]:
    """체크리스트를 실행 가능한 계획으로 변환합니다.

    Args:
        regulations: 규제 목록
        checklists: 체크리스트 목록

    Returns:
        실행 계획 목록
    """
    print("📅 [Planning Agent] 실행 계획 수립 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 규제별로 체크리스트 그룹핑
    checklists_by_regulation = {}
    for item in checklists:
        reg_id = item['regulation_id']
        if reg_id not in checklists_by_regulation:
            checklists_by_regulation[reg_id] = []
        checklists_by_regulation[reg_id].append(item)

    all_execution_plans = []

    for reg in regulations:
        reg_id = reg['id']
        reg_name = reg['name']
        reg_priority = reg['priority']

        # 해당 규제의 체크리스트 항목들
        reg_checklists = checklists_by_regulation.get(reg_id, [])

        if not reg_checklists:
            continue

        task_ids = [str(i + 1) for i in range(len(reg_checklists))]

        # 체크리스트 요약
        checklist_summary = "\n".join([
            f"{i+1}. {item['task_name']}\n   담당: {item['responsible_dept']}\n   마감: {item['deadline']}\n   기간: {item['estimated_time']}"
            for i, item in enumerate(reg_checklists)
        ])

        prompt = f"""
다음 규제의 체크리스트를 바탕으로 실행 계획을 수립하세요.

[규제 정보]
규제명: {reg_name}
우선순위: {reg_priority}

[체크리스트 항목들]
{checklist_summary}

다음 정보를 분석하여 JSON 형식으로 제공하세요:
1. 전체 예상 소요 기간 (timeline)
2. 시작 시점 (start_date: "즉시", "1개월 내", "공장등록 후" 등)
3. 마일스톤 (3-5개, 각 마일스톤마다 name, deadline, completion_criteria 포함)
4. 작업 간 의존성 (dependencies: 어떤 작업이 먼저 완료되어야 하는지)
5. 병렬 처리 가능한 작업 그룹 (parallel_tasks)
6. 크리티컬 패스 (critical_path: 가장 오래 걸리는 경로의 작업 번호들)

출력 형식:
{{
    "timeline": "3개월",
    "start_date": "즉시",
    "milestones": [
        {{
            "name": "1개월 차: 서류 준비 완료",
            "deadline": "30일 내",
            "tasks": ["1", "2"],
            "completion_criteria": "필요 서류 모두 준비"
        }}
    ],
    "dependencies": {{
        "2": ["1"],
        "3": ["1", "2"]
    }},
    "parallel_tasks": [
        ["1", "2"],
        ["3", "4"]
    ],
    "critical_path": ["1", "2", "5"]
}}

참고:
- 우선순위 HIGH는 즉시 시작
- 우선순위 MEDIUM은 1-3개월 내
- 우선순위 LOW는 6개월 내
- dependencies의 키는 작업 번호(문자열), 값은 선행 작업 번호 리스트
- parallel_tasks는 동시에 진행 가능한 작업 그룹들의 리스트

출력은 JSON 형식으로만 작성하세요.
"""

        response = llm.invoke(prompt)

        try:
            # JSON 파싱
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            plan_data = json.loads(content.strip())
            if isinstance(plan_data, list):
                plan_data = plan_data[0] if plan_data else {}
            if not isinstance(plan_data, dict):
                plan_data = {}

            plan_evidence = merge_evidence([item.get("evidence", []) for item in reg_checklists])

            milestones = normalize_milestones(
                plan_data.get("milestones"),
                task_ids
            )

            dependencies = normalize_dependencies(
                plan_data.get("dependencies"),
                task_ids
            )

            parallel_tasks = normalize_parallel_tasks(
                plan_data.get("parallel_tasks"),
                task_ids
            )

            critical_path = normalize_task_ids(plan_data.get("critical_path"))
            if task_ids:
                critical_path = [cp for cp in critical_path if cp in task_ids]
                if not critical_path:
                    critical_path = task_ids[:]

            default_start = (
                "즉시" if reg_priority == "HIGH"
                else "1개월 내" if reg_priority == "MEDIUM"
                else "3개월 내"
            )

            execution_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": task_ids,
                "timeline": str(plan_data.get("timeline") or "3개월"),
                "start_date": str(plan_data.get("start_date") or default_start),
                "milestones": milestones,
                "dependencies": dependencies,
                "parallel_tasks": parallel_tasks,
                "critical_path": critical_path,
                "evidence": plan_evidence
            }

            all_execution_plans.append(execution_plan)

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            # 기본 실행 계획 생성
            plan_evidence = merge_evidence([item.get("evidence", []) for item in reg_checklists])

            default_plan: ExecutionPlan = {
                "plan_id": f"PLAN-{len(all_execution_plans) + 1:03d}",
                "regulation_id": reg_id,
                "regulation_name": reg_name,
                "checklist_items": task_ids,
                "timeline": "3개월",
                "start_date": "즉시" if reg_priority == "HIGH" else "1개월 내",
                "milestones": [],
                "dependencies": {},
                "parallel_tasks": [],
                "critical_path": task_ids,
                "evidence": plan_evidence
            }
            all_execution_plans.append(default_plan)

    print(f"   ✓ 실행 계획 수립 완료: 총 {len(all_execution_plans)}개 계획\n")

    return {"execution_plans": all_execution_plans}