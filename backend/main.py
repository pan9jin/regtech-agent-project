"""
규제 AI Agent 서비스 - FastAPI 메인 실행 파일

- 워크플로우 관리 API
- 외부 연동을 위한 Webhook API
"""

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# API 라우터 임포트
from api import workflow_api, webhook_api

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="규제 AI Agent API",
    description="LangGraph와 FastAPI를 이용한 규제 분석 및 워크플로우 자동화 서비스",
    version="1.0.0",
    contact={
        "name": "seori",
        "url": "https://github.com/seori-k",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# API 라우터 추가
app.include_router(workflow_api.router)
app.include_router(webhook_api.router)

@app.get("/", tags=["Root"])
async def read_root():
    """
    루트 엔드포인트. API 서버가 실행 중인지 확인합니다.
    """
    return {
        "message": "규제 AI Agent API 서버가 실행 중입니다.",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    """
    Uvicorn 서버를 실행하여 API 서비스를 시작합니다.
    """
    print("🚀 규제 AI Agent API 서버를 시작합니다.")
    print("   - 문서 (Swagger UI): http://127.0.0.1:8000/docs")
    print("   - 문서 (ReDoc): http://127.0.0.1:8000/redoc")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)