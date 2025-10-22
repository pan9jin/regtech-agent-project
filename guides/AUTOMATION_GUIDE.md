# 워크플로우 자동화 가이드

## 개요

규제 준수 프로세스를 **최대한 자동화**하여 담당자의 수작업을 최소화하는 시스템입니다.

### 자동화 범위

```
┌─────────────────────────────────────────────────────────┐
│                   규제 분석 자동화                        │
│                                                           │
│  1. 규제 검색 → 2. 분류 → 3. 체크리스트 생성             │
│       ↓              ↓              ↓                    │
│    자동화         자동화         자동화                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              담당자 할당 및 알림 자동화                   │
│                                                           │
│  1. 담당자 자동 배정 → 2. 이메일 발송 → 3. 진행 모니터링 │
│       ↓                    ↓                 ↓           │
│    자동화 (AI)          자동화            자동화          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│           워크플로우 자동화 (n8n/Make.com)               │
│                                                           │
│  • Task 자동 실행     • 일정 기반 리마인더                │
│  • 상태 모니터링      • Slack/Teams 알림                 │
│  • Google Calendar    • 문서 자동 생성                   │
└─────────────────────────────────────────────────────────┘
```

## 1. 이메일 자동 발송

### 1.1 기본 사용법

```python
from utils.email_sender import EmailSender

# 이메일 발송기 초기화
sender = EmailSender(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",  # 또는 환경변수 EMAIL_USERNAME
    password="your-app-password"       # 또는 환경변수 EMAIL_PASSWORD
)

# 체크리스트 발송
sender.send_checklist_to_assignee(
    assignee_email="safety@company.com",
    assignee_name="안전관리팀",
    regulation_name="화학물질관리법",
    checklist_items=[
        {
            "task_name": "안전관리계획서 작성",
            "responsible_dept": "안전관리팀",
            "deadline": "2025-11-30",
            "estimated_cost": "2,000,000원",
            "estimated_time": "2주"
        }
    ],
    pdf_path="regulation_report.pdf"  # 선택
)
```

### 1.2 환경변수 설정

```bash
# .env 파일 생성
export EMAIL_USERNAME="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"  # Gmail 앱 비밀번호

# Gmail 앱 비밀번호 생성 방법:
# 1. Google 계정 > 보안 > 2단계 인증 활성화
# 2. 앱 비밀번호 생성
# 3. 생성된 16자리 비밀번호 사용
```

### 1.3 담당자별 자동 발송

```python
from utils.email_sender import send_checklists_by_assignee

# 담당자 이메일 매핑
assignee_contacts = {
    "안전관리팀": "safety@company.com",
    "환경관리팀": "environment@company.com",
    "규제준수팀": "compliance@company.com"
}

# 체크리스트 데이터 (JSON에서 로드)
import json
with open('regulation_analysis_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 자동 발송
results = send_checklists_by_assignee(
    checklists=data['checklists'],
    assignee_contacts=assignee_contacts,
    pdf_path="regulation_report.pdf"
)

# 결과 확인
for assignee, success in results.items():
    print(f"{'✅' if success else '❌'} {assignee}")
```

## 2. 담당자 자동 배정

### 2.1 AI 기반 자동 배정

```python
from utils.task_distributor import TaskDistributor, DEFAULT_ASSIGNEE_CONFIG

# 분배기 초기화
distributor = TaskDistributor(DEFAULT_ASSIGNEE_CONFIG)

# 체크리스트 자동 분배
distribution = distributor.distribute_checklists(
    checklists=data['checklists'],
    auto_assign=True  # AI 기반 자동 할당
)

# 결과 확인
for assignee, tasks in distribution.items():
    print(f"{assignee}: {len(tasks)}개 작업")
```

### 2.2 담당자 설정 커스터마이징

```python
# 회사별 담당자 설정
custom_config = {
    "안전관리팀": {
        "email": "safety@mycompany.com",
        "manager": "김철수",
        "specialties": ["화학물질", "안전", "위험물"],  # 전문 분야
        "max_tasks": 15  # 최대 업무량
    },
    "환경관리팀": {
        "email": "env@mycompany.com",
        "manager": "이영희",
        "specialties": ["환경", "배출", "폐기물"],
        "max_tasks": 12
    }
}

distributor = TaskDistributor(custom_config)
```

### 2.3 원스톱 자동화

```python
from utils.task_distributor import auto_distribute_and_send

# 분배 + 이메일 발송 한번에 처리
result = auto_distribute_and_send(
    checklists=data['checklists'],
    assignee_config=custom_config,  # 생략 시 기본 설정 사용
    send_emails=True  # 자동으로 이메일 발송
)

print(f"총 {result['report']['total_tasks']}개 작업을 {result['report']['total_assignees']}명에게 분배")
print(f"이메일 발송: {result['emails_sent']}건")
print(f"업무 균형: {result['report']['workload_balance']}")
```

## 3. 워크플로우 자동화 도구 연동

### 3.1 n8n 연동

#### 설치 및 실행

