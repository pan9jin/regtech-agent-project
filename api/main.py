"""FastAPI application exposing regtech_agent workflow as HTTP API."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from regtech_agent import run_regulation_agent

from .schemas import (
    AnalysisRecord,
    AnalysisRequest,
    AnalysisSummary,
    AnalysisTriggerResponse,
    BusinessInfoPayload,
    StatsResponse,
)


app = FastAPI(
    title="RegTech Agent API",
    description="LangGraph 기반 규제 준수 분석 워크플로우를 FastAPI로 제공합니다.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "report"

def _create_summary(payload: Dict[str, Any]) -> AnalysisSummary:
    regulations = payload.get("regulations") or []
    checklists = payload.get("checklists") or []
    plans = payload.get("execution_plans") or []

    priority_tally = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for regulation in regulations:
        bucket = regulation.get("priority", "MEDIUM")
        if bucket in priority_tally:
            priority_tally[bucket] += 1

    risk_assessment = payload.get("risk_assessment") or {}
    risk_score = float(risk_assessment.get("total_risk_score") or 0.0)

    return AnalysisSummary(
        regulation_count=len(regulations),
        checklist_count=len(checklists),
        execution_plan_count=len(plans),
        risk_score=risk_score,
        high_priority=priority_tally["HIGH"],
        medium_priority=priority_tally["MEDIUM"],
        low_priority=priority_tally["LOW"],
        pdf_path=payload.get("final_report", {}).get("report_pdf_path"),
    )


def _rewrite_report_files(analysis_id: str, final_report: Dict[str, Any]) -> Optional[str]:
    """복수 분석 요청 시 PDF/MD 파일이 덮어쓰이지 않도록 사본을 생성합니다."""
    base_path = final_report.get("report_pdf_path")
    if not base_path:
        return None

    source_pdf = Path(base_path)
    if not source_pdf.exists():
        return None

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    target_pdf = REPORT_DIR / f"regulation_report_{analysis_id}.pdf"
    shutil.copy2(source_pdf, target_pdf)

    # Markdown 보고서도 동일한 이름으로 복사 (존재하는 경우)
    markdown_candidate = source_pdf.with_suffix(".md")
    if markdown_candidate.exists():
        target_md = REPORT_DIR / f"regulation_report_{analysis_id}.md"
        shutil.copy2(markdown_candidate, target_md)

    final_report["report_pdf_path"] = str(target_pdf)
    return str(target_pdf)


def _persist_analysis(record: AnalysisRecord) -> None:
    filename = PROJECT_ROOT / f"analysis_{record.analysis_id}.json"
    payload = record.model_dump()
    with filename.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)


def _load_analysis(analysis_id: str) -> AnalysisRecord:
    filename = PROJECT_ROOT / f"analysis_{analysis_id}.json"
    if not filename.exists():
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    with filename.open("r", encoding="utf-8") as file_handle:
        content = json.load(file_handle)

    return AnalysisRecord.model_validate(content)


def _format_email_message(status: Dict[str, Any]) -> Optional[str]:
    if not status:
        return None

    attempted = status.get("attempted", False)
    recipients = status.get("recipients") or []
    details = status.get("details") or []
    errors = status.get("errors") or []

    if not attempted:
        if errors:
            return "; ".join(errors)
        return None

    if status.get("success"):
        if recipients:
            return f"보고서 이메일 발송 완료 ({', '.join(recipients)})"
        return "보고서 이메일 발송 완료"

    detail_errors = [item.get("error") for item in details if not item.get("success") and item.get("error")]
    all_errors = [err for err in [*errors, *detail_errors] if err]
    if all_errors:
        deduped = list(dict.fromkeys(all_errors))
        return "; ".join(deduped)
    return "이메일 발송에 실패했습니다."


@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def landing_page() -> str:
    """간단한 인덱스 페이지."""
    return """
    <html>
        <head><title>RegTech Agent API</title></head>
        <body>
            <h1>RegTech Assistant</h1>
            <p>규제 준수 분석 워크플로우 API가 실행 중입니다.</p>
            <p><a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>
        </body>
    </html>
    """


@app.post("/api/analyze", response_model=AnalysisTriggerResponse, tags=["Analysis"])
async def analyze_regulations(
    request: AnalysisRequest,
) -> AnalysisTriggerResponse:
    """regtech_agent 워크플로우를 실행하여 규제 분석을 수행합니다."""
    business_payload = request.business_info.to_agent_payload()
    analysis_id = uuid4().hex[:8]

    try:
        final_state = await run_in_threadpool(
            run_regulation_agent,
            business_payload,
            request.email_recipients,
        )
    except Exception as exc:  # pragma: no cover - FastAPI 런타임 오류 처리
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    final_report = final_state.get("final_report") or {}
    pdf_path = _rewrite_report_files(analysis_id, final_report)

    summary = _create_summary(final_state)
    if pdf_path:
        summary.pdf_path = pdf_path

    record = AnalysisRecord(
        analysis_id=analysis_id,
        summary=summary,
        business_info=request.business_info,
        regulations=final_state.get("regulations", []),
        checklists=final_state.get("checklists", []),
        execution_plans=final_state.get("execution_plans", []),
        risk_assessment=final_state.get("risk_assessment", {}),
        final_report=final_report,
        email_status=final_state.get("email_status"),
    )

    _persist_analysis(record)

    email_status = record.email_status or {}
    message = _format_email_message(email_status)

    return AnalysisTriggerResponse(
        status="completed",
        analysis_id=analysis_id,
        summary=summary,
        pdf_path=summary.pdf_path,
        message=message,
    )


@app.get("/api/analysis/{analysis_id}", response_model=AnalysisRecord, tags=["Analysis"])
async def get_analysis(analysis_id: str) -> AnalysisRecord:
    """저장된 분석 결과를 조회합니다."""
    return _load_analysis(analysis_id)


@app.get("/api/download/{analysis_id}", tags=["Analysis"])
async def download_report(analysis_id: str) -> FileResponse:
    """생성된 PDF 보고서를 다운로드합니다."""
    record = _load_analysis(analysis_id)
    pdf_path = record.summary.pdf_path or record.final_report.get("report_pdf_path")

    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF 경로가 등록되지 않았습니다.")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다.")

    return FileResponse(
        path=pdf_file,
        media_type="application/pdf",
        filename=pdf_file.name,
    )


@app.get("/api/stats", response_model=StatsResponse, tags=["Analysis"])
async def get_stats() -> StatsResponse:
    """분석 통계를 반환합니다 (메모리 캐시 기반)."""
    total_analyses = len(_analysis_cache)

    if total_analyses == 0:
        return StatsResponse(
            total_analyses=0,
            total_regulations=0,
            total_checklists=0,
            average_regulations=0.0,
            average_checklists=0.0,
        )

    total_regulations = 0
    total_checklists = 0

    for analysis_id, record in _analysis_cache.items():
        try:
            total_regulations += len(record.regulations)
            total_checklists += len(record.checklists)
        except Exception:
            continue

    average_regulations = total_regulations / total_analyses if total_analyses else 0.0
    average_checklists = total_checklists / total_analyses if total_analyses else 0.0

    return StatsResponse(
        total_analyses=total_analyses,
        total_regulations=total_regulations,
        total_checklists=total_checklists,
        average_regulations=round(average_regulations, 2),
        average_checklists=round(average_checklists, 2),
    )


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """간단한 헬스 체크."""
    return {
        "status": "healthy",
        "version": app.version,
        "features": {
            "regulation_analysis": True,
            "report_generation": True,
            "email_notification": True,
        },
    }
