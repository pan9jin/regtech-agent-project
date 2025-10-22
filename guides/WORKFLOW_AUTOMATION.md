# 워크플로우 자동화 시스템 설계

## 개요
규제 준수 프로세스를 "Task 정의 → Task 자동화 → 담당자 수작업 최소화"로 구성하여
체크리스트를 실행 가능한 워크플로우로 전환합니다.

---

## 핵심 컨셉

### 현재 시스템 (Before)
```
사업 정보 입력 → AI 분석 → 규제 목록 + 체크리스트 출력
                                    ↓
                            담당자가 수동으로 실행
```

### 자동화 시스템 (After)
```
사업 정보 입력 → AI 분석 → 규제 목록 + 워크플로우 생성
                                    ↓
                            자동 실행 가능한 Task들
                            - 자동 처리: 문서 생성, 신청서 작성
                            - 반자동: 승인 요청, 알림
                            - 수동: 사람 판단 필요한 항목만
```

---

## 시스템 구조

### 1. Task 분류 체계

```python
class TaskType(str, Enum):
    AUTOMATED = "automated"      # 완전 자동화 가능
    SEMI_AUTO = "semi_auto"      # 사람 승인 후 자동 실행
    MANUAL = "manual"            # 사람이 직접 수행
    MONITORING = "monitoring"    # 자동 모니터링 + 알림

class TaskStatus(str, Enum):
    PENDING = "pending"          # 대기 중
    IN_PROGRESS = "in_progress"  # 진행 중
    WAITING_APPROVAL = "waiting_approval"  # 승인 대기
    COMPLETED = "completed"      # 완료
    FAILED = "failed"            # 실패
    SKIPPED = "skipped"          # 건너뜀
```

### 2. 워크플로우 Task 모델

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class WorkflowTask(BaseModel):
    """워크플로우 Task 정의"""
    id: str
    regulation_id: str
    regulation_name: str

    # Task 기본 정보
    task_name: str
    task_type: TaskType
    priority: Priority

    # 실행 정보
    responsible_dept: str
    responsible_person: Optional[str] = None
    deadline: datetime

    # 자동화 설정
    automation_config: Dict[str, Any]  # 자동화 실행 설정
    prerequisites: List[str] = []      # 선행 Task ID들

    # 상태 관리
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0              # 진행률 (0-100)

    # 실행 결과
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    # 메타데이터
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 비용/시간
    estimated_cost: int
    estimated_time_hours: int
    actual_cost: Optional[int] = None
    actual_time_hours: Optional[int] = None
```

---

## 자동화 가능한 Task 유형

### Type 1: AUTOMATED (완전 자동화)

#### 1.1 문서 자동 생성
```python
automation_config = {
    "type": "document_generation",
    "template": "chemical_permit_application",
    "data_source": "business_info",
    "output_format": "pdf",
    "auto_submit": False  # 생성만 하고 제출은 승인 필요
}

