"""규제 AI Agent 서비스 + 워크플로우 자동화 - 메인 실행 파일

LangGraph Multi-Agent Workflow + Task Automation
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from langsmith import Client

from models import BusinessInfo
from workflows import run_regulation_agent
from workflows.orchestrator import WorkflowOrchestrator
from utils import print_checklists, print_risk_assessment

# 환경 변수 로드
load_dotenv()

# LangSmith API 클라이언트 생성
client = Client()


def print_workflow_status(workflow_status: dict):
    """워크플로우 상태를 보기 좋게 출력"""
    print("🔄 워크플로우 현황")
    print("=" * 60)
    print()

    print(f"📊 전체 상태:")
    print(f"   총 Task: {workflow_status['total_tasks']}개")
    print(f"   완료: {workflow_status['completed']}개")
    print(f"   진행 중: {workflow_status['in_progress']}개")
    print(f"   승인 대기: {workflow_status['waiting_approval']}개")
    print(f"   대기: {workflow_status['pending']}개")
    print(f"   자동화 비율: {workflow_status['automation_rate']}%")
    print()

    # Task 유형별 집계
    tasks = workflow_status['tasks']
    task_types = {}
    for task in tasks:
        task_type = task.get('task_type', 'manual')
        task_types[task_type] = task_types.get(task_type, 0) + 1

    type_emoji = {
        'automated': '🤖',
        'semi_auto': '🔄',
        'manual': '👤',
        'monitoring': '📊'
    }

    type_names = {
        'automated': '완전 자동화',
        'semi_auto': '반자동화',
        'manual': '수동 작업',
        'monitoring': '모니터링'
    }

    print(f"📋 Task 유형별 분류:")
    for task_type, count in task_types.items():
        emoji = type_emoji.get(task_type, '📝')
        name = type_names.get(task_type, task_type)
        print(f"   {emoji} {name}: {count}개")
    print()

    # Task 목록 (우선순위별)
    priority_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_tasks = sorted(
        tasks,
        key=lambda x: priority_order.get(x.get('priority', 'MEDIUM'), 2)
    )

    print(f"📝 Task 목록 (우선순위 순):")
    print("-" * 60)

    for task in sorted_tasks[:10]:  # 상위 10개만 표시
        priority = task.get('priority', 'MEDIUM')
        status = task.get('status', 'pending')
        task_type = task.get('task_type', 'manual')

        priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        status_emoji = {
            "completed": "✅",
            "in_progress": "⏳",
            "waiting_approval": "⏸️",
            "pending": "⭕",
            "failed": "❌"
        }

        p_emoji = priority_emoji.get(priority, "⚪")
        s_emoji = status_emoji.get(status, "⭕")
        t_emoji = type_emoji.get(task_type, "📝")

        print(f"\n{p_emoji} [{priority}] {task['task_name']}")
        print(f"   상태: {s_emoji} {status}")
        print(f"   유형: {t_emoji} {type_names.get(task_type, task_type)}")
        print(f"   담당: {task.get('responsible_dept', '미정')}")
        print(f"   예상 비용: {task.get('estimated_cost', 0):,}원")
        print(f"   예상 시간: {task.get('estimated_time_hours', 0)}시간")

    if len(sorted_tasks) > 10:
        print(f"\n   ... 외 {len(sorted_tasks) - 10}개 Task")

    print()


async def main_with_workflow():
    """워크플로우 자동화가 포함된 메인 실행 함수"""

    print("=" * 60)
    print("🤖 규제 AI Agent + 워크플로우 자동화 시스템")
    print("=" * 60)
    print()

    # 샘플 사업 정보 (배터리 제조업)
    sample_business_info: BusinessInfo = {
        "industry": "배터리 제조",
        "product_name": "리튬이온 배터리",
        "raw_materials": "리튬, 코발트, 니켈",
        "processes": ["화학 처리", "고온 가공", "조립"],
        "employee_count": 45,
        "sales_channels": ["B2B", "수출"],
        "export_countries": ["미국", "유럽"]
    }

    print("📝 입력된 사업 정보:")
    print(json.dumps(sample_business_info, indent=2, ensure_ascii=False))
    print()
    print("-" * 60)
    print()

    # ========================================
    # Step 1: 규제 분석 (기존 Agent 워크플로우)
    # ========================================
    print("🔍 Step 1: 규제 분석 시작...")
    print()

    try:
        result = run_regulation_agent(sample_business_info)
    except Exception as exc:
        print(f"[ERROR] 분석 파이프라인이 실패했습니다: {exc}")
        raise

    # 분석 결과 출력
    print("=" * 60)
    print("✅ Step 1 완료 - 규제 분석 결과")
    print("=" * 60)
    print()

    final_output = result.get('final_output', {})

    print(f"📊 요약")
    print(f"   총 규제 개수: {final_output.get('total_count', 0)}개")
    print(f"   체크리스트 항목: {len(result.get('checklists', []))}개")
    print()

    # ========================================
    # Step 2: 워크플로우 생성
    # ========================================
    print("=" * 60)
    print("🔄 Step 2: 워크플로우 자동화 시작...")
    print("=" * 60)
    print()

    orchestrator = WorkflowOrchestrator()

    # 각 규제에 대해 워크플로우 생성
    all_workflow_tasks = []
    regulations = final_output.get('regulations', [])
    checklists = result.get('checklists', [])

    for regulation in regulations:
        # 해당 규제의 체크리스트만 필터링
        regulation_checklists = [
            checklist for checklist in checklists
            if checklist['regulation_id'] == regulation['id']
        ]

        if regulation_checklists:
            print(f"   📋 {regulation['name']} - 워크플로우 생성 중...")

            workflow_tasks = orchestrator.create_workflow_from_checklists(
                regulation=regulation,
                checklists=regulation_checklists
            )

            all_workflow_tasks.extend(workflow_tasks)

            print(f"      ✓ {len(workflow_tasks)}개 Task 생성 완료")

    print()
    print(f"✅ 전체 {len(all_workflow_tasks)}개 Task가 생성되었습니다!")
    print()

    # ========================================
    # Step 3: 자동화 가능한 Task 실행
    # ========================================
    print("=" * 60)
    print("🤖 Step 3: 자동화 Task 실행...")
    print("=" * 60)
    print()

    for regulation in regulations:
        regulation_id = regulation['id']

        print(f"   규제: {regulation['name']}")

        try:
            result_exec = await orchestrator.execute_automated_tasks(regulation_id)

            executed = result_exec.get('executed_tasks', 0)
            if executed > 0:
                print(f"   ✓ {executed}개 Task 자동 실행 완료")
            else:
                print(f"   ⏸️  자동 실행 가능한 Task 없음")

        except Exception as e:
            print(f"   ⚠️  실행 오류: {e}")

    print()

    # ========================================
    # Step 4: 워크플로우 현황 출력
    # ========================================
    print("=" * 60)
    print("📊 Step 4: 최종 워크플로우 현황")
    print("=" * 60)
    print()

    # 첫 번째 규제의 워크플로우 상태 출력 (예시)
    if regulations:
        first_regulation_id = regulations[0]['id']
        workflow_status = orchestrator.get_workflow_status(first_regulation_id)

        print_workflow_status(workflow_status)

    # ========================================
    # Step 5: 종합 대시보드
    # ========================================
    print("=" * 60)
    print("📈 Step 5: 종합 대시보드")
    print("=" * 60)
    print()

    # 전체 Task 집계
    all_tasks = []
    for reg_id in orchestrator.workflows:
        all_tasks.extend(orchestrator.workflows[reg_id])

    total_cost = sum(task.get('estimated_cost', 0) for task in all_tasks)
    total_time = sum(task.get('estimated_time_hours', 0) for task in all_tasks)

    automated_tasks = [
        task for task in all_tasks
        if task.get('task_type') in ['automated', 'semi_auto']
    ]
    manual_tasks = [
        task for task in all_tasks
        if task.get('task_type') == 'manual'
    ]

    # 자동화로 인한 절감
    cost_saved = sum(task.get('estimated_cost', 0) for task in automated_tasks) * 0.7
    time_saved = sum(task.get('estimated_time_hours', 0) for task in automated_tasks) * 0.8

    print(f"⏱️  시간 분석:")
    print(f"   총 예상 시간: {total_time}시간 ({total_time/8:.1f}일)")
    print(f"   자동화 절감 시간: {int(time_saved)}시간 ({time_saved/8:.1f}일)")
    print(f"   실제 소요 시간: {int(total_time - time_saved)}시간 ({(total_time-time_saved)/8:.1f}일)")
    print()

    print(f"🎯 효율성 분석:")
    print(f"   총 Task: {len(all_tasks)}개")
    print(f"   자동화 Task: {len(automated_tasks)}개 ({len(automated_tasks)/len(all_tasks)*100:.1f}%)")
    print(f"   수동 Task: {len(manual_tasks)}개 ({len(manual_tasks)/len(all_tasks)*100:.1f}%)")
    print(f"   담당자 업무 감소율: {time_saved/total_time*100:.1f}%")
    print()

    # ========================================
    # Step 6: JSON 저장
    # ========================================
    complete_output = {
        "business_info": result.get('business_info', {}),
        "summary": {
            "total_regulations": final_output.get('total_count', 0),
            "total_tasks": len(all_tasks),
            "automated_tasks": len(automated_tasks),
            "manual_tasks": len(manual_tasks),
            "total_time_hours": total_time,
            "time_saved_hours": int(time_saved),
            "automation_rate": len(automated_tasks)/len(all_tasks)*100 if all_tasks else 0
        },
        "regulations": regulations,
        "checklists": checklists,
        "workflow_tasks": all_tasks,
        "risk_assessment": result.get('risk_assessment', {})
    }

    output_file = "regulation_analysis_with_workflow.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_output, f, indent=2, ensure_ascii=False)

    print(f"💾 전체 결과가 '{output_file}' 파일로 저장되었습니다.")
    print()

    print("=" * 60)
    print("🎉 모든 작업이 완료되었습니다!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main_with_workflow())
