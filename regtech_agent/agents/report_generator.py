"""
Report Generation Agent - 최종 통합 보고서 생성
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from ..models import (
    BusinessInfo,
    Regulation,
    ChecklistItem,
    ExecutionPlan,
    RiskAssessment,
    FinalReport
)
from ..utils import merge_evidence, save_report_pdf, format_evidence_link


@tool
def generate_final_report(
    business_info: BusinessInfo,
    regulations: List[Regulation],
    checklists: List[ChecklistItem],
    execution_plans: List[ExecutionPlan],
    risk_assessment: RiskAssessment
) -> Dict[str, Any]:
    """전체 분석 결과를 통합 마크다운 보고서로 작성하고 PDF로 저장합니다.

    Args:
        business_info: 사업 정보
        regulations: 규제 목록
        checklists: 체크리스트
        execution_plans: 실행 계획
        risk_assessment: 리스크 평가

    Returns:
        최종 보고서 (통합 마크다운 + PDF 경로)
    """
    print("📄 [Report Generation Agent] 통합 보고서 생성 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    # === 1. 기본 통계 계산 ===
    priority_count = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    category_count = {}
    for reg in regulations:
        priority_count[reg['priority']] += 1
        cat = reg['category']
        category_count[cat] = category_count.get(cat, 0) + 1

    high_risk_items = risk_assessment.get('high_risk_items', [])
    total_risk_score = risk_assessment.get('total_risk_score', 0)
    immediate_actions = [reg for reg in regulations if reg['priority'] == 'HIGH']

    regulation_evidence = merge_evidence([reg.get('sources', []) for reg in regulations])
    checklist_evidence = merge_evidence([item.get('evidence', []) for item in checklists])
    execution_plan_evidence = merge_evidence([plan.get('evidence', []) for plan in execution_plans])
    risk_evidence = merge_evidence([
        item.get('evidence', []) for bucket in risk_assessment.get('risk_matrix', {}).values()
        for item in bucket
    ] if isinstance(risk_assessment.get('risk_matrix'), dict) else [])
    all_citations = merge_evidence([
        regulation_evidence,
        checklist_evidence,
        execution_plan_evidence,
        risk_evidence
    ])

    # === 2. 통합 마크다운 보고서 생성 ===
    print("   통합 마크다운 보고서 작성 중...")

    # 2-1. 헤더 및 사업 정보
    full_markdown = f"""# 규제 준수 분석 통합 보고서

> 생성일: {datetime.now().strftime('%Y년 %m월 %d일')}

---

## 1. 사업 정보

| 항목 | 내용 |
|------|------|
| **업종** | {business_info.get('industry', 'N/A')} |
| **제품명** | {business_info.get('product_name', 'N/A')} |
| **원자재** | {business_info.get('raw_materials', 'N/A')} |
| **제조 공정** | {', '.join(business_info.get('processes', []))} |
| **직원 수** | {business_info.get('employee_count', 0)}명 |
| **판매 방식** | {', '.join(business_info.get('sales_channels', []))} |

---

## 2. 분석 요약

### 2.1 규제 현황
- **총 규제 개수**: {len(regulations)}개
- **우선순위 분포**:
  - 🔴 HIGH: {priority_count['HIGH']}개 (즉시 조치 필요)
  - 🟡 MEDIUM: {priority_count['MEDIUM']}개 (1-3개월 내 조치)
  - 🟢 LOW: {priority_count['LOW']}개 (6개월 내 조치)
- **카테고리 분포**:
{chr(10).join(f'  - {cat}: {count}개' for cat, count in category_count.items())}

### 2.2 리스크 평가
- **전체 리스크 점수**: {total_risk_score:.1f}/10
- **고위험 규제**: {len(high_risk_items)}개
- **즉시 조치 필요**: {len(immediate_actions)}개

---

## 3. 규제 목록 및 분류
"""

    # 2-2. 카테고리별 규제 목록
    categories = list(set(reg['category'] for reg in regulations))
    for i, category in enumerate(categories, 1):
        full_markdown += f"\n### 3.{i} {category}\n\n"

        category_regs = [reg for reg in regulations if reg['category'] == category]
        for j, reg in enumerate(category_regs, 1):
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[reg['priority']]
            full_markdown += f"""#### 3.{i}.{j} {priority_icon} {reg['name']}

**우선순위:** {reg['priority']}
**관할 기관:** {reg['authority']}
**적용 이유:** {reg['why_applicable']}

**주요 요구사항:**