# 예시: 화학물질 영업허가 신청서 자동 작성
task = WorkflowTask(
    task_name="화학물질 영업허가 신청서 작성",
    task_type=TaskType.AUTOMATED,
    automation_config={
        "type": "document_generation",
        "template_id": "chem_permit_001",
        "fields": {
            "company_name": "{{business_info.company_name}}",
            "address": "{{business_info.address}}",
            "materials": "{{business_info.raw_materials}}",
            "processes": "{{business_info.processes}}"
        },
        "attachments": ["business_license", "facility_certificate"]
    }
)
```

#### 1.2 데이터 수집 및 체크
```python
automation_config = {
    "type": "data_collection",
    "checks": [
        {"field": "employee_count", "condition": ">= 50", "alert": True},
        {"field": "hazardous_materials", "exists": True, "required": ["MSDS"]},
    ],
    "auto_notify": True
}
```

#### 1.3 일정 관리 및 알림
```python
automation_config = {
    "type": "schedule_management",
    "reminders": [
        {"days_before": 30, "notify": ["responsible_person", "manager"]},
        {"days_before": 7, "notify": ["responsible_person", "manager", "ceo"]},
        {"days_before": 1, "notify": ["all"], "urgent": True}
    ],
    "auto_create_calendar_event": True
}
```

### Type 2: SEMI_AUTO (반자동화)

#### 2.1 승인 후 자동 제출
```python
automation_config = {
    "type": "approval_workflow",
    "steps": [
        {"step": 1, "action": "generate_document", "auto": True},
        {"step": 2, "action": "request_approval", "approver": "legal_team"},
        {"step": 3, "action": "submit_to_agency", "auto": True, "after_approval": True}
    ],
    "approval_timeout_hours": 48,
    "escalation": "manager"
}
```

#### 2.2 외부 시스템 연동
```python
automation_config = {
    "type": "external_integration",
    "system": "government_portal",
    "action": "submit_application",
    "credentials": "stored_securely",
    "require_2fa": True,  # 2단계 인증 필요
    "human_verification": True
}
```

### Type 3: MANUAL (수동 작업)

```python
automation_config = {
    "type": "manual_task",
    "guidance": {
        "steps": [
            "1. 화학물질안전원 방문 (예약 필요)",
            "2. 시설 현장 점검 받기",
            "3. 적합 확인서 수령"
        ],
        "tips": ["예약은 최소 2주 전에 진행", "시설 청소 미리 완료"],
        "contacts": [
            {"name": "화학물질안전원 고객센터", "phone": "1234-5678"}
        ]
    },
    "evidence_required": ["photo", "certificate"],
    "completion_check": "manager_approval"
}
```

### Type 4: MONITORING (모니터링)

```python
automation_config = {
    "type": "continuous_monitoring",
    "monitor": [
        {"metric": "regulation_changes", "source": "government_api", "frequency": "daily"},
        {"metric": "deadline_approaching", "check": "weekly"},
        {"metric": "compliance_status", "check": "monthly"}
    ],
    "alerts": {
        "regulation_change": {"notify": "immediately", "channels": ["email", "slack"]},
        "deadline_near": {"notify": "7_days_before", "channels": ["email"]},
    }
}
```

---

## 워크플로우 엔진 구현

### 1. Workflow Orchestrator

```python
from typing import List, Dict
import asyncio
from datetime import datetime

class WorkflowOrchestrator:
    """워크플로우 실행 엔진"""

    def __init__(self):
        self.tasks: Dict[str, WorkflowTask] = {}
        self.executors = {
            TaskType.AUTOMATED: AutomatedTaskExecutor(),
            TaskType.SEMI_AUTO: SemiAutoTaskExecutor(),
            TaskType.MANUAL: ManualTaskGuide(),
            TaskType.MONITORING: MonitoringService()
        }

    async def execute_workflow(self, regulation_id: str) -> Dict[str, Any]:
        """워크플로우 실행"""
        tasks = self.get_tasks_by_regulation(regulation_id)

        # Topological sort (선행 Task 고려)
        execution_order = self.topological_sort(tasks)

        results = []
        for task in execution_order:
            # 선행 Task 완료 확인
            if not self.check_prerequisites(task):
                task.status = TaskStatus.WAITING
                continue

            # Task 실행
            executor = self.executors[task.task_type]
            result = await executor.execute(task)

            results.append({
                "task_id": task.id,
                "status": task.status,
                "result": result
            })

        return {
            "regulation_id": regulation_id,
            "total_tasks": len(tasks),
            "completed": len([r for r in results if r["status"] == TaskStatus.COMPLETED]),
            "results": results
        }

    def topological_sort(self, tasks: List[WorkflowTask]) -> List[WorkflowTask]:
        """Task 의존성에 따른 실행 순서 결정"""
        # DAG 기반 정렬
        # ... implementation
        pass
