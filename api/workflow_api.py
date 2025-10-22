"""워크플로우 API 엔드포인트"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from pydantic import BaseModel

from workflows.orchestrator import WorkflowOrchestrator
from models.workflow_task import WorkflowTask, WorkflowStatus
from models.regulation import Regulation
from models.checklist import ChecklistItem

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# 전역 Orchestrator 인스턴스
orchestrator = WorkflowOrchestrator()


class CreateWorkflowRequest(BaseModel):
    """워크플로우 생성 요청"""
    regulation: Regulation
    checklists: List[ChecklistItem]


class ExecuteWorkflowRequest(BaseModel):
    """워크플로우 실행 요청"""
    regulation_id: str
    auto_execute: bool = True


@router.post("/create", response_model=Dict[str, Any])
async def create_workflow(request: CreateWorkflowRequest):
    """
    체크리스트로부터 워크플로우 생성

    Args:
        request: 규제 정보 및 체크리스트

    Returns:
        생성된 워크플로우 Task 목록
    """
    try:
        tasks = orchestrator.create_workflow_from_checklists(
            regulation=request.regulation,
            checklists=request.checklists
        )

        return {
            "success": True,
            "regulation_id": request.regulation['id'],
            "regulation_name": request.regulation['name'],
            "total_tasks": len(tasks),
            "automated_tasks": sum(
                1 for task in tasks
                if task['task_type'] in ['automated', 'semi_auto']
            ),
            "tasks": tasks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=Dict[str, Any])
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    워크플로우 실행 (자동화 가능한 Task들)

    Args:
        request: 실행 요청 정보
        background_tasks: FastAPI 백그라운드 태스크

    Returns:
        실행 상태
    """
    try:
        if request.auto_execute:
            # 백그라운드에서 실행
            background_tasks.add_task(
                orchestrator.execute_automated_tasks,
                request.regulation_id
            )

            return {
                "success": True,
                "status": "started",
                "regulation_id": request.regulation_id,
                "message": "자동화 Task들이 백그라운드에서 실행 중입니다."
            }
        else:
            # 즉시 실행
            result = await orchestrator.execute_automated_tasks(
                request.regulation_id
            )

            return {
                "success": True,
                "status": "completed",
                **result
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{regulation_id}", response_model=WorkflowStatus)
async def get_workflow_status(regulation_id: str):
    """
    워크플로우 상태 조회

    Args:
        regulation_id: 규제 ID

    Returns:
        워크플로우 전체 상태
    """
    try:
        status = orchestrator.get_workflow_status(regulation_id)
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{regulation_id}", response_model=List[WorkflowTask])
async def get_tasks(regulation_id: str):
    """
    특정 규제의 모든 Task 조회

    Args:
        regulation_id: 규제 ID

    Returns:
        Task 목록
    """
    tasks = orchestrator.workflows.get(regulation_id, [])

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail=f"규제 ID '{regulation_id}'에 대한 워크플로우를 찾을 수 없습니다."
        )

    return tasks


@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, approved: bool, comment: str = ""):
    """
    Task 승인/거부

    Args:
        task_id: Task ID
        approved: 승인 여부
        comment: 승인/거부 사유

    Returns:
        승인 결과
    """
    # TODO: 실제 승인 로직 구현
    return {
        "success": True,
        "task_id": task_id,
        "approved": approved,
        "comment": comment,
        "approved_at": "2025-10-21T14:00:00"
    }


@router.get("/dashboard/overview")
async def get_dashboard_overview(company_id: str = "default"):
    """
    대시보드 전체 현황

    Args:
        company_id: 회사 ID

    Returns:
        전체 워크플로우 현황
    """
    # 모든 워크플로우 집계
    all_tasks = []
    for tasks in orchestrator.workflows.values():
        all_tasks.extend(tasks)

    if not all_tasks:
        return {
            "total_regulations": 0,
            "total_tasks": 0,
            "completed": 0,
            "in_progress": 0,
            "waiting_approval": 0,
            "pending": 0,
            "automation_rate": 0.0,
            "estimated_completion": None,
            "cost_saved": 0
        }

    # 상태별 집계
    completed = sum(1 for task in all_tasks if task.get('status') == 'completed')
    in_progress = sum(1 for task in all_tasks if task.get('status') == 'in_progress')
    waiting_approval = sum(1 for task in all_tasks if task.get('status') == 'waiting_approval')
    pending = sum(1 for task in all_tasks if task.get('status') == 'pending')

    # 자동화 비율
    automated = sum(
        1 for task in all_tasks
        if task.get('task_type') in ['automated', 'semi_auto']
    )
    automation_rate = (automated / len(all_tasks) * 100) if all_tasks else 0

    # 비용 절감액 계산 (자동화로 인한 절감)
    cost_saved = sum(
        task.get('estimated_cost', 0) * 0.7  # 70% 절감 가정
        for task in all_tasks
        if task.get('task_type') == 'automated'
    )

    return {
        "total_regulations": len(orchestrator.workflows),
        "total_tasks": len(all_tasks),
        "completed": completed,
        "in_progress": in_progress,
        "waiting_approval": waiting_approval,
        "pending": pending,
        "automation_rate": round(automation_rate, 1),
        "estimated_completion": "2025-11-15",  # TODO: 실제 계산
        "cost_saved": int(cost_saved)
    }
