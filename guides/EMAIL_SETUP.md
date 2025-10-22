# 이메일 발송 기능 설정 가이드

## 📧 현재 상태

이메일 기능은 **테스트 모드**로 동작 중입니다. 실제 이메일 발송 없이 로그로만 확인됩니다.

### 테스트 모드에서 확인되는 정보:
- ✅ 수신자 이메일: eunsu0613@naver.com, woals424@naver.com
- ✅ 이메일 제목
- ✅ 첨부파일 여부
- ✅ 담당자별 체크리스트 분배

## 🔧 실제 이메일 발송 설정 방법

### 1. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```bash
# 이메일 발송 계정 정보
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

**주의**: Gmail을 사용하는 경우 **앱 비밀번호**를 사용해야 합니다!

### 2. Gmail 앱 비밀번호 생성 방법

1. Google 계정 관리 페이지로 이동
2. "보안" 섹션 클릭
3. "2단계 인증" 활성화 (필수)
4. "앱 비밀번호" 생성
5. 생성된 16자리 비밀번호를 `.env` 파일의 `EMAIL_PASSWORD`에 입력

### 3. 테스트 모드 비활성화

`utils/email_sender.py` 파일에서:

```python
def __init__(
    self,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    username: Optional[str] = None,
    password: Optional[str] = None,
    test_mode: bool = True  # ← 이 값을 False로 변경
):
```

또는 환경변수가 설정되어 있으면 자동으로 테스트 모드가 비활성화됩니다.

## 📨 수신자 설정

### 현재 설정된 담당자 이메일 (DEFAULT_ASSIGNEE_CONFIG)

| 담당팀 | 이메일 | 담당자 |
|--------|--------|--------|
| 안전관리팀 | eunsu0613@naver.com | 김은수 |
| 환경관리팀 | woals424@naver.com | 박재진 |
| 규제준수팀 | eunsu0613@naver.com | 김은수 |
| 품질관리팀 | woals424@naver.com | 박재진 |
| 법무팀 | eunsu0613@naver.com | 김은수 |
| 시설관리팀 | woals424@naver.com | 박재진 |
| 인사팀 | eunsu0613@naver.com | 김은수 |

### 수신자 변경 방법

`utils/task_distributor.py` 파일의 `DEFAULT_ASSIGNEE_CONFIG`를 수정:

```python
DEFAULT_ASSIGNEE_CONFIG = {
    "안전관리팀": {
        "email": "새로운이메일@example.com",  # ← 이메일 변경
        "manager": "담당자명",
        "specialties": ["화학물질", "안전", "위험", "사고", "보건"],
        "max_tasks": 15
    },
    # ...
}
```

## 🚀 사용 방법

### 1. 웹 UI에서 사용

1. http://localhost:8000?demo=1 접속
2. "분석 시작" 버튼 클릭하여 규제 분석 실행
3. "📧 담당자별 체크리스트 발송" 버튼 클릭
4. 각 담당자에게 자동으로 이메일 발송

### 2. API 직접 호출

```bash
# 분석 + 자동 이메일 발송
curl -X POST "http://localhost:8000/api/analyze?send_emails=true" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "배터리 제조",
    "product_name": "리튬이온 배터리",
    "raw_materials": "리튬, 코발트, 니켈",
    "processes": ["화학 처리", "고온 가공"],
    "employee_count": 45,
    "sales_channels": ["B2B", "수출"],
    "export_countries": ["미국", "유럽"]
  }'

# 기존 분석 결과로 이메일 발송
curl -X POST "http://localhost:8000/api/distribute?analysis_id=YOUR_ID&send_emails=true"
```

## 📝 이메일 내용

각 담당자에게 발송되는 이메일에는 다음 정보가 포함됩니다:

- **제목**: [규제 준수] {규제명} - 체크리스트 플래닝 결과
- **본문**:
  - 담당자명 인사말
  - 규제명 및 설명
  - 할당된 작업 목록 (작업명, 마감기한, 소요시간 등)
- **첨부**: PDF 보고서 (선택사항)

## 🔍 로그 확인

이메일 발송 로그는 `server.log` 파일에서 확인할 수 있습니다:

```bash
tail -f server.log | grep "📧"
```

### 테스트 모드 로그 예시:
```
📧 [테스트 모드] 이메일 발송 시뮬레이션
   수신: eunsu0613@naver.com
   제목: [규제 준수] IEC 61508 - 체크리스트 플래닝 결과
   첨부파일: 없음
   ✅ 이메일 발송 시뮬레이션 완료
```

### 실제 발송 로그 예시:
```
✅ 이메일 발송 성공: eunsu0613@naver.com
```

## ⚠️ 주의사항

1. **Gmail 일일 발송 제한**: 500건/일 (무료 계정 기준)
2. **네이버 메일**: 네이버는 외부 SMTP를 제한할 수 있으니 Gmail 사용 권장
3. **보안**: `.env` 파일은 절대 Git에 커밋하지 마세요!
4. **스팸 필터**: 대량 발송 시 스팸으로 분류될 수 있으니 주의

## 🐛 문제 해결

### 이메일이 발송되지 않을 때

1. `.env` 파일 확인
2. 앱 비밀번호가 올바른지 확인
3. 2단계 인증이 활성화되어 있는지 확인
4. 방화벽/보안 프로그램 확인
5. 서버 로그에서 에러 메시지 확인

### 테스트 모드 해제가 안 될 때

`utils/email_sender.py:35` 라인 확인:
```python
self.test_mode = test_mode or (not self.username or not self.password)
```

환경변수가 제대로 설정되어 있으면 자동으로 `test_mode=False`가 됩니다.
