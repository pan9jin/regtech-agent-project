"""체크리스트 관련 데이터 모델"""

from typing import List, Optional
from typing_extensions import TypedDict, NotRequired


class ChecklistItem(TypedDict):
    """체크리스트 항목 데이터 구조"""
    regulation_id: str          # 연결된 규제 ID
    regulation_name: str        # 규제명
    task_name: str              # 작업명
    responsible_dept: str       # 담당 부서
    deadline: str               # 마감 기한
    method: List[str]           # 실행 방법 (단계별)
    action_plan: NotRequired[List[str]] # 구체적인 실행 계획
    estimated_time: str         # 소요 시간
    priority: str               # 우선순위 (상위 규제와 동일)
    status: str                 # 상태 (pending/in_progress/completed)
