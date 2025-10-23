"""
Email utility helpers for RegTech Agent.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


load_dotenv()


def prepare_email_recipient(
    provided_email: Optional[str],
    default_email: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Normalize and validate recipient email."""
    if provided_email:
        candidate = provided_email.strip()
    elif default_email:
        candidate = default_email.strip()
    else:
        return "", "수신자 이메일이 지정되지 않았습니다."

    if not candidate:
        return "", "수신자 이메일이 비어 있습니다."

    if "@" not in candidate or candidate.count("@") != 1 or "." not in candidate.split("@")[1]:
        return candidate, "유효하지 않은 이메일 형식입니다. 예: user@example.com"

    return candidate, None


def extract_executive_summary(markdown_report: str) -> str:
    """Extract an executive summary from markdown text."""
    if not markdown_report:
        return ""

    lines = markdown_report.splitlines()
    summary_lines = []
    in_summary = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("##") and "executive summary" in stripped.lower():
            in_summary = True
            continue
        if in_summary and stripped.startswith("#"):
            break
        if in_summary:
            summary_lines.append(stripped)

    if summary_lines:
        return "\n".join(summary_lines)

    return markdown_report[:500] + ("..." if len(markdown_report) > 500 else "")


def create_email_body(
    summary: str,
    analysis_scope: Dict[str, Any],
    pdf_filename: str,
    checklist_count: int = 0,
    plan_count: int = 0,
    insights: Optional[List[str]] = None,
    next_steps: Optional[List[str]] = None,
) -> str:
    """Build HTML email body summarizing the report with checklist style."""
    insights = insights or []
    next_steps = next_steps or []

    insights_html = "".join(f"<li>{item}</li>" for item in insights[:5]) or "<li>등록된 인사이트가 없습니다.</li>"
    next_steps_html = "".join(f"<li>{item}</li>" for item in next_steps[:5]) or "<li>다음 단계 제안이 없습니다.</li>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 720px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1f5ca6; color: white; padding: 18px 22px; border-radius: 6px; }}
            .section {{ margin-top: 24px; padding: 18px 22px; background-color: #f7f9fc; border-radius: 6px; }}
            h1 {{ margin: 0 0 6px 0; font-size: 22px; }}
            h2 {{ margin-top: 0; color: #1f5ca6; }}
            ul {{ padding-left: 20px; }}
            .footer {{ margin-top: 32px; font-size: 12px; color: #6b7280; text-align: center; }}
            .badge {{ display: inline-block; background-color: #2563eb; color: #fff; padding: 4px 10px; border-radius: 12px; font-size: 12px; margin-right: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>규제 준수 분석 결과</h1>
                <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>

            <div class="section">
                <h2>요약</h2>
                <span class="badge">체크리스트 {checklist_count}건</span>
                <span class="badge">실행 계획 {plan_count}건</span>
                <div style="margin-top: 16px;">
                    {summary or '<p>요약 정보가 없습니다.</p>'}
                </div>
            </div>

            <div class="section">
                <h2>핵심 인사이트</h2>
                <ul>
                    {insights_html}
                </ul>
            </div>

            <div class="section">
                <h2>다음 단계 제안</h2>
                <ul>
                    {next_steps_html}
                </ul>
            </div>

            <div class="footer">
                <p>이 메일은 RegTech Assistant가 자동으로 발송했습니다.</p>
                <p>첨부된 PDF 보고서를 참고해주세요. ({pdf_filename})</p>
            </div>
        </div>
    </body>
    </html>
    """


class EmailSender:
    """SMTP email sender using Gmail credentials."""

    def __init__(
        self,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        self.sender_email = sender_email or os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = sender_password or os.getenv("GMAIL_APP_PASSWORD")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.last_error: Optional[str] = None

    def _ensure_credentials(self) -> bool:
        if self.sender_email and self.sender_password:
            return True
        self.last_error = (
            "Gmail 인증 정보가 설정되지 않았습니다. "
            "GMAIL_SENDER_EMAIL / GMAIL_APP_PASSWORD 환경 변수를 확인하세요."
        )
        print(f"⚠️  {self.last_error}")
        return False

    def send_report(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        pdf_path: Optional[Path] = None,
    ) -> bool:
        """Send report email with optional PDF attachment."""
        self.last_error = None

        if not self._ensure_credentials():
            return False

        try:
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = subject

            message.attach(MIMEText(body, "html", "utf-8"))

            if pdf_path and pdf_path.exists():
                with pdf_path.open("rb") as file_handle:
                    attachment = MIMEApplication(file_handle.read(), _subtype="pdf")
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=pdf_path.name,
                    )
                    message.attach(attachment)

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.ehlo()
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            print(f"✅ 이메일 발송 성공: {recipient_email}")
            return True

        except Exception as exc:
            self.last_error = str(exc)
            print(f"❌ 이메일 발송 실패: {exc}")
            return False
