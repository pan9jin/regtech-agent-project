"""LangGraph 노드 정의 - 각 Tool을 호출하고 상태를 업데이트"""

from typing import Dict, Any

from models import AgentState
from agents import (
    analyze_business,
    search_regulations,
    classify_regulations,
    prioritize_regulations,
    generate_checklists,
    create_action_plan,
    assess_risks,
)


def analyzer_node(state: AgentState) -> Dict[str, Any]:
    """분석 노드: 사업 정보를 분석하여 키워드를 추출합니다."""
    result = analyze_business.invoke({"business_info": state["business_info"]})
    return {"keywords": result["keywords"]}


def search_node(state: AgentState) -> Dict[str, Any]:
    """검색 노드: 키워드를 사용하여 규제 정보를 검색합니다."""
    result = search_regulations.invoke({"keywords": state["keywords"]})
    return {"search_results": result["search_results"]}


def classifier_node(state: AgentState) -> Dict[str, Any]:
    """분류 노드: 검색 결과를 분석하여 규제를 분류합니다."""
    result = classify_regulations.invoke({
        "business_info": state["business_info"],
        "search_results": state["search_results"]
    })
    return {"regulations": result["regulations"]}


def prioritizer_node(state: AgentState) -> Dict[str, Any]:
    """우선순위 노드: 규제의 우선순위를 결정합니다."""
    result = prioritize_regulations.invoke({
        "business_info": state["business_info"],
        "regulations": state["regulations"]
    })
    return {
        "regulations": result["regulations"],
        "final_output": result["final_output"]
    }


def checklist_generator_node(state: AgentState) -> Dict[str, Any]:
    """체크리스트 생성 노드: 규제별 실행 체크리스트를 생성합니다."""
    result = generate_checklists.invoke({"regulations": state["regulations"]})
    return {"checklists": result["checklists"]}


def planning_node(state: AgentState) -> Dict[str, Any]:
    """계획 노드: 각 체크리스트 항목에 대한 실행 계획을 수립합니다."""
    updated_checklists = []
    for item in state["checklists"]:
        result = create_action_plan.invoke({"checklist_item": item})
        item["action_plan"] = result["action_plan"]
        updated_checklists.append(item)
    return {"checklists": updated_checklists}


def risk_assessor_node(state: AgentState) -> Dict[str, Any]:
    """리스크 평가 노드: 미준수 시 리스크를 평가합니다."""
    result = assess_risks.invoke({
        "regulations": state["regulations"],
        "business_info": state["business_info"]
    })
    return {"risk_assessment": result["risk_assessment"]}
