"""
LangGraph Workflow 빌드 및 실행
"""

from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .models import AgentState, BusinessInfo
from .nodes import (
    analyzer_node,
    search_node,
    classifier_node,
    prioritizer_node,
    checklist_generator_node,
    planning_agent_node,
    risk_assessor_node,
    report_generator_node,
    email_notifier_node,
)


def build_workflow() -> StateGraph:
    """LangGraph 워크플로우를 구성합니다 (병렬 처리 최적화).

    실행 순서:
    1. analyzer: 사업 정보 분석 및 키워드 추출
    2. searcher: Tavily로 규제 검색
    3. classifier: 규제 분류
    4. prioritizer: 우선순위 결정
    5-6. [병렬 실행]
         - checklist_generator: 규제별 체크리스트 생성
         - risk_assessor: 리스크 평가
    7. planning_agent: 실행 계획 수립 (checklist_generator 완료 후)
    8. report_generator: 최종 보고서 생성 (planning_agent + risk_assessor 완료 후)
    9. email_notifier: 보고서를 이메일로 발송

    병렬화 이점: Risk Assessment Agent가 Checklist Generator/Planning Agent와
                동시 실행되어 전체 소요 시간 약 30초~1분 단축
    """
    graph = StateGraph(AgentState)

    # Agent 노드 추가
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("searcher", search_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("prioritizer", prioritizer_node)
    graph.add_node("checklist_generator", checklist_generator_node)
    graph.add_node("risk_assessor", risk_assessor_node)
    graph.add_node("planning_agent", planning_agent_node)
    graph.add_node("report_generator", report_generator_node)
    graph.add_node("email_notifier", email_notifier_node)

    # 엣지 추가: 순차 실행 (Prioritizer까지)
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "searcher")
    graph.add_edge("searcher", "classifier")
    graph.add_edge("classifier", "prioritizer")

    # 병렬 실행: Prioritizer 이후 Checklist Generator와 Risk Assessor 동시 시작
    graph.add_edge("prioritizer", "checklist_generator")
    graph.add_edge("prioritizer", "risk_assessor")

    # Checklist Generator → Planning Agent (순차)
    graph.add_edge("checklist_generator", "planning_agent")

    # Report Generator는 Planning Agent와 Risk Assessor 모두 완료 후 실행
    graph.add_edge("planning_agent", "report_generator")
    graph.add_edge("risk_assessor", "report_generator")

    graph.add_edge("report_generator", "email_notifier")
    graph.add_edge("email_notifier", END)

    return graph


def run_regulation_agent(
    business_info: BusinessInfo,
    email_recipient: Optional[str] = None,
) -> AgentState:
    """규제 AI Agent를 실행합니다.

    Args:
        business_info: 사업 정보

    Returns:
        최종 상태 객체 (분석 결과 포함)
    """
    workflow = build_workflow()
    app = workflow.compile(checkpointer=MemorySaver())

    initial_recipient = (email_recipient or "").strip()

    initial_state: AgentState = {
        "business_info": business_info,
        "keywords": [],
        "search_results": [],
        "regulations": [],
        "final_output": {},
        # Agent 결과 필드 초기화
        "checklists": [],
        "execution_plans": [],
        "risk_assessment": {
            "total_risk_score": 0.0,
            "high_risk_items": [],
            "risk_matrix": {},
            "recommendations": []
        },
        "final_report": {
            "executive_summary": "",
            "key_insights": [],
            "action_items": [],
            "risk_highlights": [],
            "next_steps": [],
            "full_markdown": "",
            "report_pdf_path": "",
            "citations": []
        },
        "email_status": {
            "success": False,
            "recipient": initial_recipient,
            "error": "이메일 발송 전",
            "attachments": [],
            "attempted": False,
        },
        "email_recipient": email_recipient,
    }

    print("🚀 [RegTech Agent] Workflow 시작...\n")
    print("=" * 80)
    print()

    config = {"configurable": {"thread_id": "regulation_agent_v3"}}
    final_state = app.invoke(initial_state, config=config)

    print()
    print("=" * 80)
    print("✅ [RegTech Agent] Workflow 완료!\n")

    return final_state