```bash
# n8n 설치 (Docker)
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# 브라우저에서 http://localhost:5678 접속
```

#### Workflow 예시 1: 체크리스트 자동 이메일 발송

```yaml
이름: 규제 분석 완료 → 자동 이메일 발송

Nodes:
  1. Webhook Trigger
     - URL: http://your-server/api/webhook/trigger
     - Method: POST

  2. HTTP Request (규제 데이터 조회)
     - URL: http://your-server/api/regulation/{{$json.regulation_id}}
     - Method: GET

  3. Function (담당자별 그룹핑)
     - Code:
       const checklists = $input.item.json.checklists;
       const byAssignee = {};

       checklists.forEach(checklist => {
         checklist.items.forEach(item => {
           const assignee = item.responsible_dept;
           if (!byAssignee[assignee]) {
             byAssignee[assignee] = [];
           }
           byAssignee[assignee].push(item);
         });
       });

       return Object.entries(byAssignee).map(([assignee, tasks]) => ({
         json: { assignee, tasks }
       }));

  4. Email (각 담당자에게 발송)
     - To: {{$json.assignee_email}}
     - Subject: [규제 준수] 체크리스트 알림
     - Body: (HTML 템플릿)
```

#### Workflow 예시 2: 일정 기반 리마인더

```yaml
이름: 매일 오전 9시 마감 임박 알림

Nodes:
  1. Cron Trigger
     - Schedule: 0 9 * * *  # 매일 오전 9시

  2. HTTP Request (마감 임박 작업 조회)
     - URL: http://your-server/api/tasks/due-soon?days=7
     - Method: GET

  3. IF (조건 분기)
     - Condition: {{$json.tasks.length > 0}}

  4. Slack Message
     - Channel: #규제준수
     - Message:
       :warning: 다음 주 마감 작업이 {{$json.tasks.length}}개 있습니다.

       {{$json.tasks.map(t => `• ${t.task_name} (마감: ${t.deadline})`).join('\n')}}
```

#### 설정 가이드 조회

```bash
# API 서버 실행 후
curl http://localhost:8000/api/webhook/config/n8n
```

### 3.2 Make.com 연동

#### Scenario 예시 1: 규제 분석 → 이메일 자동 발송

```
Modules:
  1. Webhooks > Custom Webhook
     - URL: https://hook.us1.make.com/your-webhook-id

  2. HTTP > Make a Request
     - URL: http://your-server/api/webhook/make/send-checklist
     - Method: POST
     - Body:
       {
         "regulation_name": "{{regulation_name}}",
         "assignee_email": "{{assignee_email}}",
         "assignee_name": "{{assignee_name}}",
         "checklist_items": {{checklist_items}}
       }

  3. Gmail > Send an Email
     - To: {{assignee_email}}
     - Subject: [규제 준수] 체크리스트
     - Content: (HTML 템플릿)

  4. Google Sheets > Add a Row
     - Spreadsheet: 규제 준수 추적
     - Values: {{regulation_name}}, {{assignee}}, {{date}}
```

#### Scenario 예시 2: Slack 알림

```
Modules:
  1. Schedule > Every Day
     - Time: 09:00

  2. HTTP > Make a Request
     - URL: http://your-server/api/workflow/status/all
     - Method: GET

  3. Iterator
     - Array: {{workflows}}

  4. Slack > Create a Message
     - Channel: #규제준수
     - Text:
       워크플로우 상태 업데이트
       • 규제: {{item.regulation_name}}
       • 진행률: {{item.progress}}%
       • 담당자: {{item.assignee}}
```

#### 설정 가이드 조회

```bash
curl http://localhost:8000/api/webhook/config/make
```

### 3.3 Google Apps Script 연동 (간단한 자동화)

```javascript
// Google Sheets에서 실행되는 스크립트
function sendWeeklyReport() {
  // 1. 규제 API에서 데이터 조회
  const response = UrlFetchApp.fetch('http://your-server/api/regulations/summary');
  const data = JSON.parse(response.getContentText());

  // 2. Google Sheets에 기록
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('규제 현황');
  const lastRow = sheet.getLastRow();

  sheet.getRange(lastRow + 1, 1, 1, 4).setValues([[
    new Date(),
    data.total_regulations,
    data.pending_tasks,
    data.completed_tasks
  ]]);

  // 3. 이메일 발송
  if (data.pending_tasks > 10) {
    GmailApp.sendEmail(
      'manager@company.com',
      '주간 규제 준수 리포트',
      `미완료 작업: ${data.pending_tasks}개`
    );
  }
}

// 트리거 설정: 매주 월요일 오전 9시
```

## 4. API 서버 실행

### 4.1 FastAPI 서버 시작

```python
# api/main.py 생성
from fastapi import FastAPI
from api.webhook_api import router as webhook_router
from api.workflow_api import router as workflow_router

app = FastAPI(title="규제 준수 자동화 API")

app.include_router(webhook_router, prefix="/api", tags=["webhook"])
app.include_router(workflow_router, prefix="/api", tags=["workflow"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

```bash
# 실행
python api/main.py

