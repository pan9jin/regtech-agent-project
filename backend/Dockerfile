# 빌드 스테이지: 의존성 설치
FROM python:3.11-slim AS build-stage

WORKDIR /app

# 시스템 패키지 설치 (PDF 렌더링 및 빌드용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libxml2 \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        libffi-dev \
        shared-mime-info \
        fonts-nanum \
        fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

# 프로덕션 스테이지: 런타임 환경
FROM python:3.11-slim

WORKDIR /app

# 빌드 스테이지에서 설치한 패키지 복사
COPY --from=build-stage /usr/local /usr/local

# PDF 렌더링에 필요한 시스템 라이브러리 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libxml2 \
        libxslt1.1 \
        libffi8 \
        shared-mime-info \
        fonts-nanum \
        fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# 앱 소스 복사
COPY . .

# 보고서 출력 디렉토리 보장
RUN mkdir -p /app/report

# (선택) 비root 사용자 생성
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# FastAPI 실행 (uvicorn)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
