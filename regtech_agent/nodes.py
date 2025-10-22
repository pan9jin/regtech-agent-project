"""
LangGraph 노드 함수들
각 Agent를 LangGraph 노드로 래핑합니다.
"""

from typing import Dict, Any

from .models import AgentState, BusinessInfo, FinalReport
from .agents import (
    analyze_business,
    search_regulations,
    classify_regulations,
    prioritize_regulations,
    generate_checklists,
    plan_execution,
    assess_risks,
    generate_final_report,
    send_final_report_email,
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
    return {"regulations": result["regulations"]}


def checklist_generator_node(state: AgentState) -> Dict[str, Any]:
    """체크리스트 노드: 규제별 체크리스트를 생성합니다."""
    result = generate_checklists.invoke({"regulations": state["regulations"]})
    return {"checklists": result["checklists"]}


def planning_agent_node(state: AgentState) -> Dict[str, Any]:
    """계획 노드: 실행 계획을 수립합니다."""
    result = plan_execution.invoke({
        "regulations": state["regulations"],
        "checklists": state["checklists"]
    })
    return {"execution_plans": result["execution_plans"]}


def risk_assessor_node(state: AgentState) -> Dict[str, Any]:
    """리스크 노드: 리스크를 평가합니다."""
    result = assess_risks.invoke({
        "regulations": state["regulations"],
        "business_info": state["business_info"]
    })
    return {"risk_assessment": result["risk_assessment"]}


def report_generator_node(state: AgentState) -> Dict[str, Any]:
    """보고서 노드: 최종 보고서를 생성합니다."""
    result = generate_final_report.invoke({
        "business_info": state["business_info"],
        "regulations": state["regulations"],
        "checklists": state["checklists"],
        "execution_plans": state["execution_plans"],
        "risk_assessment": state["risk_assessment"]
    })
    return {"final_report": result["final_report"]}


def email_notifier_node(state: AgentState) -> Dict[str, Any]:
    """이메일 노드: 최종 보고서를 지정된 이메일로 발송합니다."""
    existing_status = state.get("email_status") or {}
    if existing_status.get("attempted"):
        return {}

    final_report: FinalReport = state.get("final_report", {})
    business_info: BusinessInfo = state.get("business_info", {})

    result = send_final_report_email.invoke({
        "final_report": final_report,
        "business_info": business_info,
        "checklists": state.get("checklists", []),
        "execution_plans": state.get("execution_plans", []),
        "recipient_email": state.get("email_recipient"),
    })
    return {"email_status": result["email_status"]}
