"""Pydantic schemas for the RegTech FastAPI service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator, model_validator

from regtech_agent import BusinessInfo


class BusinessInfoPayload(BaseModel):
    """사용자로부터 입력받는 사업 정보 스키마."""

    industry: str = Field(..., description="사업 업종")
    product_name: str = Field(..., description="주요 제품명")
    raw_materials: str = Field(..., description="주요 원자재")
    processes: List[str] = Field(default_factory=list, description="주요 공정 목록")
    employee_count: int = Field(
        0, ge=0, description="직원 수 (0 이상의 정수)"
    )
    sales_channels: List[str] = Field(default_factory=list, description="판매 채널")
    export_countries: List[str] = Field(default_factory=list, description="수출 국가")
    contact_email: Optional[str] = Field(
        default=None,
        description="보고서 기본 수신 이메일 (선택값)",
    )

    @validator("processes", "sales_channels", "export_countries", pre=True)
    def _ensure_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [item.strip() for item in text.split(",") if item.strip()] if text else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def to_agent_payload(self) -> BusinessInfo:
        """regtech_agent에서 사용하는 TypedDict 형태로 변환."""
        payload: BusinessInfo = {
            "industry": self.industry,
            "product_name": self.product_name,
            "raw_materials": self.raw_materials,
            "processes": self.processes,
            "employee_count": self.employee_count,
            "sales_channels": self.sales_channels,
            "export_countries": self.export_countries,
        }
        if self.contact_email:
            payload["contact_email"] = self.contact_email
        return payload


class AnalysisRequest(BaseModel):
    """규제 분석 실행 요청."""

    business_info: BusinessInfoPayload
    email_recipients: Optional[List[str]] = Field(
        default=None,
        description="보고서를 수신할 이메일 주소 목록 (쉼표 구분 허용)",
    )

    @model_validator(mode="before")
    @classmethod
    def _merge_email_fields(cls, data: Any) -> Any:
        """기존 필드명(email_recipient)과 호환되도록 전처리."""
        if isinstance(data, dict) and "email_recipients" not in data:
            legacy_value = data.get("email_recipient")
            if legacy_value is not None:
                data = {**data, "email_recipients": legacy_value}
        return data

    @validator("email_recipients", pre=True)
    def _normalize_emails(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        candidates: List[str] = []
        if isinstance(value, str):
            candidates = [token.strip() for token in value.split(",") if token.strip()]
        elif isinstance(value, list):
            for entry in value:
                if entry is None:
                    continue
                candidates.extend(
                    [token.strip() for token in str(entry).split(",") if token and token.strip()]
                )
        else:
            text = str(value).strip()
            if text:
                candidates.append(text)
        return candidates or None


class AnalysisSummary(BaseModel):
    """분석 결과 요약."""

    regulation_count: int
    checklist_count: int
    execution_plan_count: int
    risk_score: float
    high_priority: int
    medium_priority: int
    low_priority: int
    pdf_path: Optional[str] = None


class AnalysisRecord(BaseModel):
    """저장/응답용 분석 레코드."""

    analysis_id: str
    summary: AnalysisSummary
    business_info: BusinessInfoPayload
    regulations: List[Dict[str, Any]]
    checklists: List[Dict[str, Any]]
    execution_plans: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    final_report: Dict[str, Any]
    email_status: Optional[Dict[str, Any]] = None


class AnalysisTriggerResponse(BaseModel):
    """POST /api/analyze 응답."""

    status: str = Field("completed", description="분석 상태")
    analysis_id: str
    summary: AnalysisSummary
    pdf_path: Optional[str] = None
    message: Optional[str] = None


class StatsResponse(BaseModel):
    """분석 파일 기반 통계 응답."""

    total_analyses: int
    total_regulations: int
    total_checklists: int
    average_regulations: float
    average_checklists: float
