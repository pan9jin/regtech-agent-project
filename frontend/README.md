# RegTech Assistant - Vue.js Frontend

Vue.js 3 기반 규제 준수 자동화 시스템 프론트엔드

## 기술 스택

- **Vue 3** (Composition API)
- **Vite** - 빌드 툴
- **Pinia** - 상태 관리
- **Vue Router** - 라우팅
- **Axios** - HTTP 클라이언트

## 프로젝트 구조

```
frontend/
├── src/
│   ├── api/               # API 클라이언트
│   │   ├── index.js       # Axios 인스턴스
│   │   └── endpoints.js   # API 엔드포인트 함수
│   ├── components/        # 재사용 가능한 컴포넌트
│   │   ├── AnalysisForm.vue
│   │   ├── ProgressBar.vue
│   │   ├── PriorityBadge.vue
│   │   ├── RegulationCard.vue
│   │   ├── ChecklistItem.vue
│   │   ├── StatsCard.vue
│   │   └── Modal.vue
│   ├── stores/            # Pinia 스토어
│   │   ├── analysis.js    # 분석 상태 관리
│   │   └── stats.js       # 통계 상태 관리
│   ├── views/             # 페이지 뷰
│   │   ├── AnalyzeView.vue
│   │   ├── ResultsView.vue
│   │   └── DashboardView.vue
│   ├── router/            # Vue Router 설정
│   │   └── index.js
│   ├── App.vue            # 루트 컴포넌트
│   └── main.js            # 앱 진입점
├── .env                   # 환경 변수
├── vite.config.js         # Vite 설정
└── package.json
```

## 환경 설정

1. **의존성 설치**
   ```bash
   npm install
   ```

2. **환경 변수 설정** (`.env` 파일)
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

## 개발 실행

```bash
npm run dev
```

개발 서버가 http://localhost:5173 에서 실행됩니다.

## 프로덕션 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다.

## 주요 기능

### 1. 규제 분석 탭 (`/analyze`)
- 사업 정보 입력 폼 (7개 필드)
- 이메일 발송 옵션
- 실시간 진행 상황 표시

### 2. 분석 결과 탭 (`/results`)
- 분석 요약 정보
- 우선순위 분포
- 규제 목록 (카테고리별)
- 실행 체크리스트
- PDF 다운로드
- 담당자별 체크리스트 분배

### 3. 대시보드 탭 (`/dashboard`)
- 통계 카드 (총 분석 수, 발견된 규제, 체크리스트)
- 시스템 상태 모니터링
- 최근 분석 내역

## API 통신

백엔드 API (FastAPI)와 통신:
- **Base URL**: `http://localhost:8000`
- **Proxy**: Vite dev server에서 `/api` 요청을 백엔드로 프록시

### API 엔드포인트
- `POST /api/analyze` - 규제 분석 실행
- `GET /api/analysis/:id` - 분석 결과 조회
- `GET /api/download/:id` - PDF 다운로드
- `POST /api/distribute` - 체크리스트 분배
- `GET /api/stats` - 통계 조회
- `GET /health` - 헬스체크

## 상태 관리 (Pinia)

### Analysis Store (`stores/analysis.js`)
- 분석 결과, 진행 상황, 에러 관리
- Computed: regulations, checklists, priorityDistribution 등
- Actions: setAnalysis, updateProgress, startLoading, stopLoading

### Stats Store (`stores/stats.js`)
- 대시보드 통계 관리
- Actions: fetchStats, clearStats

## 스타일링

- eunsu 브랜치의 CSS를 Vue 스타일로 변환
- Scoped CSS 사용
- 그라데이션 배경: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- 우선순위 뱃지 색상: HIGH (빨강), MEDIUM (노랑), LOW (초록)
- 반응형 디자인 (모바일 대응)

## 데모 모드

URL에 `?demo=1` 추가 시 샘플 데이터 자동 입력:
```
http://localhost:5173/?demo=1
```

## 백엔드 연동

1. **백엔드 서버 실행** (FastAPI)
   ```bash
   cd ../backend
   uvicorn api.main:app --reload --port 8000
   ```

2. **프론트엔드 실행**
   ```bash
   npm run dev
   ```

3. **브라우저에서 접속**
   ```
   http://localhost:5173
   ```

## 개발 가이드

### 새 컴포넌트 추가
1. `src/components/` 에 `.vue` 파일 생성
2. `<template>`, `<script setup>`, `<style scoped>` 섹션 작성
3. 필요한 경우 Pinia 스토어 임포트

### 새 페이지 추가
1. `src/views/` 에 뷰 파일 생성
2. `src/router/index.js` 에 라우트 추가
3. `App.vue` 네비게이션 탭 추가

### API 엔드포인트 추가
1. `src/api/endpoints.js` 에 함수 추가
2. Axios 인스턴스 사용

## 트러블슈팅

### CORS 오류
- Vite 프록시 설정 확인 (`vite.config.js`)
- 백엔드 CORS 설정 확인

### API 연결 실패
- 백엔드 서버 실행 확인 (`http://localhost:8000`)
- 환경 변수 확인 (`.env`)

### 빌드 오류
- `node_modules` 삭제 후 재설치: `rm -rf node_modules && npm install`
- Node.js 버전 확인 (16.0 이상 권장)

## 라이선스

MIT
