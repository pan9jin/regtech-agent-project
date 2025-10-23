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
    recipient_emails: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """최종 보고서를 이메일로 전송합니다."""
    load_dotenv()

    def normalize_candidates(values: Optional[List[str]]) -> List[str]:
        normalized: List[str] = []
        if not values:
            return normalized
        for entry in values:
            if entry is None:
                continue
            for token in str(entry).split(","):
                email = token.strip()
                if email and email not in normalized:
                    normalized.append(email)
        return normalized

    provided = recipient_emails or []
    if not provided:
        fallback = business_info.get("contact_email")
        if isinstance(fallback, list):
            provided = fallback
        elif isinstance(fallback, str):
            provided = [fallback]

    candidate_emails = normalize_candidates(provided)
    status_payload = {
        "recipients": candidate_emails,
        "details": [],
        "errors": [],
        "success": False,
        "attachments": [],
        "attempted": False,
    }

    if not candidate_emails:
        status_payload["errors"] = ["수신자 이메일이 지정되지 않았습니다."]
        return {"email_status": status_payload}

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
    if pdf_exists:
        status_payload["attachments"] = [pdf_filename]

    results: List[Dict[str, Any]] = []
    overall_success = True

    for candidate in candidate_emails:
        normalized_email, validation_error = prepare_email_recipient(candidate)
        detail: Dict[str, Any] = {
            "input": candidate,
            "recipient": normalized_email or candidate,
            "success": False,
        }

        if validation_error:
            detail["error"] = validation_error
            overall_success = False
            results.append(detail)
            continue

        results.append(detail)

    if not pdf_exists:
        print("⚠️  PDF 보고서를 찾을 수 없어 첨부 없이 전송합니다.")

    subject = f"[RegTech Assistant] {business_info.get('industry', '규제')} 분석 보고서"

    for detail in results:
        if detail.get("error"):
            continue

        success = sender.send_report(
            recipient_email=detail["recipient"],
            subject=subject,
            body=body,
            pdf_path=pdf_path if pdf_exists else None,
        )
        detail["success"] = success
        if not success:
            detail["error"] = sender.last_error or "SMTP 전송에 실패했습니다. Gmail 설정을 확인하세요."
            overall_success = False

    status_payload["details"] = results
    status_payload["recipients"] = [
        detail["recipient"] for detail in results if detail.get("recipient")
    ]
    status_payload["errors"] = [item["error"] for item in results if item.get("error")]
    if status_payload["errors"]:
        status_payload["errors"] = list(dict.fromkeys(status_payload["errors"]))
    status_payload["attempted"] = bool(results)
    status_payload["success"] = overall_success and bool(results)

    return {"email_status": status_payload}
