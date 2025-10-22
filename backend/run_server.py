"""
규제 준수 자동화 시스템 서버 실행 스크립트

사용법:
    python run_server.py
"""

import uvicorn
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


def main():
    """서버 실행"""
    print("=" * 60)
    print("🚀 규제 준수 자동화 시스템 서버 시작")
    print("=" * 60)
    print()
    print("📡 API 서버: http://localhost:8000")
    print("📚 API 문서: http://localhost:8000/docs")
    print("🌐 웹 UI:    http://localhost:8000")
    print("🎮 데모 모드: http://localhost:8000?demo=1")
    print()
    print("Ctrl+C를 눌러 서버를 종료할 수 있습니다.")
    print("=" * 60)
    print()

    # uvicorn으로 서버 실행
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