```

### 2. Automated Task Executor

```python
class AutomatedTaskExecutor:
    """완전 자동화 Task 실행"""

    async def execute(self, task: WorkflowTask) -> Dict[str, Any]:
        """Task 자동 실행"""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        try:
            config = task.automation_config

            if config["type"] == "document_generation":
                result = await self.generate_document(task, config)

            elif config["type"] == "data_collection":
                result = await self.collect_data(task, config)

            elif config["type"] == "schedule_management":
                result = await self.manage_schedule(task, config)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            task.result = result

            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            return {"error": str(e)}

    async def generate_document(self, task: WorkflowTask, config: Dict) -> Dict:
        """문서 자동 생성"""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4")

        prompt = f"""
        다음 정보로 {config['template_id']} 문서를 작성하세요:

        회사명: {config['fields']['company_name']}
        주소: {config['fields']['address']}
        원자재: {config['fields']['materials']}

        공식 신청서 양식에 맞게 작성해주세요.
        """

        response = llm.invoke(prompt)

        # PDF 생성
        pdf_path = self.create_pdf(response.content)

        return {
            "document_path": pdf_path,
            "content": response.content,
            "timestamp": datetime.now().isoformat()
        }
```

### 3. Semi-Auto Task Executor

```python
class SemiAutoTaskExecutor:
    """반자동 Task 실행 (승인 필요)"""

    async def execute(self, task: WorkflowTask) -> Dict[str, Any]:
        """반자동 Task 실행"""
        config = task.automation_config

        if config["type"] == "approval_workflow":
            return await self.run_approval_workflow(task, config)

    async def run_approval_workflow(self, task: WorkflowTask, config: Dict) -> Dict:
        """승인 워크플로우 실행"""
        for step_config in config["steps"]:
            step_num = step_config["step"]
            action = step_config["action"]

            if step_config.get("auto", False):
                # 자동 실행
                if action == "generate_document":
                    result = await self.generate_document(task)
                elif action == "submit_to_agency":
                    result = await self.submit_to_agency(task)
            else:
                # 승인 요청
                task.status = TaskStatus.WAITING_APPROVAL
                approval_result = await self.request_approval(
                    task,
                    step_config["approver"]
                )

                if not approval_result["approved"]:
                    task.status = TaskStatus.FAILED
                    return {"error": "Approval denied"}

        task.status = TaskStatus.COMPLETED
        return {"success": True}

    async def request_approval(self, task: WorkflowTask, approver: str) -> Dict:
        """승인 요청 전송"""
        # 이메일/슬랙 알림
        # 승인 링크 생성
        # 대기...
        approval_link = f"https://app.regtech.com/approve/{task.id}"

        # 알림 전송
        await self.send_notification(
            to=approver,
            subject=f"승인 요청: {task.task_name}",
            message=f"다음 Task에 대한 승인이 필요합니다.\n{approval_link}"
        )

        # 실제로는 비동기 대기, 여기서는 시뮬레이션
        return {"approved": True, "approver": approver, "timestamp": datetime.now()}
```

---

## 대시보드 및 모니터링

### 1. 실시간 진행 상황 대시보드

```python
class WorkflowDashboard:
    """워크플로우 대시보드"""

    def get_overview(self, company_id: str) -> Dict:
        """전체 현황"""
        return {
            "total_regulations": 15,
            "total_tasks": 45,
            "completed": 12,
            "in_progress": 8,
            "waiting_approval": 3,
            "pending": 22,
            "automation_rate": "73%",  # 자동화 가능 비율
            "estimated_completion": "2025-11-15",
            "cost_saved": "약 3,500만원 (자동화로 절감)"
        }

    def get_task_timeline(self) -> List[Dict]:
        """Timeline 뷰"""
        return [
            {
                "date": "2025-10-22",
                "tasks": [
                    {"name": "화학물질 신고서 생성", "status": "completed", "type": "automated"},
                    {"name": "시설 점검 예약", "status": "in_progress", "type": "manual"}
                ]
            },
            # ...
        ]
```

### 2. 알림 시스템

```python
class NotificationService:
    """알림 서비스"""

    async def send_task_reminder(self, task: WorkflowTask):
        """Task 알림 전송"""
        if task.deadline - datetime.now() <= timedelta(days=7):
            await self.send_email(
                to=task.responsible_person,
                subject=f"⚠️ 마감 임박: {task.task_name}",
                body=f"""
                안녕하세요,

                다음 Task의 마감이 7일 남았습니다:

                Task: {task.task_name}
                마감일: {task.deadline.strftime('%Y-%m-%d')}
                우선순위: {task.priority}

                지금 확인하기: https://app.regtech.com/tasks/{task.id}
                """
            )