# 또는 uvicorn 직접 실행
uvicorn api.main:app --reload --port 8000

# API 문서 확인
# http://localhost:8000/docs
```

### 4.2 주요 엔드포인트

| 엔드포인트 | 메소드 | 설명 |
|-----------|--------|------|
| `/api/webhook/trigger` | POST | 범용 Webhook 트리거 |
| `/api/webhook/n8n/task-automation` | POST | n8n 태스크 자동화 |
| `/api/webhook/make/send-checklist` | POST | Make.com 체크리스트 발송 |
| `/api/webhook/workflow/status-update` | POST | 워크플로우 상태 업데이트 |
| `/api/webhook/config/n8n` | GET | n8n 설정 가이드 |
| `/api/webhook/config/make` | GET | Make.com 설정 가이드 |

## 5. 완전 자동화 시나리오

### 시나리오 A: 신규 사업 규제 분석 완전 자동화

```
1. 사용자: 사업 정보 입력 (Web UI)
   ↓
2. AI Agent: 규제 검색 및 분석 (자동)
   ↓
3. AI Agent: 체크리스트 생성 (자동)
   ↓
4. AI Agent: 담당자 자동 배정 (자동)
   ↓
5. 시스템: PDF 보고서 생성 (자동)
   ↓
6. 시스템: 각 담당자에게 이메일 발송 (자동)
   ↓
7. n8n/Make: Google Calendar에 일정 추가 (자동)
   ↓
8. n8n/Make: Slack/Teams 알림 발송 (자동)
   ↓
9. 담당자: 이메일 확인 및 작업 시작 (수작업)
```

**자동화율: 88% (9단계 중 8단계 자동화)**

### 시나리오 B: 일일 모니터링 및 리마인더

```
[매일 오전 9시 자동 실행]

1. n8n Cron: 트리거 실행 (자동)
   ↓
2. API: 미완료 작업 조회 (자동)
   ↓
3. API: 마감 임박 작업 필터링 (자동)
   ↓
4. n8n: Slack 채널에 알림 발송 (자동)
   ↓
5. n8n: 담당자에게 개별 이메일 발송 (자동)
   ↓
6. 담당자: 이메일 확인 및 조치 (수작업)
```

**자동화율: 83% (6단계 중 5단계 자동화)**

## 6. 모범 사례

### 6.1 이메일 발송 모범 사례

```python
# ✅ Good: 환경변수 사용
sender = EmailSender()  # 환경변수에서 자동 로드

# ❌ Bad: 하드코딩
sender = EmailSender(username="email@example.com", password="password123")
```

### 6.2 담당자 설정 모범 사례

```python
# ✅ Good: JSON 파일로 관리
import json
with open('assignee_config.json', 'r') as f:
    config = json.load(f)

distributor = TaskDistributor(config)

# ❌ Bad: 코드에 하드코딩
```

### 6.3 Webhook 보안 모범 사례

```python
# ✅ Good: Secret 검증
@router.post("/webhook/trigger")
async def trigger(request: Request, x_webhook_secret: str = Header(...)):
    if x_webhook_secret != os.getenv("WEBHOOK_SECRET"):
        raise HTTPException(401, "Unauthorized")
    # ...

# ❌ Bad: 인증 없음
```

## 7. 문제 해결

### 7.1 이메일 발송 실패

```
문제: "SMTPAuthenticationError: Username and Password not accepted"

해결:
1. Gmail 2단계 인증 활성화 확인
2. 앱 비밀번호 재생성
3. 환경변수 EMAIL_USERNAME, EMAIL_PASSWORD 확인
4. SMTP 포트 확인 (Gmail: 587)
```

### 7.2 n8n Webhook 연결 실패

```
문제: "Connection timed out"

해결:
1. API 서버가 실행 중인지 확인
2. 방화벽 설정 확인
3. ngrok 등으로 로컬 서버 외부 노출:
   ngrok http 8000
4. n8n에 ngrok URL 입력
```

### 7.3 담당자 자동 배정 실패

```
문제: 모든 작업이 "미지정"으로 분류됨

해결:
1. assignee_config에 specialties 키워드 확인
2. 규제명/작업명과 키워드 매칭 여부 확인
3. 로그 출력하여 디버깅:
   print(f"Task: {task_name}, Scores: {keyword_scores}")
```

## 8. 다음 단계

### Phase 2: 고급 자동화

- [ ] Google Calendar API 연동
- [ ] Jira/Asana 태스크 자동 생성
- [ ] Microsoft Teams 연동
- [ ] 자동 리포트 생성 (주간/월간)

### Phase 3: AI 고도화

- [ ] 담당자 추천 AI 모델 학습
- [ ] 마감일 자동 예측
- [ ] 리스크 자동 평가 고도화

## 9. 참고 자료

- [n8n 공식 문서](https://docs.n8n.io/)
- [Make.com 공식 문서](https://www.make.com/en/help)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Gmail API 가이드](https://developers.google.com/gmail/api)