"""
            # 주요 요구사항을 list 형식으로 출력 (각 항목 사이에 빈 줄 추가)
            key_reqs = reg.get('key_requirements', [])
            for idx, req in enumerate(key_reqs):
                full_markdown += f"- {req}"
                # 마지막 항목이 아니면 줄바꿈 추가
                if idx < len(key_reqs) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"
            if reg.get('penalty'):
                full_markdown += f"**벌칙:** {reg['penalty']}\n\n"

            if reg.get('sources'):
                full_markdown += "**근거 출처:**\n\n"
                for idx, src in enumerate(reg['sources']):
                    full_markdown += f"  - {format_evidence_link(src)}"
                    if idx < len(reg['sources']) - 1:
                        full_markdown += "\n\n"
                    else:
                        full_markdown += "\n"
                full_markdown += "\n"

    # 2-3. 실행 체크리스트
    full_markdown += "\n---\n\n## 4. 실행 체크리스트\n\n"

    for reg in regulations:
        reg_checklists = [c for c in checklists if c['regulation_id'] == reg['id']]
        if reg_checklists:
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[reg['priority']]
            full_markdown += f"### 4.{regulations.index(reg)+1} {priority_icon} {reg['name']}\n\n"

            for item in reg_checklists:
                full_markdown += f"- [ ] **{item['task_name']}**\n"
                full_markdown += f"  - 담당: {item['responsible_dept']}\n"
                full_markdown += f"  - 마감: {item['deadline']}\n"
                full_markdown += "\n"
                if item.get('evidence'):
                    full_markdown += "  **근거 출처:**\n\n"
                    for idx, ev in enumerate(item['evidence']):
                        full_markdown += f"  - {format_evidence_link(ev)}"
                        if idx < len(item['evidence']) - 1:
                            full_markdown += "\n\n  "
                        else:
                            full_markdown += "\n"
                    full_markdown += "\n"

    # 2-4. 실행 계획 및 타임라인
    full_markdown += "\n---\n\n## 5. 실행 계획 및 타임라인\n\n"

    for plan in execution_plans:
        reg_name = plan['regulation_name']
        priority = next((r['priority'] for r in regulations if r['id'] == plan['regulation_id']), 'MEDIUM')
        priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[priority]

        full_markdown += f"### 5.{execution_plans.index(plan)+1} {priority_icon} {reg_name}\n\n"
        full_markdown += f"**타임라인:** {plan['timeline']}  \n"
        full_markdown += f"**시작 예정:** {plan['start_date']}  \n\n"

        # 마일스톤
        if plan.get('milestones'):
            full_markdown += "**주요 마일스톤:**\n\n"
            milestones = plan['milestones']
            for idx, milestone in enumerate(milestones):
                full_markdown += f"- {milestone['name']} (완료 목표: {milestone['deadline']})"
                # 마지막 항목이 아니면 줄바꿈 추가
                if idx < len(milestones) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"

        if plan.get('evidence'):
            full_markdown += "**근거 출처:**\n\n"
            for idx, ev in enumerate(plan['evidence']):
                full_markdown += f"  - {format_evidence_link(ev)}"
                if idx < len(plan['evidence']) - 1:
                    full_markdown += "\n\n"
                else:
                    full_markdown += "\n"
            full_markdown += "\n"

    # 2-5. 리스크 평가
    full_markdown += "\n---\n\n## 6. 리스크 평가\n\n"
    full_markdown += f"### 6.1 전체 리스크 평가\n\n"
    full_markdown += f"**전체 리스크 점수:** {total_risk_score:.1f}/10\n\n"

    risk_level = "매우 높음" if total_risk_score >= 8 else "높음" if total_risk_score >= 6 else "중간"
    full_markdown += f"**리스크 수준:** {risk_level}\n\n"

    if high_risk_items:
        full_markdown += "### 6.2 고위험 규제 (상위 5개)\n\n"
        for item in high_risk_items[:5]:
            full_markdown += f"#### {item['regulation_name']}\n\n"
            full_markdown += f"**리스크 점수:** {item['risk_score']}/10\n\n"
            full_markdown += f"**처벌 유형:** {item['penalty_type']}\n\n"
            full_markdown += f"**사업 영향:** {item['business_impact']}\n\n"

            if item.get('mitigation_priority'):
                full_markdown += f"**완화 우선순위:** {item['mitigation_priority']}\n\n"

            if item.get('evidence'):
                full_markdown += "**근거 출처:**\n\n"
                for idx, ev in enumerate(item['evidence']):
                    full_markdown += f"  - {format_evidence_link(ev)}"
                    if idx < len(item['evidence']) - 1:
                        full_markdown += "\n\n"
                    else:
                        full_markdown += "\n"
                full_markdown += "\n"

    # 2-6. 경영진 요약 (LLM으로 생성)
    print("   경영진 요약 생성 중...")

    exec_summary_prompt = f"""
