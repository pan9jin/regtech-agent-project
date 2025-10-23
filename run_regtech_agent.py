"""
RegTech Agent 메인 실행 파일 (리팩토링 버전)
"""

import json
import sys
from dotenv import load_dotenv

from regtech_agent import BusinessInfo, run_regulation_agent

# 환경 변수 로드
load_dotenv()


def main():
    """메인 실행 함수"""

    print("=" * 80)
    print("RegTech Assistant - 규제 준수 분석 AI Agent")
    print("=" * 80)
    print()

    # 샘플 사업 정보
    sample_business_info: BusinessInfo = {
        "industry": "배터리 제조",
        "product_name": "리튬이온 배터리",
        "raw_materials": "리튬, 코발트, 니켈, 흑연",
        "processes": ["원자재 혼합", "전극 제조", "셀 조립", "충방전 테스트"],
        "employee_count": 50,
        "sales_channels": ["B2B", "온라인"],
        "export_countries": ["미국", "일본"]
    }
    recipient_email = sys.argv[1] if len(sys.argv) > 1 else None

    # Workflow 실행
    final_state = run_regulation_agent(
        business_info=sample_business_info,
        email_recipient=recipient_email,
    )

    # 결과 저장
    output_file = "regulation_analysis_result.json"

    # AgentState를 JSON serializable하게 변환
    output_data = {
        "business_info": final_state.get("business_info", {}),
        "keywords": final_state.get("keywords", []),
        "regulations": final_state.get("regulations", []),
        "checklists": final_state.get("checklists", []),
        "execution_plans": final_state.get("execution_plans", []),
        "risk_assessment": final_state.get("risk_assessment", {}),
        "final_report": final_state.get("final_report", {}),
        "email_status": final_state.get("email_status", {}),
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"📊 분석 결과 저장: {output_file}")

    # 보고서 정보 출력
    if "final_report" in final_state:
        report = final_state["final_report"]
        print(f"\n📄 보고서 파일:")
        print(f"   - PDF: {report.get('report_pdf_path')}")
        print(f"   - Markdown: report/regulation_report_reason.md")

    email_status = final_state.get("email_status", {})
    if email_status:
        status_icon = "✅" if email_status.get("success") else "⚠️"
        recipients = email_status.get("recipients") or []
        recipient = ", ".join(recipients) if recipients else "미지정"
        print("\n📧 이메일 발송 결과:")
        print(f"   {status_icon} 수신자: {recipient}")
        if email_status.get("errors"):
            for error in email_status["errors"]:
                print(f"   오류: {error}")
        if email_status.get("details"):
            for detail in email_status["details"]:
                icon = "✅" if detail.get("success") else "❌"
                target = detail.get("recipient") or detail.get("input") or "알 수 없음"
                message = detail.get("error")
                if message:
                    print(f"   {icon} {target} → {message}")
                else:
                    print(f"   {icon} {target} 전송 완료")

    print("\n" + "=" * 80)
    print("🎉 완료! 생성된 보고서를 확인하세요.")
    print("=" * 80)


if __name__ == "__main__":
    main()
