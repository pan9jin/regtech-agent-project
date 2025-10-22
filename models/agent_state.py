"""LangGraph Agent State 정의"""

from typing import List, Dict, Any
from typing_extensions import TypedDict

from .business_info import BusinessInfo
from .regulation import Regulation
from .checklist import ChecklistItem
from .risk_assessment import RiskAssessment


class AgentState(TypedDict, total=False):
    """LangGraph State - Agent 간 데이터 전달"""
    # 기존 필드
    business_info: BusinessInfo
    keywords: List[str]
    search_results: List[Dict[str, Any]]
    regulations: List[Regulation]
    final_output: Dict[str, Any]

    # 추가 필드 (2개 새로운 Agent)
    checklists: List[ChecklistItem]     # 체크리스트 목록
    risk_assessment: RiskAssessment     # 리스크 평가 결과
