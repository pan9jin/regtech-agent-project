"""PDF 보고서 생성 유틸리티"""

from typing import List, Dict, Any
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


class RegulationReportGenerator:
    """규제 분석 보고서 PDF 생성기"""

    def __init__(self, output_path: str = "regulation_report.pdf"):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        self.story = []
        self.styles = getSampleStyleSheet()

        # 한글 폰트 등록 시도 (선택적)
        self._register_fonts()

        # 커스텀 스타일 추가
        self._add_custom_styles()

    def _register_fonts(self):
        """한글 폰트 등록 (시스템에 폰트가 있는 경우)"""
        self.korean_font = None
        try:
            # macOS 기본 한글 폰트 경로
            font_paths = [
                ('/System/Library/Fonts/Supplemental/AppleGothic.ttf', 'AppleGothic'),
                ('/System/Library/Fonts/Supplemental/AppleMyungjo.ttf', 'AppleMyungjo'),
                ('/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf', 'NotoSansGothic'),
            ]

            for font_path, font_name in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        self.korean_font = font_name
                        print(f"✓ 한글 폰트 등록 성공: {font_name}")
                        break
                    except Exception as e:
                        print(f"⚠️  폰트 등록 실패 ({font_name}): {e}")
                        continue

            if not self.korean_font:
                print("⚠️  한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
                self.korean_font = 'Helvetica'  # fallback
        except Exception as e:
            print(f"⚠️  폰트 등록 중 오류: {e}")
            self.korean_font = 'Helvetica'  # fallback

    def _add_custom_styles(self):
        """커스텀 스타일 추가"""
        # 한글 폰트 사용 (등록된 경우)
        font_name = self.korean_font if self.korean_font and self.korean_font != 'Helvetica' else 'Helvetica'

        # 기본 스타일에 한글 폰트 적용
        for style_name in ['Normal', 'BodyText', 'Heading1', 'Heading2', 'Heading3', 'Title']:
            if style_name in self.styles:
                self.styles[style_name].fontName = font_name

        # 제목 스타일
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=font_name
        ))

        # 섹션 제목
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#2c3e50'),
            spaceBefore=20,
            spaceAfter=12,
            fontName=font_name
        ))

        # 본문
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            fontName=font_name
        ))

        # 하이라이트
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=HexColor('#e74c3c'),
            fontName=font_name
        ))

    def _get_table_style(self, header_row=False):
        """테이블 기본 스타일 생성 (한글 폰트 적용)"""
        font_name = self.korean_font if self.korean_font and self.korean_font != 'Helvetica' else 'Helvetica'

        base_style = [
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),  # 모든 셀에 한글 폰트
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
        ]

        return base_style

    def generate_report(self, data: Dict[str, Any]) -> str:
        """보고서 생성 메인 함수"""
        # 표지
        self._add_cover_page(data)

        # 목차는 생략 (간소화)

        # 요약
        self._add_summary_section(data)

        # 규제 목록
        self._add_regulations_section(data)

        # 체크리스트
        self._add_checklist_section(data)

        # PDF 생성
        self.doc.build(self.story)

        return self.output_path

    def _add_cover_page(self, data: Dict[str, Any]):
        """표지 페이지"""
        business_info = data.get('business_info', {})

        # 로고/제목 공간
        self.story.append(Spacer(1, 2*inch))

        # 메인 제목
        title = Paragraph(
            "규제 준수 분석 보고서",
            self.styles['CustomTitle']
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.5*inch))

        # 부제
        subtitle = Paragraph(
            f"<b>{business_info.get('product_name', '제품')}</b> 제조업",
            self.styles['Heading2']
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.3*inch))

        # 사업 정보 테이블
        business_data = [
            ['업종', business_info.get('industry', '-')],
            ['제품명', business_info.get('product_name', '-')],
            ['주요 원자재', business_info.get('raw_materials', '-')],
            ['직원 수', f"{business_info.get('employee_count', 0)}명"],
        ]

        business_table = Table(business_data, colWidths=[4*cm, 10*cm])
        business_table.setStyle(TableStyle(self._get_table_style()))

        self.story.append(business_table)
        self.story.append(Spacer(1, 1*inch))

        # 생성 일자
        date_text = Paragraph(
            f"<i>생성일: {datetime.now().strftime('%Y년 %m월 %d일')}</i>",
            self.styles['Normal']
        )
        self.story.append(date_text)

        self.story.append(PageBreak())

    def _add_summary_section(self, data: Dict[str, Any]):
        """요약 섹션"""
        summary = data.get('summary', {})

        # 섹션 제목
        self.story.append(Paragraph("1. 요약", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))

        # 핵심 지표
        summary_data = [
            ['항목', '값'],
            ['적용 규제 수', f"{summary.get('total_regulations', 0)}개"],
            ['체크리스트 항목', f"{summary.get('total_tasks', summary.get('total_checklist_items', 0))}개"],
        ]

        font_name = self.korean_font if self.korean_font and self.korean_font != 'Helvetica' else 'Helvetica'
        summary_table = Table(summary_data, colWidths=[6*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#ecf0f1')]),
        ]))

        self.story.append(summary_table)
        self.story.append(Spacer(1, 0.5*inch))

    def _add_regulations_section(self, data: Dict[str, Any]):
        """규제 목록 섹션"""
        regulations = data.get('regulations', [])

        self.story.append(Paragraph("2. 적용 규제 목록", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))

        # 우선순위별 분류
        high_regs = [r for r in regulations if r.get('priority') == 'HIGH']
        medium_regs = [r for r in regulations if r.get('priority') == 'MEDIUM']
        low_regs = [r for r in regulations if r.get('priority') == 'LOW']

        # HIGH 우선순위
        if high_regs:
            self._add_regulation_priority_group('HIGH (필수)', high_regs, HexColor('#e74c3c'))

        # MEDIUM 우선순위
        if medium_regs:
            self._add_regulation_priority_group('MEDIUM (권장)', medium_regs, HexColor('#f39c12'))

        # LOW 우선순위
        if low_regs:
            self._add_regulation_priority_group('LOW (선택)', low_regs, HexColor('#27ae60'))

    def _add_regulation_priority_group(self, title: str, regulations: List[Dict], color: HexColor):
        """우선순위별 규제 그룹 추가"""
        self.story.append(Paragraph(f"<b>{title}</b>", self.styles['Heading3']))
        self.story.append(Spacer(1, 0.1*inch))

        for idx, reg in enumerate(regulations, 1):
            # 규제명
            reg_title = Paragraph(
                f"<b>{idx}. {reg.get('name', '규제명 없음')}</b>",
                self.styles['CustomBody']
            )
            self.story.append(reg_title)

            # 규제 정보 테이블
            reg_data = [
                ['카테고리', reg.get('category', '-')],
                ['관할 기관', reg.get('authority', '-')],
                ['적용 이유', reg.get('why_applicable', '-')],
            ]

            font_name = self.korean_font if self.korean_font and self.korean_font != 'Helvetica' else 'Helvetica'
            reg_table = Table(reg_data, colWidths=[3*cm, 11*cm])
            reg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
            ]))

            self.story.append(reg_table)

            # 주요 요구사항
            if reg.get('key_requirements'):
                self.story.append(Spacer(1, 0.1*inch))
                req_text = Paragraph("<b>주요 요구사항:</b>", self.styles['CustomBody'])
                self.story.append(req_text)

                for req in reg['key_requirements'][:3]:  # 최대 3개만
                    req_item = Paragraph(f"• {req}", self.styles['CustomBody'])
                    self.story.append(req_item)

            self.story.append(Spacer(1, 0.2*inch))

    def _add_checklist_section(self, data: Dict[str, Any]):
        """체크리스트 섹션"""
        checklists = data.get('checklists', [])

        self.story.append(PageBreak())
        self.story.append(Paragraph("3. 실행 체크리스트", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))

        # 규제별로 그룹핑
        checklists_by_reg = {}
        for item in checklists:
            reg_id = item.get('regulation_id')
            if reg_id not in checklists_by_reg:
                checklists_by_reg[reg_id] = {
                    'name': item.get('regulation_name', ''),
                    'items': []
                }
            checklists_by_reg[reg_id]['items'].append(item)

        # 각 규제의 체크리스트 출력
        for reg_id, reg_data in checklists_by_reg.items():
            self.story.append(Paragraph(f"<b>{reg_data['name']}</b>", self.styles['Heading3']))
            self.story.append(Spacer(1, 0.1*inch))

            for idx, item in enumerate(reg_data['items'], 1):
                checklist_data = [
                    ['[ ]', f"<b>{item.get('task_name', '')}</b>"],
                    ['담당', item.get('responsible_dept', '-')],
                    ['마감', item.get('deadline', '-')],
                    ['기간', item.get('estimated_time', '-')],
                ]

                font_name = self.korean_font if self.korean_font and self.korean_font != 'Helvetica' else 'Helvetica'
                checklist_table = Table(checklist_data, colWidths=[1*cm, 13*cm])
                checklist_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
                ]))

                self.story.append(checklist_table)
                self.story.append(Spacer(1, 0.15*inch))


def generate_pdf_report(data: Dict[str, Any], output_path: str = "regulation_report.pdf") -> str:
    """PDF 보고서 생성 헬퍼 함수

    Args:
        data: 보고서 데이터
        output_path: 출력 파일 경로

    Returns:
        생성된 PDF 파일 경로
    """
    generator = RegulationReportGenerator(output_path)
    return generator.generate_report(data)
