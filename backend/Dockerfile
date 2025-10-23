# 빌드 스테이지: 의존성 설치
FROM python:3.11-slim AS build-stage

WORKDIR /app

# 시스템 패키지 설치 (필요시)
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

# 프로덕션 스테이지: 런타임 환경
FROM python:3.11-slim

WORKDIR /app

# 빌드 스테이지에서 설치한 패키지 복사
COPY --from=build-stage /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 앱 소스 복사
COPY . .

# (선택) 비root 사용자 생성
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# 포트 노출
EXPOSE 8000

# FastAPI 실행 (uvicorn)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
