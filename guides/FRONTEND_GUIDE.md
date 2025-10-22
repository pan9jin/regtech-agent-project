## Frontend 웹 애플리케이션 가이드

## 개요

규제 준수 자동화 시스템의 **웹 UI**입니다. 사용자 친화적인 인터페이스로 규제 분석을 쉽게 수행할 수 있습니다.

### 주요 기능

- ✅ **직관적인 규제 분석 폼**: 사업 정보 입력
- ✅ **실시간 진행 상황 표시**: 분석 단계별 진행률
- ✅ **분석 결과 시각화**: 규제 목록, 체크리스트 표시
- ✅ **PDF 다운로드**: 원클릭 보고서 다운로드
- ✅ **대시보드**: 전체 통계 및 시스템 상태
- ✅ **담당자 자동 배정**: 체크리스트 이메일 발송

## 실행 방법

### 1. API 서버 실행

```bash
# 프로젝트 루트에서
python api/main.py

# 또는 uvicorn 사용
uvicorn api.main:app --reload --port 8000
```

### 2. 브라우저에서 접속

```
http://localhost:8000
```

### 3. API 문서 확인 (선택)

```
http://localhost:8000/docs
```

## 화면 구성

### 1. 규제 분석 탭

#### 사업 정보 입력 폼

- **업종** (필수): 예) 배터리 제조
- **제품명** (필수): 예) 리튬이온 배터리
- **주요 원자재** (필수): 예) 리튬, 코발트, 니켈
- **주요 공정** (필수): 예) 화학 처리, 고온 가공, 조립
- **직원 수** (필수): 예) 45
- **판매 채널** (필수): 예) B2B, 수출
- **수출 국가** (선택): 예) 미국, 유럽, 일본
- **이메일 자동 발송** (체크박스): 분석 완료 후 담당자에게 이메일 발송

#### 진행 상황 표시

분석 중에는 다음과 같은 단계가 표시됩니다:

```
규제 검색 중... (20%)
    ↓
규제 분류 중... (40%)
    ↓
체크리스트 생성 중... (60%)
    ↓
PDF 보고서 생성 중... (80%)
    ↓
최종 검토 중... (95%)
    ↓
분석 완료! (100%)
```

### 2. 분석 결과 탭

#### 분석 요약

- 분석 ID
- 적용 규제 수
- 체크리스트 항목 수
- 총 예상 비용
- 리스크 점수

#### 적용 규제 목록

각 규제마다 다음 정보가 표시됩니다:

- **규제명**: 화학물질관리법 등
- **우선순위**: HIGH (빨강), MEDIUM (주황), LOW (초록)
- **카테고리**: 환경·안전 등
- **관할 기관**: 환경부 등
- **적용 이유**: 왜 이 규제가 적용되는지

#### 실행 체크리스트

규제별로 그룹핑된 체크리스트:

- [ ] 작업명
- 담당 부서
- 마감일
- 예상 비용

#### 액션 버튼

- **📄 PDF 보고서 다운로드**: 전체 분석 결과를 PDF로 다운로드
- **📧 담당자별 체크리스트 발송**: AI가 자동으로 담당자를 배정하고 이메일 발송

### 3. 대시보드 탭

#### 통계 카드

- **총 분석 수**: 지금까지 수행된 분석 건수
- **발견된 규제**: 총 규제 수
- **생성된 체크리스트**: 총 체크리스트 항목 수
- **자동화율**: 88% (고정)

#### 시스템 상태

- 규제 분석 엔진: ✅ 정상
- 이메일 자동화: ✅ 정상
- 담당자 배정 AI: ✅ 정상
- Webhook API: ✅ 정상

## 기술 스택

### Frontend

- **HTML5**: 시맨틱 마크업
- **CSS3**: 반응형 디자인, 그라데이션, 애니메이션
- **Vanilla JavaScript**: 프레임워크 없는 순수 JS
- **Fetch API**: 백엔드 API 통신

### Backend

- **FastAPI**: 고성능 Python 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **CORS**: 크로스 오리진 요청 지원

## API 엔드포인트

### POST /api/analyze

규제 분석 실행

**Request:**
```json
{
  "industry": "배터리 제조",
  "product_name": "리튬이온 배터리",
  "raw_materials": "리튬, 코발트, 니켈",
  "processes": ["화학 처리", "고온 가공"],
  "employee_count": 45,
  "sales_channels": ["B2B", "수출"],
  "export_countries": ["미국", "유럽"]
}
```

**Query Parameters:**
- `send_emails` (boolean): 이메일 자동 발송 여부

