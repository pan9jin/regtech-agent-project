# PDF 보고서 생성 가이드

## 개요

Report Generation Agent가 JSON 파일뿐만 아니라 **전문적인 PDF 보고서**를 자동 생성합니다.

## 주요 기능

### 1. 자동 PDF 생성
- ✅ 규제 분석 결과를 전문적인 PDF 문서로 자동 변환
- ✅ 깔끔한 레이아웃 및 테이블 스타일
- ✅ 섹션별 구조화된 내용
- ✅ A4 크기로 인쇄 가능
- ✅ **한글 폰트 자동 지원** (네모 깨짐 현상 해결)

### 2. PDF 보고서 구성

```
┌─────────────────────────────────────┐
│        규제 준수 분석 보고서         │
│                                     │
│   리튬이온 배터리 제조업             │
│                                     │
│   생성일: 2025년 10월 21일           │
└─────────────────────────────────────┘

1. 요약
   ├─ 적용 규제 수
   ├─ 체크리스트 항목
   └─ 리스크 점수

2. 적용 규제 목록
   ├─ HIGH (필수)
   │   └─ 화학물질관리법
   ├─ MEDIUM (권장)
   └─ LOW (선택)

3. 실행 체크리스트
   ├─ 규제별 그룹핑
   └─ Task 상세 정보

4. 리스크 평가
   ├─ 리스크 점수
   └─ 권장 사항
```

## 사용 방법

### Option 1: main.py 실행 (권장)

```bash
python main.py
```

실행 시 자동으로 두 가지 파일 생성:
- ✅ `regulation_analysis_result.json` - 데이터 파일
- ✅ `regulation_report.pdf` - **PDF 보고서**

### Option 2: 프로그래밍 방식

```python
from utils.pdf_generator import generate_pdf_report

# 분석 결과 데이터
data = {
    "business_info": {...},
    "summary": {...},
    "regulations": [...],
    "checklists": [...],
    "risk_assessment": {...}
}

# PDF 생성
pdf_path = generate_pdf_report(data, "my_report.pdf")
print(f"PDF 생성 완료: {pdf_path}")
```

### Option 3: Report Generation Agent 직접 호출

```python
from agents import generate_report

result = run_regulation_agent(business_info)

# Agent가 자동으로 JSON + PDF 생성
report_result = generate_report.invoke({
    "agent_state": result,
    "output_json": "report.json",
    "output_pdf": "report.pdf"
})

print(f"JSON: {report_result['json_path']}")
print(f"PDF: {report_result['pdf_path']}")
```

## 한글 폰트 지원

### 자동 폰트 등록
PDF 생성 시 macOS 시스템 폰트를 자동으로 감지하고 등록합니다:

1. **AppleGothic** (우선 순위 1) - macOS 기본 한글 폰트
2. **AppleMyungjo** (우선 순위 2) - 명조체
3. **NotoSansGothic** (우선 순위 3) - Noto Sans 한글

### 폰트 적용 범위
- ✅ 모든 텍스트 (제목, 본문, 테이블 등)
- ✅ PDF 표지 페이지
- ✅ 섹션 제목
- ✅ 테이블 셀 내용
- ✅ 리스트 항목

### 폰트 등록 확인
PDF 생성 시 터미널에 다음 메시지가 표시됩니다:
```
✓ 한글 폰트 등록 성공: AppleGothic
```

폰트를 찾지 못하면 경고 메시지가 표시되지만, PDF는 여전히 생성됩니다 (단, 한글이 깨질 수 있음).

## PDF 커스터마이징

### 1. 출력 경로 변경

```python
from utils.pdf_generator import RegulationReportGenerator

generator = RegulationReportGenerator("custom_report.pdf")
generator.generate_report(data)
```

### 2. 스타일 수정

`utils/pdf_generator.py`의 `_add_custom_styles()` 메서드에서 스타일 변경 가능:

```python
self.styles.add(ParagraphStyle(
    name='CustomTitle',
    fontSize=28,  # 제목 크기 변경
    textColor=HexColor('#ff0000'),  # 색상 변경
    ...
))
```

**참고**: 한글 폰트는 자동으로 적용되므로 별도 설정이 필요 없습니다.

### 3. 섹션 추가/제거

`generate_report()` 메서드에서 원하는 섹션만 포함:

```python
def generate_report(self, data):
    self._add_cover_page(data)
    self._add_summary_section(data)
    self._add_regulations_section(data)
    # self._add_checklist_section(data)  # 체크리스트 제외
    # ... 필요한 섹션만 추가
```

