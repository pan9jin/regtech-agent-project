# 설치 가이드

## 옵션 1: 새로운 가상환경 생성 (권장)

기존 환경과의 충돌을 피하기 위해 새로운 가상환경을 만드는 것을 권장합니다.

```bash
# 1. 가상환경 생성
python -m venv venv-regtech

# 2. 가상환경 활성화
# macOS/Linux:
source venv-regtech/bin/activate
# Windows:
# venv-regtech\Scripts\activate

# 3. 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# 4. 실행
python main.py
```

## 옵션 2: 기존 환경에서 설치

기존 환경의 패키지와 호환되도록 조정된 버전을 설치합니다.

```bash
# langchain-core 다운그레이드 (langchain-huggingface 호환)
pip install "langchain-core>=0.3.70,<1.0.0"

# pydantic 다운그레이드 (gradio 호환)
pip install "pydantic>=2.0,<2.12"

# 나머지 패키지 설치
pip install -r requirements.txt
```

## 옵션 3: 핵심 패키지만 설치

최소한의 패키지만 설치하여 충돌을 최소화합니다.

```bash
pip install python-dotenv
pip install langchain-openai
pip install langchain-tavily
pip install langgraph
```

## 의존성 충돌 해결

### 1. langchain-huggingface 충돌
```bash
# langchain-core 버전 조정
pip install "langchain-core>=0.3.70,<1.0.0"
```

### 2. gradio 충돌
```bash
# pydantic 버전 조정
pip install "pydantic>=2.0,<2.12"
```

### 3. 모든 충돌 한번에 해결
```bash
pip install "langchain-core>=0.3.70,<1.0.0" "pydantic>=2.0,<2.12"
pip install -r requirements.txt
```

## 설치 확인

```bash
# Python 인터프리터에서 확인
python -c "import langchain; import langgraph; print('설치 성공!')"
```

## 환경 변수 설정

`.env` 파일을 생성하고 API 키를 설정하세요:

```bash
# .env 파일 생성
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_TRACING=true
EOF
```

## 문제 해결

### ImportError 발생 시
```bash
# 캐시 삭제 후 재설치
pip cache purge
pip uninstall langchain langchain-core langgraph -y
pip install -r requirements.txt
```

### 버전 확인
```bash
pip list | grep -E "langchain|langgraph|pydantic"
```

## 추천 방법

**새 프로젝트라면**: 옵션 1 (새 가상환경)
**기존 환경 유지**: 옵션 2 (버전 조정)
**빠른 테스트**: 옵션 3 (최소 설치)
