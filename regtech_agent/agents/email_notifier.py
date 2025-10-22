"""
Email Notification Agent
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import tool
from markdown import markdown

from ..models import BusinessInfo, FinalReport, ChecklistItem, ExecutionPlan
from ..email_utils import (
    EmailSender,
    prepare_email_recipient,
    create_email_body,
    extract_executive_summary,
)


@tool
def send_final_report_email(
    final_report: FinalReport,
    business_info: BusinessInfo,
    checklists: List[ChecklistItem],
    execution_plans: List[ExecutionPlan],
    recipient_email: Optional[str] = None,
) -> Dict[str, Any]:
    """최종 보고서를 이메일로 전송합니다."""
    load_dotenv()

    default_recipient = business_info.get("contact_email") or None
    target_email, validation_error = prepare_email_recipient(recipient_email, default_recipient)

    pdf_path = Path(final_report.get("report_pdf_path", ""))
    pdf_exists = pdf_path.exists()
    pdf_filename = pdf_path.name if pdf_exists else "regulation_report.pdf"

    summary_md = final_report.get("executive_summary", "") or extract_executive_summary(
        final_report.get("full_markdown", "")
    )
    summary_html = markdown(summary_md) if summary_md else "<p>요약 정보가 없습니다.</p>"

    body = create_email_body(
        summary=summary_html,
        analysis_scope={
            "industry": business_info.get("industry", ""),
            "timeframe": final_report.get("timeframe") or business_info.get("analysis_period", ""),
            "description": business_info.get("analysis_scope", ""),
            "keywords": business_info.get("keywords", []),
        },
        pdf_filename=pdf_filename,
        checklist_count=len(checklists),
        plan_count=len(execution_plans),
        insights=final_report.get("key_insights", []),
        next_steps=final_report.get("next_steps", []),
    )

    sender = EmailSender()
    status_payload = {
        "recipient": target_email,
        "success": False,
        "error": validation_error,
        "attachments": [pdf_filename] if pdf_exists else [],
        "attempted": True,
    }

    if validation_error:
        return {"email_status": status_payload}

    if not target_email:
        status_payload["error"] = "수신자 이메일이 지정되지 않았습니다."
        return {"email_status": status_payload}

    if not pdf_exists:
        print("⚠️  PDF 보고서를 찾을 수 없어 첨부 없이 전송합니다.")

    subject = f"[RegTech Assistant] {business_info.get('industry', '규제')} 분석 보고서"

    success = sender.send_report(
        recipient_email=target_email,
        subject=subject,
        body=body,
        pdf_path=pdf_path if pdf_exists else None,
    )

    status_payload["success"] = success
    if not success:
        status_payload["error"] = sender.last_error or "SMTP 전송에 실패했습니다. Gmail 설정을 확인하세요."

    return {"email_status": status_payload}