**Response:**
```json
{
  "status": "completed",
  "analysis_id": "abc123",
  "summary": {...},
  "regulations": [...],
  "checklists": [...],
  "pdf_path": "analysis_abc123.pdf"
}
```

### GET /api/analysis/{analysis_id}

분석 결과 조회

**Response:**
전체 분석 결과 JSON

### GET /api/download/{analysis_id}

PDF 다운로드

**Response:**
PDF 파일 (application/pdf)

### POST /api/distribute

체크리스트 담당자별 분배

**Query Parameters:**
- `analysis_id` (string): 분석 ID
- `send_emails` (boolean): 이메일 발송 여부

**Response:**
```json
{
  "status": "completed",
  "distribution": {...},
  "report": {...},
  "emails_sent": 3
}
```

### GET /api/stats

전체 통계 조회

**Response:**
```json
{
  "total_analyses": 10,
  "total_regulations": 50,
  "total_checklists": 120,
  "avg_regulations_per_analysis": 5.0,
  "avg_checklists_per_analysis": 12.0
}
```

### GET /health

헬스체크

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "features": {...}
}
```

## 파일 구조

```
frontend/
├── index.html              # 메인 HTML
├── css/
│   └── styles.css          # 전체 스타일시트
└── js/
    └── app.js              # 애플리케이션 로직

api/
└── main.py                 # FastAPI 백엔드
```

## 커스터마이징

### 1. 색상 변경

`frontend/css/styles.css`에서:

```css
/* 메인 그라데이션 */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* 원하는 색상으로 변경 */
background: linear-gradient(135deg, #your-color 0%, #your-color2 100%);
```

### 2. 폼 필드 추가

`frontend/index.html`에 폼 필드 추가:

```html
<div class="form-group">
    <label for="new_field">새 필드</label>
    <input type="text" id="new_field" name="new_field">
</div>
```

`frontend/js/app.js`에서 데이터에 추가:

```javascript
const data = {
    // ... 기존 필드
    new_field: formData.get('new_field')
};
```

### 3. 로고 추가

`frontend/index.html` 헤더에:

```html
<header class="header">
    <img src="/static/logo.png" alt="Logo" style="height: 50px;">
    <h1>규제 준수 자동화 시스템</h1>
</header>
```

## 데모 모드

URL에 `?demo=1`을 추가하면 샘플 데이터가 자동으로 입력됩니다:

```
http://localhost:8000?demo=1
```

## 프로덕션 배포

### 1. 환경변수 설정

```bash
export EMAIL_USERNAME="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export WEBHOOK_SECRET="your-secret-key"
```

### 2. Nginx 설정 (선택)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. SSL 인증서 (Let's Encrypt)

```bash
sudo certbot --nginx -d yourdomain.com
```

### 4. Systemd 서비스 (자동 시작)

```ini
[Unit]
Description=Regulation Compliance API
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/regtech-agent-project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable regtech-api
sudo systemctl start regtech-api
```

## 문제 해결

### 1. CORS 오류

`api/main.py`에서 CORS 설정 확인:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. 정적 파일이 로드되지 않음

- `frontend/` 디렉토리 경로 확인
- 브라우저 콘솔에서 404 오류 확인
- `api/main.py`의 `StaticFiles` 설정 확인

### 3. 분석이 너무 느림

- 백그라운드 태스크 사용:
  ```python
  background_tasks.add_task(run_workflow, business_info)
  ```
- 또는 Celery 사용 (비동기 작업 큐)

### 4. 이메일 발송 실패

- 환경변수 `EMAIL_USERNAME`, `EMAIL_PASSWORD` 확인
- Gmail 앱 비밀번호 사용 (2단계 인증 필요)
- SMTP 포트 확인 (587)

## 성능 최적화

### 1. 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_analysis(analysis_id: str):
    # ...
```

### 2. 압축

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 3. CDN

정적 파일을 CDN에서 서빙:

```html
<link rel="stylesheet" href="https://cdn.yoursite.com/css/styles.css">
```

## 다음 단계

### Phase 2: 고급 기능

- [ ] 사용자 인증 (로그인/회원가입)
- [ ] 분석 이력 관리
- [ ] 실시간 알림 (WebSocket)
- [ ] 차트 및 그래프 (Chart.js)
- [ ] 다크 모드

### Phase 3: 모바일 앱

- [ ] React Native 앱
- [ ] PWA (Progressive Web App)
- [ ] 푸시 알림

## 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [MDN Web Docs](https://developer.mozilla.org/)
- [CSS Tricks](https://css-tricks.com/)
