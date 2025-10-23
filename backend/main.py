"""Backend entry point for running the RegTech FastAPI service."""

from pathlib import Path
import sys

import uvicorn
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app as fastapi_app  # noqa: E402

# 환경 변수(.env) 선 로드
load_dotenv()

# FastAPI 애플리케이션 노출
app = fastapi_app


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