다음 규제 분석 결과를 바탕으로 경영진을 위한 핵심 요약을 작성하세요.

[분석 결과]
- 총 규제: {len(regulations)}개
- HIGH: {priority_count['HIGH']}개, MEDIUM: {priority_count['MEDIUM']}개, LOW: {priority_count['LOW']}개
- 리스크 점수: {total_risk_score:.1f}/10
- 고위험 규제: {len(high_risk_items)}개

다음 형식으로 작성하세요 (마크다운):

### 핵심 인사이트
- 인사이트 1 (구체적 숫자 포함)
- 인사이트 2
- 인사이트 3

### 의사결정 포인트
- [ ] 결정 사항 1
- [ ] 결정 사항 2
- [ ] 결정 사항 3

### 권장 조치 (우선순위 순)
1. **즉시:** [조치 내용]
2. **1개월 내:** [조치 내용]
3. **3개월 내:** [조치 내용]

간결하고 명확하게 작성하세요.
"""

    exec_response = llm.invoke(exec_summary_prompt)
    executive_summary = exec_response.content.strip()

    full_markdown += f"\n---\n\n## 7. 경영진 요약\n\n{executive_summary}\n"

    # 2-7. Next Steps
    full_markdown += "\n---\n\n## 8. 다음 단계\n\n"

    next_steps = [
        f"**1단계 (즉시):** HIGH 우선순위 {priority_count['HIGH']}개 규제 착수",
        "**2단계 (1주일 내):** 담당 부서 및 책임자 지정",
        "**3단계 (2주일 내):** 상세 실행 일정 확정 및 예산 승인",
        "**4단계 (1개월):** 월 단위 진행 상황 모니터링 체계 구축",
        "**5단계 (분기별):** 전문가 검토 및 보완"
    ]

    for step in next_steps:
        full_markdown += f"- {step}\n"

    if all_citations:
        full_markdown += "\n---\n\n## 9. 근거 출처 모음\n\n"
        for idx, citation in enumerate(all_citations, 1):
            full_markdown += f"  - {format_evidence_link(citation)}"
            if idx < len(all_citations):
                full_markdown += "\n\n"
            else:
                full_markdown += "\n"

    # 2-8. 면책 조항
    full_markdown += "\n---\n\n## 면책 조항\n\n"
    full_markdown += "> 본 보고서는 AI 기반 분석 도구로 생성된 참고 자료입니다. "
    full_markdown += "실제 규제 준수 여부는 반드시 전문가의 검토를 받으시기 바랍니다. "
    full_markdown += "본 보고서 내용으로 인한 법적 책임은 사용자에게 있습니다.\n"

    # === 3. 인사이트 및 액션 아이템 추출 (구조화된 데이터) ===
    print("   핵심 데이터 추출 중...")

    key_insights = [
        f"총 {len(regulations)}개 규제 적용 대상 - 체계적 준수 관리 필요",
        f"HIGH 우선순위 {priority_count['HIGH']}개 규제는 사업 개시 전 필수 완료",
        f"전체 리스크 점수 {total_risk_score:.1f}/10 - {'즉각 대응 필요' if total_risk_score >= 7 else '전문가 컨설팅 권장'}"
    ]

    action_items = []
    for reg in immediate_actions[:3]:
        action_items.append({
            "name": f"{reg['name']} 준수 조치 시작",
            "deadline": "즉시",
            "priority": "HIGH"
        })

    risk_highlights = []
    for item in high_risk_items[:3]:
        penalty = item.get('penalty_type') or "제재 정보 없음"
        impact = item.get('business_impact') or "영향 정보 미기재"
        risk_highlights.append(
            f"{item['regulation_name']} 미준수 시 {penalty} - {impact}"
        )

    # === 4. PDF 저장 ===
    print("   PDF 파일 생성 중...")

    try:
        pdf_path = save_report_pdf(full_markdown, Path("report"))
        report_pdf_path = str(pdf_path)
        print(f"   ✓ PDF 저장 완료: {report_pdf_path}")
    except Exception as e:
        print(f"   ⚠ PDF 생성 실패: {e}")
        report_pdf_path = "PDF 생성 실패"

    # === 5. 최종 보고서 반환 ===
    final_report: FinalReport = {
        "executive_summary": executive_summary,
        "key_insights": key_insights,
        "action_items": action_items,
        "risk_highlights": risk_highlights,
        "next_steps": next_steps,
        "full_markdown": full_markdown,
        "report_pdf_path": report_pdf_path,
        "citations": all_citations
    }

    print(f"   ✓ 통합 보고서 생성 완료\n")

    return {"final_report": final_report}