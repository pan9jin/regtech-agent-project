"""이메일 발송 유틸리티"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Optional
from pathlib import Path
import os


class EmailSender:
    """이메일 발송 클래스"""

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        test_mode: bool = False
    ):
        """
        Args:
            smtp_server: SMTP 서버 주소
            smtp_port: SMTP 포트
            username: 이메일 계정 (환경변수 EMAIL_USERNAME 사용 가능)
            password: 이메일 비밀번호 (환경변수 EMAIL_PASSWORD 사용 가능)
            test_mode: 테스트 모드 (True면 실제 발송 없이 로그만 출력)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username or os.getenv("EMAIL_USERNAME")
        self.password = password or os.getenv("EMAIL_PASSWORD")
        self.test_mode = test_mode or (not self.username or not self.password)

    def send_checklist_to_assignee(
        self,
        assignee_email: str,
        assignee_name: str,
        regulation_name: str,
        checklist_items: List[Dict[str, Any]],
        pdf_path: Optional[str] = None
    ) -> bool:
        """
        담당자에게 체크리스트를 이메일로 발송

        Args:
            assignee_email: 담당자 이메일
            assignee_name: 담당자 이름
            regulation_name: 규제명
            checklist_items: 체크리스트 항목들
            pdf_path: 첨부할 PDF 파일 경로 (선택)

        Returns:
            발송 성공 여부
        """
        subject = f"[규제 준수] {regulation_name} - 체크리스트 플래닝 결과"

        # HTML 이메일 본문 생성
        html_content = self._create_checklist_html(
            assignee_name=assignee_name,
            regulation_name=regulation_name,
            checklist_items=checklist_items
        )

        return self.send_email(
            to_email=assignee_email,
            subject=subject,
            html_content=html_content,
            attachment_paths=[pdf_path] if pdf_path else None
        )

    def send_workflow_notification(
        self,
        to_email: str,
        to_name: str,
        workflow_status: Dict[str, Any],
        regulation_name: str
    ) -> bool:
        """
        워크플로우 진행 상황 알림 발송

        Args:
            to_email: 수신자 이메일
            to_name: 수신자 이름
            workflow_status: 워크플로우 상태 정보
            regulation_name: 규제명

        Returns:
            발송 성공 여부
        """
        subject = f"[워크플로우 알림] {regulation_name} - 진행 상황 업데이트"

        html_content = self._create_workflow_notification_html(
            to_name=to_name,
            workflow_status=workflow_status,
            regulation_name=regulation_name
        )

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content
        )

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """
        이메일 발송 (범용)

        Args:
            to_email: 수신자 이메일
            subject: 제목
            html_content: HTML 본문
            text_content: 텍스트 본문 (선택)
            attachment_paths: 첨부파일 경로 리스트 (선택)

        Returns:
            발송 성공 여부
        """
        # 테스트 모드
        if self.test_mode:
            print(f"\n📧 [테스트 모드] 이메일 발송 시뮬레이션")
            print(f"   수신: {to_email}")
            print(f"   제목: {subject}")
            print(f"   첨부파일: {attachment_paths if attachment_paths else '없음'}")
            print(f"   ✅ 이메일 발송 시뮬레이션 완료\n")
            return True

        if not self.username or not self.password:
            print("⚠️  이메일 계정 정보가 설정되지 않았습니다.")
            print("   환경변수 EMAIL_USERNAME, EMAIL_PASSWORD를 설정하세요.")
            return False

        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject

            # 텍스트 버전
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)

            # HTML 버전
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 첨부파일 추가
            if attachment_paths:
                for file_path in attachment_paths:
                    if file_path and Path(file_path).exists():
                        with open(file_path, 'rb') as f:
                            attachment = MIMEApplication(f.read())
                            attachment.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=Path(file_path).name
                            )
                            msg.attach(attachment)

            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            print(f"✅ 이메일 발송 성공: {to_email}")
            return True

        except Exception as e:
            print(f"❌ 이메일 발송 실패: {e}")
            return False

    def _create_checklist_html(
        self,
        assignee_name: str,
        regulation_name: str,
        checklist_items: List[Dict[str, Any]]
    ) -> str:
        """체크리스트 이메일 HTML 생성"""

        # 체크리스트 항목을 HTML 테이블로 변환
        checklist_rows = ""
        for idx, item in enumerate(checklist_items, 1):
            checklist_rows += f"""
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{idx}</td>
                <td style="padding: 12px; border: 1px solid #ddd;"><strong>{item.get('task_name', '-')}</strong></td>
                <td style="padding: 12px; border: 1px solid #ddd;">{item.get('responsible_dept', '-')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{item.get('deadline', '-')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{item.get('estimated_cost', '-')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{item.get('estimated_time', '-')}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #3498db; color: white; padding: 20px; border-radius: 5px; }}
                .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 5px; margin-top: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: white; }}
                th {{ background-color: #3498db; color: white; padding: 12px; border: 1px solid #ddd; }}
                .footer {{ margin-top: 30px; padding: 15px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>규제 준수 체크리스트</h1>
                    <p>담당자: {assignee_name}님</p>
                </div>

                <div class="content">
                    <h2 style="color: #2c3e50;">{regulation_name}</h2>
                    <p>안녕하세요, {assignee_name}님.</p>
                    <p>'{regulation_name}' 규제 준수를 위한 체크리스트가 생성되었습니다.</p>
                    <p>아래 항목들을 검토하시고 필요한 조치를 취해주시기 바랍니다.</p>

                    <table>
                        <thead>
                            <tr>
                                <th>No.</th>
                                <th>작업</th>
                                <th>담당 부서</th>
                                <th>마감일</th>
                                <th>예상 비용</th>
                                <th>소요 기간</th>
                            </tr>
                        </thead>
                        <tbody>
                            {checklist_rows}
                        </tbody>
                    </table>
                </div>

                <div class="footer">
                    <p>이 메시지는 규제 준수 관리 시스템에서 자동으로 발송되었습니다.</p>
                    <p>문의사항이 있으시면 담당 부서에 연락해주세요.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _create_workflow_notification_html(
        self,
        to_name: str,
        workflow_status: Dict[str, Any],
        regulation_name: str
    ) -> str:
        """워크플로우 알림 이메일 HTML 생성"""

        completed = workflow_status.get('completed', 0)
        total = workflow_status.get('total', 0)
        progress = (completed / total * 100) if total > 0 else 0

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #27ae60; color: white; padding: 20px; border-radius: 5px; }}
                .progress-bar {{ width: 100%; background-color: #ecf0f1; border-radius: 10px; overflow: hidden; margin: 20px 0; }}
                .progress-fill {{ background-color: #27ae60; height: 30px; line-height: 30px; text-align: center; color: white; font-weight: bold; }}
                .status-item {{ padding: 10px; margin: 10px 0; background-color: #f9f9f9; border-left: 4px solid #3498db; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>워크플로우 진행 상황</h1>
                    <p>{regulation_name}</p>
                </div>

                <div style="padding: 20px;">
                    <p>안녕하세요, {to_name}님.</p>
                    <p>워크플로우 진행 상황을 안내드립니다.</p>

                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progress}%;">
                            {progress:.0f}%
                        </div>
                    </div>

                    <div class="status-item">
                        <strong>완료:</strong> {completed} / {total} 작업
                    </div>

                    <div class="status-item">
                        <strong>상태:</strong> {workflow_status.get('status', 'IN_PROGRESS')}
                    </div>
                </div>

                <div style="margin-top: 30px; padding: 15px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d;">
                    <p>이 메시지는 워크플로우 자동화 시스템에서 발송되었습니다.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html


def send_checklists_by_assignee(
    checklists: List[Dict[str, Any]],
    assignee_contacts: Dict[str, str],
    pdf_path: Optional[str] = None
) -> Dict[str, bool]:
    """
    담당자별로 체크리스트를 그룹핑하여 이메일 발송

    Args:
        checklists: 체크리스트 항목들
        assignee_contacts: 담당자 이름 -> 이메일 매핑
        pdf_path: 첨부할 PDF 파일

    Returns:
        담당자별 발송 성공 여부
    """
    email_sender = EmailSender()

    # 담당자별로 그룹핑
    by_assignee = {}
    for checklist in checklists:
        for item in checklist.get('items', []):
            assignee = item.get('responsible_dept', '미지정')
            if assignee not in by_assignee:
                by_assignee[assignee] = {
                    'regulation': checklist.get('regulation_name', ''),
                    'items': []
                }
            by_assignee[assignee]['items'].append(item)

    # 각 담당자에게 이메일 발송
    results = {}
    for assignee, data in by_assignee.items():
        email = assignee_contacts.get(assignee)
        if not email:
            print(f"⚠️  담당자 '{assignee}'의 이메일 정보가 없습니다.")
            results[assignee] = False
            continue

        success = email_sender.send_checklist_to_assignee(
            assignee_email=email,
            assignee_name=assignee,
            regulation_name=data['regulation'],
            checklist_items=data['items'],
            pdf_path=pdf_path
        )
        results[assignee] = success

    return results