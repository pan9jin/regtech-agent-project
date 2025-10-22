"""LangGraph 워크플로우 빌더"""

from langgraph.graph import StateGraph, START, END

from models import AgentState
from .graph_nodes import (
    analyzer_node,
    search_node,
    classifier_node,
    prioritizer_node,
    checklist_generator_node,
    planning_node,
    risk_assessor_node,
)


def build_workflow() -> StateGraph:
    """LangGraph 워크플로우를 구성합니다.

    실행 순서:
    1. analyzer: 사업 정보 분석 및 키워드 추출
    2. searcher: Tavily로 규제 검색
    3. classifier: 규제 분류
    4. prioritizer: 우선순위 결정
    5. checklist_generator: 규제별 체크리스트 생성
    6. planner: 체크리스트별 실행 계획 수립
    7. risk_assessor: 리스크 평가

    Returns:
        구성된 StateGraph 객체
    """
    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("searcher", search_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("prioritizer", prioritizer_node)
    graph.add_node("checklist_generator", checklist_generator_node)
    graph.add_node("planner", planning_node)
    graph.add_node("risk_assessor", risk_assessor_node)

    # 엣지 추가: 순차 실행
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "searcher")
    graph.add_edge("searcher", "classifier")
    graph.add_edge("classifier", "prioritizer")
    graph.add_edge("prioritizer", "checklist_generator")
    graph.add_edge("checklist_generator", "planner")
    graph.add_edge("planner", "risk_assessor")
    graph.add_edge("risk_assessor", END)

    return graph
