"""FastAPI 메인 애플리케이션"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# API 라우터 임포트 (조건부)
try:
    from .webhook_api import router as webhook_router
    from .workflow_api import router as workflow_router
except ImportError:
    # 상대 경로로 실행할 때
    try:
        from webhook_api import router as webhook_router
        from workflow_api import router as workflow_router
    except ImportError:
        # API 라우터를 찾을 수 없으면 더미 라우터 생성
        from fastapi import APIRouter
        webhook_router = APIRouter()
        workflow_router = APIRouter()
        print("⚠️  Webhook/Workflow API 라우터를 로드할 수 없습니다.")

# 유틸리티 임포트
from utils.task_distributor import auto_distribute_and_send, DEFAULT_ASSIGNEE_CONFIG
from utils.pdf_generator import generate_pdf_report

app = FastAPI(
    title="규제 준수 자동화 API",
    description="AI 기반 규제 분석 및 워크플로우 자동화 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(webhook_router, prefix="/api", tags=["webhook"])
app.include_router(workflow_router, prefix="/api", tags=["workflow"])

# 정적 파일 서빙 (frontend)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============================================================
# Request/Response 모델
# ============================================================

class BusinessInfoRequest(BaseModel):
    """사업 정보 입력 모델"""
    industry: str
    product_name: str
    raw_materials: str
    processes: List[str]
    employee_count: int
    sales_channels: List[str]
    export_countries: Optional[List[str]] = []


class AnalysisResponse(BaseModel):
    """규제 분석 결과 응답"""
    status: str
    analysis_id: str
    summary: Dict[str, Any]
    regulations: List[Dict[str, Any]]
    checklists: List[Dict[str, Any]]
    pdf_path: Optional[str] = None


# ============================================================
# 메인 페이지
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지 서빙"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return """
        <html>
            <head><title>규제 준수 자동화 시스템</title></head>
            <body>
                <h1>규제 준수 자동화 시스템</h1>
                <p>Frontend를 설치 중입니다...</p>
                <p>API 문서: <a href="/docs">/docs</a></p>
            </body>
        </html>
        """


# ============================================================
# 규제 분석 API
# ============================================================

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_regulations(
    request: BusinessInfoRequest,
    background_tasks: BackgroundTasks,
    send_emails: bool = False
):
    """
    규제 분석 실행 API

    Args:
        request: 사업 정보
        send_emails: 이메일 자동 발송 여부

    Returns:
        분석 결과 (regulations, checklists, pdf_path 등)
    """
    try:
        # 사업 정보를 딕셔너리로 변환
        business_info = request.dict()

        # 실제 워크플로우 실행 시도
        try:
            from workflows.runner import run_regulation_agent
            result = run_regulation_agent(business_info)
        except Exception as workflow_error:
            # 워크플로우 실행 실패 시 기존 분석 결과 사용 (데모용)
            print(f"워크플로우 실행 실패: {workflow_error}")
            print("기존 분석 결과를 로드합니다...")

            # 기존 분석 결과 파일 사용
            demo_file = "regulation_analysis_with_workflow.json"
            if os.path.exists(demo_file):
                with open(demo_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                # 사업 정보 업데이트
                result['business_info'] = business_info
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"워크플로우 실행 실패: {str(workflow_error)}"
                )

        # 분석 ID 생성
        import uuid
        analysis_id = str(uuid.uuid4())[:8]

        # PDF 생성
        pdf_filename = f"analysis_{analysis_id}.pdf"
        pdf_path = generate_pdf_report(result, pdf_filename)

        # 이메일 발송 (옵션)
        if send_emails:
            background_tasks.add_task(
                auto_distribute_and_send,
                checklists=result.get('checklists', []),
                assignee_config=DEFAULT_ASSIGNEE_CONFIG,
                send_emails=True
            )

        # 결과 저장 (파일 시스템, 프로덕션에서는 DB 사용)
        result_filename = f"analysis_{analysis_id}.json"
        with open(result_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return AnalysisResponse(
            status="completed",
            analysis_id=analysis_id,
            summary=result.get('summary', {}),
            regulations=result.get('regulations', []),
            checklists=result.get('checklists', []),
            pdf_path=pdf_path
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """분석 결과 조회"""
    result_filename = f"analysis_{analysis_id}.json"

    if not os.path.exists(result_filename):
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

    with open(result_filename, 'r', encoding='utf-8') as f:
        result = json.load(f)

    return result


@app.get("/api/download/{analysis_id}")
async def download_pdf(analysis_id: str):
    """PDF 다운로드"""
    pdf_filename = f"analysis_{analysis_id}.pdf"

    if not os.path.exists(pdf_filename):
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다")

    return FileResponse(
        pdf_filename,
        media_type="application/pdf",
        filename=f"regulation_report_{analysis_id}.pdf"
    )


# ============================================================
# 담당자 배정 API
# ============================================================

@app.post("/api/distribute")
async def distribute_tasks(
    analysis_id: str,
    send_emails: bool = False
):
    """
    체크리스트 담당자별 자동 분배

    Args:
        analysis_id: 분석 ID
        send_emails: 이메일 발송 여부
    """
    result_filename = f"analysis_{analysis_id}.json"

    if not os.path.exists(result_filename):
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

    with open(result_filename, 'r', encoding='utf-8') as f:
        result = json.load(f)

    # 자동 분배 및 이메일 발송
    distribution_result = auto_distribute_and_send(
        checklists=result.get('checklists', []),
        assignee_config=DEFAULT_ASSIGNEE_CONFIG,
        send_emails=send_emails
    )

    return {
        "status": "completed",
        "distribution": distribution_result['distribution'],
        "report": distribution_result['report'],
        "emails_sent": distribution_result['emails_sent']
    }


# ============================================================
# 통계 API
# ============================================================

@app.get("/api/stats")
async def get_stats():
    """전체 통계 조회"""
    # 분석 파일 개수 세기
    import glob
    analysis_files = glob.glob("analysis_*.json")

    total_analyses = len(analysis_files)

    # 최근 분석들의 통계
    total_regulations = 0
    total_checklists = 0

    for filename in analysis_files[:10]:  # 최근 10개
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_regulations += len(data.get('regulations', []))
                total_checklists += len(data.get('checklists', []))
        except:
            continue

    return {
        "total_analyses": total_analyses,
        "total_regulations": total_regulations,
        "total_checklists": total_checklists,
        "avg_regulations_per_analysis": total_regulations / max(total_analyses, 1),
        "avg_checklists_per_analysis": total_checklists / max(total_analyses, 1)
    }


# ============================================================
# 헬스체크
# ============================================================

@app.get("/health")
async def health_check():
    """API 헬스체크"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "features": {
            "regulation_analysis": True,
            "email_automation": True,
            "task_distribution": True,
            "webhook_api": True,
            "pdf_generation": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
