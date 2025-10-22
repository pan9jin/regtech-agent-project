# 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1단계: 서버 실행

```bash
# 프로젝트 디렉토리로 이동
cd regtech-agent-project

# 서버 실행
python run_server.py
```

서버가 시작되면 다음과 같은 메시지가 표시됩니다:

```
============================================================
🚀 규제 준수 자동화 시스템 서버 시작
============================================================

📡 API 서버: http://localhost:8000
📚 API 문서: http://localhost:8000/docs
🌐 웹 UI:    http://localhost:8000
```

### 2단계: 웹 브라우저 접속

브라우저를 열고 다음 주소로 접속:

```
http://localhost:8000
```

### 3단계: 사업 정보 입력

"규제 분석" 탭에서 다음 정보를 입력:

- **업종**: 배터리 제조
- **제품명**: 리튬이온 배터리
- **주요 원자재**: 리튬, 코발트, 니켈
- **주요 공정**: 화학 처리, 고온 가공, 조립
- **직원 수**: 45
- **판매 채널**: B2B, 수출
- **수출 국가**: 미국, 유럽, 일본

### 4단계: 분석 시작

"분석 시작" 버튼을 클릭하고 진행 상황을 확인하세요.

```
규제 검색 중... (20%)
   ↓
규제 분류 중... (40%)
   ↓
체크리스트 생성 중... (60%)
   ↓
PDF 보고서 생성 중... (80%)
   ↓
분석 완료! (100%)
```

### 5단계: 결과 확인

"분석 결과" 탭에서:

- ✅ 적용 규제 목록 확인
- ✅ 우선순위 확인 (HIGH/MEDIUM/LOW)
- ✅ 체크리스트 확인
- ✅ PDF 보고서 다운로드
- ✅ 담당자별 체크리스트 발송

## 💡 더 빠른 방법: 데모 모드

샘플 데이터가 자동으로 입력되는 데모 모드:

```
http://localhost:8000?demo=1
```

→ "분석 시작" 버튼만 클릭하면 됩니다!

## 🔧 서버 관리

### 서버 상태 확인

```bash
curl http://localhost:8000/health
```

### 서버 중지

```bash
# 터미널에서 Ctrl+C

# 또는 PID로 종료
pkill -f run_server
```

### 서버 재시작

```bash
python run_server.py
```

## 📡 주요 URL

| URL | 설명 |
|-----|------|
| http://localhost:8000 | 웹 UI (메인) |
| http://localhost:8000/docs | API 문서 (Swagger) |
| http://localhost:8000/health | 헬스체크 |
| http://localhost:8000?demo=1 | 데모 모드 |

## 🎯 주요 기능

### 1. 규제 분석
- AI 기반 자동 규제 검색
- 8개 전문 Agent 활용
- 30초~2분 소요

### 2. 결과 시각화
- 우선순위별 색상 코딩
- 규제 정보 카드
- 체크리스트 그리드

### 3. PDF 다운로드
- 한글 지원
- 전문적인 레이아웃
- 원클릭 다운로드

### 4. 담당자 자동 배정
- AI 기반 자동 분배
- 이메일 자동 발송
- 업무 균형 조절

### 5. 대시보드
- 전체 통계
- 시스템 상태
- 실시간 업데이트

## 🐛 문제 해결

### Q: 서버가 시작되지 않아요

```bash
# 필요한 패키지 설치
pip install uvicorn fastapi httpx

# 다시 실행
python run_server.py
```

### Q: 포트 8000이 이미 사용 중이에요

```bash
# 다른 포트 사용 (예: 8080)
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

### Q: 분석이 실패해요

1. 환경변수 확인 (.env 파일)
   ```
   OPENAI_API_KEY=your-key
   TAVILY_API_KEY=your-key
   ```

2. 의존성 설치 확인
   ```bash
   pip install -r requirements.txt
   ```

### Q: PDF 다운로드가 안 돼요

1. reportlab 설치 확인
   ```bash
   pip install reportlab
   ```

2. 분석 완료 여부 확인
   - "분석 결과" 탭 확인
   - 100% 완료되었는지 확인

## 📚 더 알아보기

- **FRONTEND_GUIDE.md** - 웹 UI 상세 가이드
- **AUTOMATION_GUIDE.md** - 워크플로우 자동화
- **README.md** - 전체 시스템 개요
- **PDF_REPORT_GUIDE.md** - PDF 보고서 가이드

## 🎉 다음 단계

1. **이메일 설정**
   - .env 파일에 EMAIL_USERNAME, EMAIL_PASSWORD 설정
   - 담당자 이메일 자동 발송 활성화

2. **워크플로우 자동화**
   - n8n 또는 Make.com 연동
   - AUTOMATION_GUIDE.md 참고

3. **커스터마이징**
   - 담당자 설정 수정 (utils/task_distributor.py)
   - UI 색상 변경 (frontend/css/styles.css)

---

**문의사항이 있으시면 README.md를 참고하세요!**
