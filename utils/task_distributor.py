"""태스크 자동 분배 및 할당 시스템"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json


class TaskDistributor:
    """담당자별 태스크 자동 분배 클래스"""

    def __init__(self, assignee_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            assignee_config: 담당자 설정
                {
                    "안전관리팀": {
                        "email": "safety@company.com",
                        "manager": "김철수",
                        "specialties": ["화학물질", "안전", "환경"],
                        "max_tasks": 10
                    },
                    ...
                }
        """
        self.assignee_config = assignee_config or {
            "안전관리팀": {
                "email": "eunsu0613@naver.com",
                "manager": "김은수",
                "specialties": ["안전", "화학물질", "위험물"],
                "max_tasks": 15
            },
            "환경관리팀": {
                "email": "woals424@naver.com",
                "manager": "박재진",
                "specialties": ["환경", "배출", "폐기물", "에너지"],
                "max_tasks": 15
            }
        }

    def distribute_checklists(
        self,
        checklists: List[Dict[str, Any]],
        auto_assign: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        체크리스트를 담당자별로 분배

        Args:
            checklists: 전체 체크리스트
            auto_assign: 자동 할당 여부 (True면 규칙 기반 자동 할당)

        Returns:
            담당자별 그룹핑된 체크리스트
            {
                "안전관리팀": [{"task_name": "...", ...}, ...],
                "환경관리팀": [...]
            }
        """
        distribution = defaultdict(list)

        for checklist in checklists:
            # 체크리스트가 직접 항목인 경우 (평면 구조)
            if 'task_name' in checklist:
                regulation_name = checklist.get('regulation_name', '')
                item = checklist

                # 이미 담당자가 지정된 경우
                if item.get('responsible_dept'):
                    assignee = item['responsible_dept']
                # 자동 할당
                elif auto_assign:
                    assignee = self._auto_assign_task(item, regulation_name)
                    item['responsible_dept'] = assignee
                else:
                    assignee = '미지정'

                # 담당자 정보 추가
                if assignee in self.assignee_config:
                    item['assignee_email'] = self.assignee_config[assignee].get('email')
                    item['assignee_manager'] = self.assignee_config[assignee].get('manager')

                distribution[assignee].append(item.copy())

            # 체크리스트가 items를 포함하는 경우 (중첩 구조)
            else:
                regulation_name = checklist.get('regulation_name', '')
                items = checklist.get('items', [])

                for item in items:
                    # 이미 담당자가 지정된 경우
                    if item.get('responsible_dept'):
                        assignee = item['responsible_dept']
                    # 자동 할당
                    elif auto_assign:
                        assignee = self._auto_assign_task(item, regulation_name)
                        item['responsible_dept'] = assignee
                    else:
                        assignee = '미지정'

                    # 담당자 정보 추가
                    if assignee in self.assignee_config:
                        item['assignee_email'] = self.assignee_config[assignee].get('email')
                        item['assignee_manager'] = self.assignee_config[assignee].get('manager')

                    distribution[assignee].append({
                        'regulation_name': regulation_name,
                        **item
                    })

        return dict(distribution)

    def _auto_assign_task(self, task: Dict[str, Any], regulation_name: str) -> str:
        """
        규칙 기반 자동 담당자 할당

        할당 규칙:
        1. 키워드 매칭 (규제명, 작업명에서 키워드 추출)
        2. 담당자별 전문 분야 매칭
        3. 현재 업무량 고려
        """
        task_name = task.get('task_name', '').lower()
        combined_text = f"{regulation_name} {task_name}".lower()

        # 키워드 기반 매칭
        keyword_scores = {}
        for assignee, config in self.assignee_config.items():
            score = 0
            specialties = config.get('specialties', [])
            for specialty in specialties:
                if specialty.lower() in combined_text:
                    score += 1
            keyword_scores[assignee] = score

        # 최고 점수 담당자 선택
        if keyword_scores and max(keyword_scores.values()) > 0:
            best_assignee = max(keyword_scores, key=keyword_scores.get)
            return best_assignee

        # 매칭 실패 시 기본 담당자 반환
        return '규제준수팀'

    def create_task_assignments(
        self,
        distribution: Dict[str, List[Dict[str, Any]]],
        send_email: bool = False,
        create_calendar_events: bool = False
    ) -> List[Dict[str, Any]]:
        """
        담당자별 작업 할당 생성

        Args:
            distribution: 담당자별 분배된 태스크
            send_email: 이메일 자동 발송 여부
            create_calendar_events: 캘린더 이벤트 자동 생성 여부

        Returns:
            할당 결과 리스트
        """
        assignments = []

        for assignee, tasks in distribution.items():
            assignment = {
                'assignee': assignee,
                'assignee_email': self.assignee_config.get(assignee, {}).get('email'),
                'assignee_manager': self.assignee_config.get(assignee, {}).get('manager'),
                'task_count': len(tasks),
                'tasks': tasks,
                'assigned_at': datetime.now().isoformat(),
                'status': 'ASSIGNED'
            }

            # 우선순위별 분류
            high_priority = [t for t in tasks if 'high' in t.get('task_name', '').lower()]
            assignment['high_priority_count'] = len(high_priority)

            # 예상 완료일 계산
            total_days = sum([self._estimate_days(t.get('estimated_time', '')) for t in tasks])
            assignment['estimated_completion_date'] = (
                datetime.now() + timedelta(days=total_days)
            ).strftime('%Y-%m-%d')

            assignments.append(assignment)

            # 이메일 발송 (옵션)
            if send_email and assignment['assignee_email']:
                self._send_assignment_email(assignment)

            # 캘린더 이벤트 생성 (옵션)
            if create_calendar_events:
                self._create_calendar_events(assignment)

        return assignments

    def _estimate_days(self, time_str: str) -> int:
        """예상 소요 시간을 일수로 변환"""
        if not time_str:
            return 7  # 기본 7일

        time_str = time_str.lower()
        if '주' in time_str or 'week' in time_str:
            weeks = int(''.join(filter(str.isdigit, time_str)) or 1)
            return weeks * 7
        elif '일' in time_str or 'day' in time_str:
            return int(''.join(filter(str.isdigit, time_str)) or 1)
        elif '개월' in time_str or 'month' in time_str:
            months = int(''.join(filter(str.isdigit, time_str)) or 1)
            return months * 30

        return 7

    def _send_assignment_email(self, assignment: Dict[str, Any]):
        """담당자에게 할당 이메일 발송"""
        from utils.email_sender import EmailSender

        if not assignment.get('assignee_email'):
            return

        sender = EmailSender()

        # 첫 번째 규제명 추출
        regulation_name = assignment['tasks'][0].get('regulation_name', '규제 준수') if assignment['tasks'] else '규제 준수'

        sender.send_checklist_to_assignee(
            assignee_email=assignment['assignee_email'],
            assignee_name=assignment['assignee'],
            regulation_name=regulation_name,
            checklist_items=assignment['tasks']
        )

    def _create_calendar_events(self, assignment: Dict[str, Any]):
        """Google Calendar 등에 이벤트 생성 (구현 예정)"""
        # Google Calendar API 연동
        pass

    def generate_distribution_report(
        self,
        distribution: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        분배 현황 리포트 생성

        Returns:
            {
                "total_tasks": 50,
                "total_assignees": 5,
                "distribution": {
                    "안전관리팀": {"count": 15, "percentage": 30},
                    ...
                },
                "workload_balance": "균형" or "불균형"
            }
        """
        total_tasks = sum(len(tasks) for tasks in distribution.values())
        total_assignees = len(distribution)

        dist_summary = {}
        for assignee, tasks in distribution.items():
            count = len(tasks)
            dist_summary[assignee] = {
                'count': count,
                'percentage': round(count / total_tasks * 100, 1) if total_tasks > 0 else 0,
                'tasks': tasks
            }

        # 업무량 균형 체크
        if dist_summary:
            percentages = [v['percentage'] for v in dist_summary.values()]
            avg_percentage = sum(percentages) / len(percentages)
            max_diff = max(abs(p - avg_percentage) for p in percentages)
            workload_balance = '균형' if max_diff < 20 else '불균형'
        else:
            workload_balance = 'N/A'

        return {
            'total_tasks': total_tasks,
            'total_assignees': total_assignees,
            'distribution': dist_summary,
            'workload_balance': workload_balance,
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# 담당자 설정 예시
# ============================================================

DEFAULT_ASSIGNEE_CONFIG = {
    "안전관리팀": {
        "email": "eunsu0613@naver.com",
        "manager": "김은수",
        "specialties": ["화학물질", "안전", "위험", "사고", "보건"],
        "max_tasks": 15
    },
    "환경관리팀": {
        "email": "woals424@naver.com",
        "manager": "박재진",
        "specialties": ["환경", "배출", "폐기물", "오염", "대기", "수질"],
        "max_tasks": 12
    },
    "규제준수팀": {
        "email": "eunsu0613@naver.com",
        "manager": "김은수",
        "specialties": ["허가", "신고", "인증", "규제", "법규"],
        "max_tasks": 20
    },
    "품질관리팀": {
        "email": "woals424@naver.com",
        "manager": "박재진",
        "specialties": ["품질", "검사", "시험", "인증", "표준"],
        "max_tasks": 10
    },
    "법무팀": {
        "email": "eunsu0613@naver.com",
        "manager": "김은수",
        "specialties": ["법률", "계약", "소송", "지적재산"],
        "max_tasks": 8
    },
    "시설관리팀": {
        "email": "woals424@naver.com",
        "manager": "박재진",
        "specialties": ["시설", "설비", "유지보수", "점검"],
        "max_tasks": 10
    },
    "인사팀": {
        "email": "eunsu0613@naver.com",
        "manager": "김은수",
        "specialties": ["교육", "훈련", "채용", "인사"],
        "max_tasks": 8
    }
}


# ============================================================
# 편의 함수
# ============================================================

def auto_distribute_and_send(
    checklists: List[Dict[str, Any]],
    assignee_config: Optional[Dict[str, Any]] = None,
    send_emails: bool = True
) -> Dict[str, Any]:
    """
    체크리스트 자동 분배 및 이메일 발송 (원스톱)

    Args:
        checklists: 체크리스트 항목들
        assignee_config: 담당자 설정 (없으면 기본값 사용)
        send_emails: 이메일 발송 여부

    Returns:
        {
            "distribution": {...},
            "assignments": [...],
            "report": {...},
            "emails_sent": 5
        }
    """
    config = assignee_config or DEFAULT_ASSIGNEE_CONFIG
    distributor = TaskDistributor(config)

    # 1. 분배
    distribution = distributor.distribute_checklists(checklists, auto_assign=True)

    # 2. 할당 생성
    assignments = distributor.create_task_assignments(
        distribution,
        send_email=send_emails,
        create_calendar_events=False
    )

    # 3. 리포트 생성
    report = distributor.generate_distribution_report(distribution)

    return {
        'distribution': distribution,
        'assignments': assignments,
        'report': report,
        'emails_sent': len([a for a in assignments if a.get('assignee_email')]) if send_emails else 0
    }


def export_distribution_to_csv(distribution: Dict[str, List[Dict[str, Any]]], output_path: str):
    """분배 결과를 CSV로 내보내기"""
    import csv

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['담당자', '규제명', '작업명', '마감일', '예상비용', '소요기간'])

        for assignee, tasks in distribution.items():
            for task in tasks:
                writer.writerow([
                    assignee,
                    task.get('regulation_name', ''),
                    task.get('task_name', ''),
                    task.get('deadline', ''),
                    task.get('estimated_cost', ''),
                    task.get('estimated_time', '')
                ])

    print(f"✅ CSV 파일 저장: {output_path}")


def export_distribution_to_json(distribution: Dict[str, List[Dict[str, Any]]], output_path: str):
    """분배 결과를 JSON으로 내보내기"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(distribution, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON 파일 저장: {output_path}")
