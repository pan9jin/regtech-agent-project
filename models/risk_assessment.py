"""리스크 평가 관련 데이터 모델"""

from typing import List, Dict, Any
from typing_extensions import TypedDict


class RiskItem(TypedDict):
    """리스크 항목 데이터 구조"""
    regulation_id: str          # 규제 ID
    regulation_name: str        # 규제명
    penalty_amount: str         # 벌금액
    penalty_type: str           # 벌칙 유형 (벌금/징역/과태료)
    business_impact: str        # 사업 영향 (영업정지/인허가 취소 등)
    risk_score: float           # 리스크 점수 (0-10)
    past_cases: List[str]       # 과거 처벌 사례
    mitigation: str             # 리스크 완화 방안


class RiskAssessment(TypedDict):
    """리스크 평가 결과 데이터 구조"""
    total_risk_score: float             # 전체 리스크 점수 (0-10)
    high_risk_items: List[RiskItem]     # 고위험 항목 (점수 7.0 이상)
    risk_matrix: Dict[str, Any]         # 리스크 매트릭스
    recommendations: List[str]          # 권장 사항
