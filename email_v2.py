"""이메일 전송 유틸리티.

Gmail SMTP를 사용하여 보고서를 첨부파일과 함께 전송합니다.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional, List


class EmailSender:
    """Gmail SMTP를 사용한 이메일 전송 클래스."""

    def __init__(
        self,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
    ):
        """
        Args:
            sender_email: 발신자 Gmail 주소 (기본값: 환경 변수에서 읽기)
            sender_password: Gmail 앱 비밀번호 (기본값: 환경 변수에서 읽기)
        """
        self.sender_email = sender_email or os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = sender_password or os.getenv(
            "GMAIL_APP_PASSWORD")

        if not self.sender_email or not self.sender_password:
            raise ValueError(
                "Gmail 인증 정보가 설정되지 않았습니다. "
                "환경 변수 'GMAIL_SENDER_EMAIL'과 'GMAIL_APP_PASSWORD'를 확인하세요."
            )

        # Gmail SMTP 설정
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_report(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        pdf_path: Optional[Path] = None,
    ) -> bool:
        """보고서를 이메일로 전송합니다.

        Args:
            recipient_email: 수신자 이메일 주소
            subject: 이메일 제목
            body: 이메일 본문 (HTML 또는 텍스트)
            pdf_path: 첨부할 PDF 파일 경로

        Returns:
            성공 여부 (True/False)
        """
        try:
            # 이메일 메시지 생성
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = subject

            # 본문 추가 (HTML 형식)
            message.attach(MIMEText(body, "html"))

            # PDF 첨부
            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=Path(pdf_path).name,
                    )
                    message.attach(pdf_attachment)

            # SMTP 연결 및 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # TLS 암호화
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            print(f"✓ 이메일이 성공적으로 전송되었습니다: {recipient_email}")
            return True

        except Exception as exc:
            print(f"✗ 이메일 전송 실패: {exc}")
            return False


def create_email_body(
    summary: str,
    analysis_scope: dict,
    pdf_filename: str = "trend_report.pdf",
) -> str:
    """이메일 본문 HTML을 생성합니다.

    Args:
        summary: 보고서 핵심 요약
        analysis_scope: 분석 범위 정보
        pdf_filename: 첨부된 PDF 파일명

    Returns:
        HTML 형식의 이메일 본문
    """
    html = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: 'Apple SD Gothic Neo', 'Nanum Gothic', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
          }}
          .header {{
            background-color: #1a237e;
            color: white;
            padding: 20px;
            border-radius: 5px;
          }}
          .section {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 5px;
          }}
          .scope-info {{
            background-color: #e3f2fd;
            padding: 10px;
            border-left: 4px solid #1976d2;
            margin: 10px 0;
          }}
          .summary {{
            white-space: pre-wrap;
            background-color: #fff;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
          }}
          .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
          }}
        </style>
      </head>
      <body>
        <div class="header">
          <h1>📊 트렌드 분석 보고서</h1>
          <p>자동 생성된 산업 트렌드 분석 결과입니다.</p>
        </div>

        <div class="section">
          <h2>🎯 분석 범위</h2>
          <div class="scope-info">
            <strong>산업:</strong> {analysis_scope.get('industry', 'N/A')}<br>
            <strong>지역:</strong> {analysis_scope.get('region', 'N/A')}<br>
            <strong>기간:</strong> {analysis_scope.get('timeframe', 'N/A')}
            ({analysis_scope.get('start_date', '')} ~ {analysis_scope.get('end_date', '')})<br>
            <strong>키워드:</strong> {', '.join(analysis_scope.get('keywords', []))}
          </div>
        </div>

        <div class="section">
          <h2>📝 핵심 요약</h2>
          <div class="summary">{summary}</div>
        </div>

        <div class="section">
          <h2>📎 첨부 파일</h2>
          <p>상세한 분석 결과는 첨부된 <strong>{pdf_filename}</strong> 파일을 참조하세요.</p>
          <ul>
            <li>PDF 보고서: 전체 분석 내용 (그래프, 표 포함)</li>
          </ul>
        </div>

        <div class="footer">
          <p>🤖 본 보고서는 AI 기반 트렌드 분석 시스템에 의해 자동 생성되었습니다.</p>
          <p>문의사항이 있으시면 회신 부탁드립니다.</p>
        </div>
      </body>
    </html>
    """
    return html


def extract_executive_summary(markdown_report: str) -> str:
    """마크다운 보고서에서 Executive Summary 섹션을 추출합니다.

    Args:
        markdown_report: 전체 마크다운 보고서

    Returns:
        Executive Summary 내용 (또는 처음 500자)
    """
    lines = markdown_report.split("\n")
    summary_lines = []
    in_summary = False

    for line in lines:
        # Executive Summary 섹션 시작
        if "executive summary" in line.lower():
            in_summary = True
            continue
        # 다음 섹션 시작 (## 또는 # 로 시작)
        elif in_summary and line.strip().startswith("#"):
            break
        # Summary 내용 수집
        elif in_summary and line.strip():
            summary_lines.append(line.strip())

    # Summary를 찾지 못한 경우 처음 500자 반환
    if not summary_lines:
        return markdown_report[:500] + "..." if len(markdown_report) > 500 else markdown_report

    return "\n".join(summary_lines)