## PDF 특징

### 표지 페이지
- 보고서 제목
- 사업 정보 요약
- 생성 날짜

### 요약 섹션
- 핵심 지표를 테이블로 표시
- 색상으로 구분된 헤더
- 읽기 쉬운 레이아웃

### 규제 목록
- 우선순위별 색상 구분
  - 🔴 HIGH (빨강)
  - 🟡 MEDIUM (주황)
  - 🟢 LOW (초록)
- 각 규제의 상세 정보
- 주요 요구사항 목록

### 체크리스트
- 규제별 그룹핑
- 체크박스 (☐) 표시
- 담당 부서, 마감일, 비용 정보

### 리스크 평가
- 리스크 점수 강조
- 권장 사항 목록

## 요구사항

```bash
pip install reportlab>=4.0.0
```

## 문제 해결

### 1. "reportlab 모듈을 찾을 수 없습니다"

```bash
pip install reportlab
```

### 2. 한글 폰트가 네모(□)로 깨지는 경우

✅ **완전 해결됨!** 이제 한글 폰트가 자동으로 등록되고 모든 스타일에 적용되어 한글이 정상적으로 표시됩니다.

**해결 내용:**
- ✅ 모든 기본 스타일(Normal, Heading1-3, BodyText 등)에 한글 폰트 강제 적용
- ✅ 유니코드 이모지 제거 (☐ → `[ ]`)
- ✅ 모든 테이블 셀에 한글 폰트 명시적 지정

시스템별 폰트 경로:

**macOS** (자동 지원):
- `/System/Library/Fonts/Supplemental/AppleGothic.ttf`
- `/System/Library/Fonts/Supplemental/AppleMyungjo.ttf`
- `/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf`

**Windows** (추가 설정 필요 시):
```python
# pdf_generator.py의 _register_fonts() 메서드에 추가
font_paths = [
    ('C:/Windows/Fonts/malgun.ttf', 'MalgunGothic'),  # 맑은 고딕
    ('C:/Windows/Fonts/batang.ttc', 'Batang'),  # 바탕
]
```

**Linux** (추가 설정 필요 시):
```bash
# 나눔고딕 설치
sudo apt-get install fonts-nanum

# 또는 폰트 경로 수정
font_paths = [
    ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 'NanumGothic'),
]
```

### 3. 폰트 등록 확인

PDF 생성 시 터미널 출력 확인:
```
✓ 한글 폰트 등록 성공: AppleGothic  ← 성공
⚠️ 한글 폰트를 찾을 수 없습니다      ← 실패 (폰트 경로 확인 필요)
```

### 3. PDF 생성 실패

에러 메시지 확인 후:

```bash
# 디버그 모드로 실행
python -c "
from utils.pdf_generator import generate_pdf_report
import traceback

try:
    generate_pdf_report(data, 'test.pdf')
except Exception as e:
    traceback.print_exc()
"
```

## 예시 출력

실행 후 다음과 같은 메시지 표시:

```
============================================================
📄 최종 보고서 생성
============================================================

✓ JSON 보고서: regulation_analysis_result.json
✓ PDF 보고서: regulation_report.pdf

💾 모든 보고서가 생성되었습니다!
```

생성된 파일:
- **regulation_analysis_result.json** (약 15KB) - 데이터 파일
- **regulation_report.pdf** (약 50-100KB) - PDF 보고서

## 활용 사례

### 1. 경영진 보고용
- PDF를 이메일로 전송
- 회의 자료로 출력

### 2. 컴플라이언스 문서
- 규제 준수 현황 기록
- 내부 감사 자료

### 3. 고객 제공용
- 컨설팅 보고서
- 규제 분석 서비스 결과물

## 다음 단계

### Phase 1 (현재)
- ✅ 기본 PDF 생성
- ✅ 섹션별 구조화
- ✅ 테이블 및 스타일링

### Phase 2 (예정)
- [ ] 차트 및 그래프 추가
- [ ] 커버 페이지 디자인 개선
- [ ] 한글 폰트 자동 다운로드
- [ ] 워터마크 추가
- [ ] 목차 자동 생성

### Phase 3 (예정)
- [ ] 여러 템플릿 지원
- [ ] 인터랙티브 PDF (하이퍼링크)
- [ ] 디지털 서명
- [ ] PDF/A 표준 준수

---

## 참고 자료

- ReportLab 공식 문서: https://docs.reportlab.com/
- PDF 스타일 가이드: `utils/pdf_generator.py` 참조
- 예시 보고서: `test_report.pdf`
