"""워크플로우 오케스트레이터 - Task 실행 엔진"""

from typing import List, Dict, Any
from datetime import datetime
import asyncio

from models.workflow_task import WorkflowTask, TaskType, TaskStatus, WorkflowStatus
from models.regulation import Regulation
from models.checklist import ChecklistItem


class WorkflowOrchestrator:
    """워크플로우 실행 및 관리 엔진"""

    def __init__(self):
        self.tasks: Dict[str, WorkflowTask] = {}
        self.workflows: Dict[str, List[WorkflowTask]] = {}

    def create_workflow_from_checklists(
        self,
        regulation: Regulation,
        checklists: List[ChecklistItem]
    ) -> List[WorkflowTask]:
        """체크리스트를 워크플로우 Task로 변환"""
        workflow_tasks = []

        for idx, checklist in enumerate(checklists):
            # Task 유형 자동 분류
            task_type = self._classify_task_type(checklist)

            # 자동화 설정 생성
            automation_config = self._create_automation_config(
                checklist,
                task_type
            )

            task = WorkflowTask(
                id=f"TASK-{regulation['id']}-{idx+1:03d}",
                regulation_id=regulation['id'],
                regulation_name=regulation['name'],
                task_name=checklist['task_name'],
                task_type=task_type,
                priority=checklist['priority'],
                responsible_dept=checklist['responsible_dept'],
                responsible_person=None,
                deadline=checklist['deadline'],
                automation_config=automation_config,
                prerequisites=[],
                status=TaskStatus.PENDING,
                progress=0.0,
                result=None,
                error_message=None,
                created_at=datetime.now().isoformat(),
                started_at=None,
                completed_at=None,
                estimated_cost=self._parse_cost(checklist['estimated_cost']),
                estimated_time_hours=self._parse_time(checklist['estimated_time']),
                actual_cost=None,
                actual_time_hours=None
            )

            workflow_tasks.append(task)

        # 워크플로우 저장
        self.workflows[regulation['id']] = workflow_tasks

        return workflow_tasks

    def _classify_task_type(self, checklist: ChecklistItem) -> str:
        """체크리스트 항목을 Task 유형으로 분류"""
        task_name = checklist['task_name'].lower()
        method = ' '.join(checklist.get('method', [])).lower()

        # 키워드 기반 분류
        if any(keyword in task_name or keyword in method for keyword in [
            '신청서 작성', '서류 작성', '문서 생성', '양식 작성'
        ]):
            return TaskType.AUTOMATED

        elif any(keyword in task_name or keyword in method for keyword in [
            '제출', '신청', '온라인', '포털'
        ]):
            return TaskType.SEMI_AUTO

        elif any(keyword in task_name or keyword in method for keyword in [
            '교육', '점검', '방문', '현장', '대면'
        ]):
            return TaskType.MANUAL

        elif any(keyword in task_name or keyword in method for keyword in [
            '모니터링', '추적', '확인', '정기'
        ]):
            return TaskType.MONITORING

        # 기본값
        return TaskType.MANUAL

    def _create_automation_config(
        self,
        checklist: ChecklistItem,
        task_type: str
    ) -> Dict[str, Any]:
        """Task 유형에 따른 자동화 설정 생성"""

        if task_type == TaskType.AUTOMATED:
            return {
                "type": "document_generation",
                "template_id": f"template_{checklist['regulation_id']}",
                "auto_fill_fields": True,
                "generate_pdf": True
            }

        elif task_type == TaskType.SEMI_AUTO:
            return {
                "type": "approval_workflow",
                "steps": [
                    {"step": 1, "action": "prepare_documents", "auto": True},
                    {"step": 2, "action": "request_approval", "approver": "legal_team"},
                    {"step": 3, "action": "submit", "auto": True, "after_approval": True}
                ],
                "approval_timeout_hours": 48
            }

        elif task_type == TaskType.MANUAL:
            return {
                "type": "manual_task",
                "guidance": {
                    "steps": checklist.get('method', []),
                    "estimated_time": checklist['estimated_time'],
                    "estimated_cost": checklist['estimated_cost']
                },
                "evidence_required": ["completion_photo", "certificate"],
                "completion_check": "manager_approval"
            }

        elif task_type == TaskType.MONITORING:
            return {
                "type": "continuous_monitoring",
                "check_frequency": "weekly",
                "alerts": {
                    "deadline_near": {"notify": "7_days_before"},
                    "status_change": {"notify": "immediately"}
                }
            }

        return {}

    def _parse_cost(self, cost_str: str) -> int:
        """비용 문자열을 숫자로 변환"""
        import re

        # "약 30만원" -> 300000
        match_man = re.search(r'(\d+(?:,\d+)?)\s*만원', cost_str)
        if match_man:
            return int(match_man.group(1).replace(',', '')) * 10000

        # "100원" -> 100
        match_won = re.search(r'(\d+(?:,\d+)?)\s*원', cost_str)
        if match_won:
            return int(match_won.group(1).replace(',', ''))

        # "무료" -> 0
        if '무료' in cost_str or '0' in cost_str:
            return 0

        return 0

    def _parse_time(self, time_str: str) -> int:
        """시간 문자열을 시간 단위로 변환"""
        import re

        # "20일" -> 160시간
        match_days = re.search(r'(\d+)\s*일', time_str)
        if match_days:
            return int(match_days.group(1)) * 8  # 1일 = 8시간

        # "1개월" -> 160시간
        match_months = re.search(r'(\d+)\s*개월', time_str)
        if match_months:
            return int(match_months.group(1)) * 160  # 1개월 = 20일

        # "3시간" -> 3
        match_hours = re.search(r'(\d+)\s*시간', time_str)
        if match_hours:
            return int(match_hours.group(1))

        return 8  # 기본값 1일

    def get_workflow_status(self, regulation_id: str) -> WorkflowStatus:
        """워크플로우 상태 조회"""
        tasks = self.workflows.get(regulation_id, [])

        if not tasks:
            return WorkflowStatus(
                regulation_id=regulation_id,
                total_tasks=0,
                completed=0,
                in_progress=0,
                waiting_approval=0,
                pending=0,
                failed=0,
                automation_rate=0.0,
                estimated_completion_date=None,
                tasks=[]
            )

        # 상태별 카운트
        status_counts = {
            TaskStatus.COMPLETED: 0,
            TaskStatus.IN_PROGRESS: 0,
            TaskStatus.WAITING_APPROVAL: 0,
            TaskStatus.PENDING: 0,
            TaskStatus.FAILED: 0
        }

        for task in tasks:
            status = task.get('status', TaskStatus.PENDING)
            status_counts[status] = status_counts.get(status, 0) + 1

        # 자동화 비율 계산
        automated_tasks = sum(
            1 for task in tasks
            if task['task_type'] in [TaskType.AUTOMATED, TaskType.SEMI_AUTO]
        )
        automation_rate = (automated_tasks / len(tasks) * 100) if tasks else 0

        return WorkflowStatus(
            regulation_id=regulation_id,
            total_tasks=len(tasks),
            completed=status_counts[TaskStatus.COMPLETED],
            in_progress=status_counts[TaskStatus.IN_PROGRESS],
            waiting_approval=status_counts[TaskStatus.WAITING_APPROVAL],
            pending=status_counts[TaskStatus.PENDING],
            failed=status_counts[TaskStatus.FAILED],
            automation_rate=round(automation_rate, 1),
            estimated_completion_date=None,  # TODO: 계산 로직 추가
            tasks=tasks
        )

    async def execute_automated_tasks(self, regulation_id: str) -> Dict[str, Any]:
        """자동화 가능한 Task들을 실행"""
        tasks = self.workflows.get(regulation_id, [])
        automated_tasks = [
            task for task in tasks
            if task['task_type'] == TaskType.AUTOMATED
            and task['status'] == TaskStatus.PENDING
        ]

        results = []
        for task in automated_tasks:
            # 자동 실행 시뮬레이션
            task['status'] = TaskStatus.IN_PROGRESS
            task['started_at'] = datetime.now().isoformat()

            # TODO: 실제 자동화 로직 구현
            await asyncio.sleep(0.1)  # 시뮬레이션

            task['status'] = TaskStatus.COMPLETED
            task['completed_at'] = datetime.now().isoformat()
            task['progress'] = 100.0

            results.append({
                "task_id": task['id'],
                "task_name": task['task_name'],
                "status": "completed"
            })

        return {
            "regulation_id": regulation_id,
            "executed_tasks": len(results),
            "results": results
        }
