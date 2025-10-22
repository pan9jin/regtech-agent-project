"""
RegTech Agent 데이터 모델 정의
"""

from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from enum import Enum


class Priority(str, Enum):
    """우선순위 Enum"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(str, Enum):
    """규제 카테고리 Enum"""
    SAFETY_ENV = "안전/환경"
    PRODUCT_CERT = "제품 인증"
    FACTORY_OPS = "공장 운영"


class BusinessInfo(TypedDict, total=False):
    """사업 정보 데이터 구조"""
    industry: str
    product_name: str
    raw_materials: str
    processes: List[str]
    employee_count: int
    sales_channels: List[str]
    export_countries: List[str]


class EvidenceItem(TypedDict, total=False):
    """LLM 답변에 포함되는 근거/출처 정보"""
    source_id: str                   # 검색 결과 식별자 (예: SRC-001)
    title: str                       # 문서 제목
    url: str                         # 문서 URL
    snippet: str                     # 발췌 내용 (원본, 생략 가능)
    justification: str               # LLM이 생성한 concise 요약 (우선 사용)


class Regulation(TypedDict):
    """규제 정보 데이터 구조"""
    id: str
    name: str
    category: str
    why_applicable: str
    authority: str
    priority: str
    key_requirements: List[str]
    reference_url: Optional[str]
    sources: List[EvidenceItem]


class ChecklistItem(TypedDict):
    """체크리스트 항목 데이터 구조"""
    regulation_id: str          # 연결된 규제 ID
    regulation_name: str        # 규제명
    task_name: str              # 작업명
    responsible_dept: str       # 담당 부서
    deadline: str               # 마감 기한 (YYYY-MM-DD 형식)
    method: List[str]           # 실행 방법 (단계별)
    estimated_time: str         # 소요 시간
    priority: str               # 우선순위 (상위 규제와 동일)
    status: str                 # 상태 (pending/in_progress/completed)
    evidence: List[EvidenceItem]


class Milestone(TypedDict):
    """마일스톤 데이터 구조"""
    name: str                           # 마일스톤명
    deadline: str                       # 마감일 (예: "1개월 내")
    tasks: List[str]                    # 포함된 작업 ID들
    completion_criteria: str            # 완료 기준


class ExecutionPlan(TypedDict):
    """실행 계획 데이터 구조"""
    plan_id: str                        # 계획 ID
    regulation_id: str                  # 연결된 규제 ID
    regulation_name: str                # 규제명
    checklist_items: List[str]          # 연결된 체크리스트 항목 ID들
    timeline: str                       # 예상 소요 기간 (예: "3개월")
    start_date: str                     # 시작 시점 (예: "즉시", "공장등록 후")
    milestones: List[Milestone]         # 마일스톤 목록
    dependencies: Dict[str, List[str]]  # 선행 작업 의존성 (작업ID: [선행작업ID들])
    parallel_tasks: List[List[str]]     # 병렬 처리 가능한 작업 그룹
    critical_path: List[str]            # 크리티컬 패스 (가장 긴 경로)
    evidence: List[EvidenceItem]


class FinalReport(TypedDict):
    """최종 보고서 데이터 구조"""
    executive_summary: str              # 경영진용 요약 (마크다운)
    key_insights: List[str]             # 핵심 인사이트 (3-5개)
    action_items: List[Dict[str, Any]]  # 즉시 조치 항목
    risk_highlights: List[str]          # 주요 리스크 하이라이트
    next_steps: List[str]               # 다음 단계 권장사항
    full_markdown: str                  # 통합 마크다운 보고서 (전체)
    report_pdf_path: str                # PDF 저장 경로
    citations: List[EvidenceItem]       # 전체 보고서에 포함된 주요 출처


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
    evidence: List[EvidenceItem]


class RiskAssessment(TypedDict):
    """리스크 평가 결과 데이터 구조"""
    total_risk_score: float             # 전체 리스크 점수 (0-10)
    high_risk_items: List[RiskItem]     # 고위험 항목 (점수 7.0 이상)
    risk_matrix: Dict[str, Any]         # 리스크 매트릭스
    recommendations: List[str]          # 권장 사항


class AgentState(TypedDict, total=False):
    """LangGraph State - Agent 간 데이터 전달"""
    # 기존 필드
    business_info: BusinessInfo
    keywords: List[str]
    search_results: List[Dict[str, Any]]
    regulations: List[Regulation]
    final_output: Dict[str, Any]

    # Agent 결과 필드
    checklists: List[ChecklistItem]     # 체크리스트 목록
    execution_plans: List[ExecutionPlan]  # 실행 계획 (Planning Agent)
    risk_assessment: RiskAssessment     # 리스크 평가 결과
    final_report: FinalReport           # 최종 보고서 (Report Generation Agent)
    email_status: Dict[str, Any]        # 이메일 전송 결과
    email_recipient: Optional[str]      # 보고서 수신 이메일
