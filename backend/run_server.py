"""CLI helper to launch the RegTech FastAPI service."""

from pathlib import Path
import sys

import uvicorn
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    """Start the FastAPI development server."""
    load_dotenv()

    print("=" * 60)
    print("🚀  RegTech Assistant API 서버 기동")
    print("=" * 60)
    print("· 주소:    http://127.0.0.1:8000")
    print("· 문서:    http://127.0.0.1:8000/docs")
    print("· ReDoc:  http://127.0.0.1:8000/redoc")
    print("=" * 60)

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
