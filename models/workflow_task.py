"""워크플로우 Task 모델"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from enum import Enum
from datetime import datetime


class TaskType(str, Enum):
    """Task 유형"""
    AUTOMATED = "automated"      # 완전 자동화 가능
    SEMI_AUTO = "semi_auto"      # 사람 승인 후 자동 실행
    MANUAL = "manual"            # 사람이 직접 수행
    MONITORING = "monitoring"    # 자동 모니터링 + 알림


class TaskStatus(str, Enum):
    """Task 상태"""
    PENDING = "pending"                    # 대기 중
    IN_PROGRESS = "in_progress"            # 진행 중
    WAITING_APPROVAL = "waiting_approval"  # 승인 대기
    COMPLETED = "completed"                # 완료
    FAILED = "failed"                      # 실패
    SKIPPED = "skipped"                    # 건너뜀


class WorkflowTask(TypedDict, total=False):
    """워크플로우 Task 데이터 구조"""
    # Task ID
    id: str
    regulation_id: str
    regulation_name: str

    # Task 기본 정보
    task_name: str
    task_type: str  # TaskType
    priority: str   # Priority

    # 실행 정보
    responsible_dept: str
    responsible_person: Optional[str]
    deadline: str  # ISO format

    # 자동화 설정
    automation_config: Dict[str, Any]  # 자동화 실행 설정
    prerequisites: List[str]           # 선행 Task ID들

    # 상태 관리
    status: str    # TaskStatus
    progress: float  # 진행률 (0-100)

    # 실행 결과
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]

    # 메타데이터
    created_at: str  # ISO format
    started_at: Optional[str]
    completed_at: Optional[str]

    # 비용/시간
    estimated_cost: int
    estimated_time_hours: int
    actual_cost: Optional[int]
    actual_time_hours: Optional[int]


class WorkflowStatus(TypedDict):
    """워크플로우 전체 상태"""
    regulation_id: str
    total_tasks: int
    completed: int
    in_progress: int
    waiting_approval: int
    pending: int
    failed: int
    automation_rate: float  # 자동화 가능 비율
    estimated_completion_date: Optional[str]
    tasks: List[WorkflowTask]
