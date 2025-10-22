"""Report Generation Agent - 최종 보고서 작성 및 PDF 생성"""

from typing import Dict, Any
import json
from langchain.tools import tool


@tool
def generate_report(
    agent_state: Dict[str, Any],
    output_json: str = "regulation_analysis_result.json",
    output_pdf: str = "regulation_report.pdf"
) -> Dict[str, Any]:
    """최종 보고서를 생성합니다 (JSON + PDF).

    Args:
        agent_state: 전체 Agent State (모든 분석 결과 포함)
        output_json: JSON 출력 파일 경로
        output_pdf: PDF 출력 파일 경로

    Returns:
        최종 보고서 데이터 및 파일 경로
    """
    print("📄 [Report Generation Agent] 최종 보고서 생성 중...")

    # 모든 데이터를 통합하여 보고서 구조 생성
    final_output = agent_state.get('final_output', {})

    report_data = {
        "business_info": agent_state.get('business_info', {}),
        "summary": {
            "total_regulations": final_output.get('total_count', 0),
            "priority_distribution": final_output.get('priority_distribution', {}),
            "total_checklist_items": len(agent_state.get('checklists', [])),
            "total_cost": agent_state.get('cost_analysis', {}).get('total_cost_formatted', '0원'),
            "risk_score": agent_state.get('risk_assessment', {}).get('total_risk_score', 0.0)
        },
        "regulations": agent_state.get('regulations', []),
        "checklists": agent_state.get('checklists', []),
        "cost_analysis": agent_state.get('cost_analysis', {}),
        "risk_assessment": agent_state.get('risk_assessment', {})
    }

    # JSON 파일 저장
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"   ✓ JSON 보고서 저장: {output_json}")
    except Exception as e:
        print(f"   ⚠️  JSON 저장 실패: {e}")

    # PDF 파일 생성
    pdf_path = None
    try:
        from utils.pdf_generator import generate_pdf_report
        pdf_path = generate_pdf_report(report_data, output_pdf)
        print(f"   ✓ PDF 보고서 생성: {pdf_path}")
    except ImportError:
        print(f"   ⚠️  PDF 생성 라이브러리 없음 (reportlab 설치 필요)")
        print(f"      pip install reportlab")
    except Exception as e:
        print(f"   ⚠️  PDF 생성 실패: {e}")

    print(f"   ✓ 보고서 생성 완료\n")

    return {
        "report": report_data,
        "json_path": output_json,
        "pdf_path": pdf_path
    }
