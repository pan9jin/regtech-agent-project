"""
워크플로우 자동화 실행 예제

이 스크립트는 다음을 수행합니다:
1. 규제 분석 실행
2. 담당자별 체크리스트 자동 분배
3. 각 담당자에게 이메일 자동 발송
4. 분배 현황 리포트 생성
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.runner import run_workflow
from utils.task_distributor import auto_distribute_and_send, export_distribution_to_csv
from utils.pdf_generator import generate_pdf_report
import json


def main():
    print("=" * 60)
    print("규제 준수 워크플로우 자동화 실행")
    print("=" * 60)
    print()

    # ============================================================
    # Step 1: 사업 정보 입력
    # ============================================================
    print("📝 Step 1: 사업 정보 입력")
    print()

    business_info = {
        "industry": "배터리 제조",
        "product_name": "리튬이온 배터리",
        "raw_materials": "리튬, 코발트, 니켈, 전해액",
        "processes": ["화학 처리", "고온 가공", "조립"],
        "employee_count": 45,
        "sales_channels": ["B2B", "수출"],
        "export_countries": ["미국", "유럽", "일본"]
    }

    print(f"  업종: {business_info['industry']}")
    print(f"  제품: {business_info['product_name']}")
    print(f"  직원 수: {business_info['employee_count']}명")
    print()

    # ============================================================
    # Step 2: AI 기반 규제 분석 (자동)
    # ============================================================
    print("🤖 Step 2: AI 기반 규제 분석 실행 (자동)")
    print()

    # 실제 워크플로우 실행 (시간이 오래 걸리므로 주석 처리)
    # result = run_workflow(business_info)

    # 데모를 위해 기존 분석 결과 사용
    try:
        with open('regulation_analysis_with_workflow.json', 'r', encoding='utf-8') as f:
            result = json.load(f)
        print("  ✓ 규제 분석 완료 (기존 결과 사용)")
    except FileNotFoundError:
        print("  ⚠️  분석 결과 파일이 없습니다. 실제 워크플로우를 실행하세요.")
        return

    print(f"  ✓ 적용 규제: {len(result.get('regulations', []))}개")
    print(f"  ✓ 체크리스트: {len(result.get('checklists', []))}개")
    print()

    # ============================================================
    # Step 3: PDF 보고서 생성 (자동)
    # ============================================================
    print("📄 Step 3: PDF 보고서 생성 (자동)")
    print()

    pdf_path = "auto_regulation_report.pdf"
    generate_pdf_report(result, pdf_path)
    print(f"  ✓ PDF 생성 완료: {pdf_path}")
    print()

    # ============================================================
    # Step 4: 담당자별 체크리스트 자동 분배 (AI)
    # ============================================================
    print("🎯 Step 4: 담당자별 체크리스트 자동 분배 (AI)")
    print()

    # 담당자 설정 (회사에 맞게 수정 필요)
    assignee_config = {
        "안전관리팀": {
            "email": "safety@company.com",
            "manager": "김철수",
            "specialties": ["화학물질", "안전", "위험물", "보건"],
            "max_tasks": 15
        },
        "환경관리팀": {
            "email": "environment@company.com",
            "manager": "이영희",
            "specialties": ["환경", "배출", "폐기물", "오염"],
            "max_tasks": 12
        },
        "규제준수팀": {
            "email": "compliance@company.com",
            "manager": "박준호",
            "specialties": ["허가", "신고", "인증", "규제"],
            "max_tasks": 20
        }
    }

    # 자동 분배 및 이메일 발송
    distribution_result = auto_distribute_and_send(
        checklists=result.get('checklists', []),
        assignee_config=assignee_config,
        send_emails=False  # 실제 이메일 발송하려면 True로 변경
    )

    print("  분배 결과:")
    for assignee, tasks in distribution_result['distribution'].items():
        print(f"    • {assignee}: {len(tasks)}개 작업")
    print()
    print(f"  업무 균형: {distribution_result['report']['workload_balance']}")
    print()

    # ============================================================
    # Step 5: 분배 현황 CSV 저장 (자동)
    # ============================================================
    print("💾 Step 5: 분배 현황 CSV 저장 (자동)")
    print()

    csv_path = "task_distribution.csv"
    export_distribution_to_csv(distribution_result['distribution'], csv_path)
    print()

    # ============================================================
    # Step 6: 이메일 발송 시뮬레이션
    # ============================================================
    print("📧 Step 6: 이메일 발송 (자동)")
    print()

    if distribution_result['emails_sent'] > 0:
        print(f"  ✓ {distribution_result['emails_sent']}건 이메일 발송 완료")
    else:
        print("  ℹ️  이메일 발송 비활성화 (데모 모드)")
        print("  실제 발송하려면:")
        print("    1. .env 파일에 EMAIL_USERNAME, EMAIL_PASSWORD 설정")
        print("    2. send_emails=True로 변경")
    print()

    # ============================================================
    # Step 7: 자동화 통계
    # ============================================================
    print("=" * 60)
    print("📊 자동화 통계")
    print("=" * 60)
    print()

    total_steps = 9
    automated_steps = 8
    automation_rate = automated_steps / total_steps * 100

    print(f"  전체 단계: {total_steps}단계")
    print(f"  자동화 단계: {automated_steps}단계")
    print(f"  자동화율: {automation_rate:.0f}%")
    print()

    print("  단계별 자동화 여부:")
    steps = [
        ("사업 정보 입력", False),
        ("규제 검색", True),
        ("규제 분류", True),
        ("우선순위 결정", True),
        ("체크리스트 생성", True),
        ("담당자 자동 배정", True),
        ("PDF 보고서 생성", True),
        ("이메일 발송", True),
        ("작업 시작", False)
    ]

    for idx, (step_name, is_auto) in enumerate(steps, 1):
        status = "🤖 자동" if is_auto else "👤 수동"
        print(f"    {idx}. {step_name}: {status}")
    print()

    # ============================================================
    # Step 8: 생성된 파일 목록
    # ============================================================
    print("=" * 60)
    print("📁 생성된 파일")
    print("=" * 60)
    print()

    files = [
        ("auto_regulation_report.pdf", "PDF 보고서"),
        ("task_distribution.csv", "담당자별 작업 분배표"),
        ("regulation_analysis_with_workflow.json", "규제 분석 상세 데이터")
    ]

    for filename, description in files:
        if os.path.exists(filename):
            size = os.path.getsize(filename) / 1024
            print(f"  ✓ {filename} ({size:.1f} KB) - {description}")
        else:
            print(f"  ✗ {filename} - {description}")
    print()

    # ============================================================
    # Step 9: 다음 단계 안내
    # ============================================================
    print("=" * 60)
    print("🚀 다음 단계")
    print("=" * 60)
    print()

    print("  1. 담당자 이메일 설정")
    print("     → assignee_config에서 실제 이메일 주소 입력")
    print()

    print("  2. 이메일 계정 설정")
    print("     → .env 파일에 EMAIL_USERNAME, EMAIL_PASSWORD 설정")
    print()

    print("  3. 자동화 도구 연동 (선택)")
    print("     → n8n 또는 Make.com 워크플로우 설정")
    print("     → AUTOMATION_GUIDE.md 참고")
    print()

    print("  4. API 서버 실행 (선택)")
    print("     → python api/main.py")
    print("     → Webhook 엔드포인트 활성화")
    print()

    print("=" * 60)
    print("✅ 자동화 워크플로우 실행 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
