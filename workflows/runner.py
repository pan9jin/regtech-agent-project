"""워크플로우 실행 함수"""

from langgraph.checkpoint.memory import MemorySaver

from models import AgentState, BusinessInfo
from .graph_builder import build_workflow


def run_regulation_agent(business_info: BusinessInfo) -> AgentState:
    """규제 AI Agent를 실행합니다.

    Args:
        business_info: 사업 정보

    Returns:
        최종 상태 객체 (분석 결과 포함)
    """
    # 워크플로우 빌드 및 컴파일
    workflow = build_workflow()
    app = workflow.compile(checkpointer=MemorySaver())

    # 초기 상태 설정
    initial_state: AgentState = {
        "business_info": business_info,
        "keywords": [],
        "search_results": [],
        "regulations": [],
        "final_output": {},
        # 새로운 필드 초기화
        "checklists": [],
        "cost_analysis": {
            "total_cost": 0,
            "total_cost_formatted": "0원",
            "breakdown": {"by_priority": {}, "by_category": {}, "by_timeline": {}},
            "subsidies": [],
            "payment_plan": []
        },
        "risk_assessment": {
            "total_risk_score": 0.0,
            "high_risk_items": [],
            "risk_matrix": {},
            "recommendations": []
        }
    }

    # 워크플로우 실행
    config = {"configurable": {"thread_id": "regulation_agent_v3"}}
    return app.invoke(initial_state, config=config)