```

---

## API 엔드포인트 추가

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/api/workflow/start")
async def start_workflow(
    regulation_id: str,
    background_tasks: BackgroundTasks
):
    """워크플로우 시작"""
    orchestrator = WorkflowOrchestrator()

    # 백그라운드에서 실행
    background_tasks.add_task(
        orchestrator.execute_workflow,
        regulation_id
    )

    return {"status": "started", "regulation_id": regulation_id}

@app.get("/api/workflow/status/{regulation_id}")
async def get_workflow_status(regulation_id: str):
    """워크플로우 상태 조회"""
    orchestrator = WorkflowOrchestrator()
    status = orchestrator.get_status(regulation_id)

    return status

@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, approved: bool, comment: str = ""):
    """Task 승인/거부"""
    # ... 승인 처리
    return {"task_id": task_id, "approved": approved}

@app.get("/api/dashboard/overview")
async def get_dashboard_overview(company_id: str):
    """대시보드 개요"""
    dashboard = WorkflowDashboard()
    return dashboard.get_overview(company_id)
```

---

## 사용 시나리오

### Scenario 1: 화학물질 영업허가 워크플로우

```
1. [AUTOMATED] 신청서 자동 작성 (5분)
   → GPT-4가 사업 정보 기반으로 신청서 작성
   → PDF 생성 및 첨부 파일 준비

2. [SEMI_AUTO] 법무팀 검토 요청 (2일)
   → 자동으로 법무팀에 검토 요청 알림
   → 승인 링크 제공

3. [SEMI_AUTO] 전자 제출 (10분)
   → 승인 후 자동으로 화학물질안전원 포털에 제출
   → 접수 번호 자동 저장

4. [MONITORING] 진행 상황 추적
   → 매일 정부 포털 확인
   → 승인 시 자동 알림

총 소요 시간: 2일 (기존 2주 → 90% 단축)
담당자 작업 시간: 1시간 (승인 검토만)
```

### Scenario 2: 정기 안전교육

```
1. [AUTOMATED] 교육 일정 생성 (즉시)
   → 연 1회 반복 일정 자동 생성
   → 3개월 전 알림 설정

2. [AUTOMATED] 교육 기관 예약 (1일)
   → API 연동으로 자동 예약
   → 확정 시 참석자에게 알림

3. [MANUAL] 교육 참석 (1일)
   → 담당자가 직접 참석

4. [AUTOMATED] 이수증 업로드 및 기록 (즉시)
   → OCR로 이수증 자동 인식
   → 시스템에 자동 기록

담당자 작업: 교육 참석만 (1일)
자동화 비율: 75%
```

---

## 구현 우선순위

### Phase 1: 기본 자동화 (Week 1-2)
- ✅ 문서 자동 생성
- ✅ 일정 관리 및 알림
- ✅ 기본 대시보드

### Phase 2: 워크플로우 엔진 (Week 3-4)
- ✅ Task 의존성 관리
- ✅ 승인 워크플로우
- ✅ 외부 시스템 연동 (정부 포털 API)

### Phase 3: 고도화 (Week 5-6)
- ✅ AI 기반 문서 검토
- ✅ 실시간 모니터링
- ✅ 모바일 알림

---

## 예상 효과

| 항목 | Before | After | 개선율 |
|------|--------|-------|--------|
| 규제 파악 시간 | 2-3일 | 5분 | 99% ↓ |
| 문서 작성 시간 | 4시간 | 5분 | 98% ↓ |
| 신청 처리 시간 | 2주 | 2일 | 86% ↓ |
| 담당자 업무 시간 | 40시간 | 5시간 | 87% ↓ |
| 비용 절감 | - | 3,500만원/년 | - |

---

## 다음 단계

1. ✅ Workflow 모델 구현 (models/workflow.py)
2. ✅ Orchestrator 구현 (workflows/orchestrator.py)
3. ✅ Automated Executor 구현 (workflows/executors/)
4. ✅ Dashboard API 구현 (api/dashboard.py)
5. ✅ Frontend 대시보드 (Vue.js)
