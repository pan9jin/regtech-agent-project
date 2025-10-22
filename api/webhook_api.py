"""
Webhook API 엔드포인트 (n8n, Make.com 등 연동용)
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# regulation_agent_workflow.py에서 BusinessInfo와 run_regulation_agent 함수를 임포트합니다.
# 경로 문제를 해결하기 위해 sys.path를 조작해야 할 수 있습니다.
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from regulation_agent_workflow import BusinessInfo, run_regulation_agent

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])

# Pydantic 모델로 BusinessInfo를 다시 정의하여 FastAPI에서 사용
class BusinessInfoPayload(BaseModel):
    """사업 정보 Webhook Payload"""
    industry: str = Field(..., description="사업 업종", example="배터리 제조")
    product_name: str = Field(..., description="주요 제품명", example="리튬이온 배터리")
    raw_materials: str = Field(..., description="주요 원자재", example="리튬, 코발트, 니켈")
    processes: List[str] = Field(default_factory=list, description="주요 공정", example=["화학 처리", "고온 가공"])
    employee_count: int = Field(..., description="직원 수", example=50)
    sales_channels: List[str] = Field(default_factory=list, description="판매 채널", example=["B2B", "수출"])
    export_countries: List[str] = Field(default_factory=list, description="수출 국가", example=["미국", "유럽"])

    def to_typed_dict(self) -> BusinessInfo:
        """Pydantic 모델을 TypedDict로 변환"""
        return BusinessInfo(
            industry=self.industry,
            product_name=self.product_name,
            raw_materials=self.raw_materials,
            processes=self.processes,
            employee_count=self.employee_count,
            sales_channels=self.sales_channels,
            export_countries=self.export_countries,
        )

@router.post("/trigger/regulation-analysis", status_code=202)
async def trigger_regulation_analysis(
    payload: BusinessInfoPayload,
    background_tasks: BackgroundTasks
):
    """
    Webhook을 통해 규제 분석 워크플로우를 트리거합니다.

    이 엔드포인트는 n8n, Make.com, Zapier 등 외부 자동화 도구에서 호출하여
    새로운 사업 정보가 입력되었을 때 전체 규제 분석 파이프라인을 시작할 수 있습니다.

    - **payload**: 분석할 사업 정보.
    - **background_tasks**: FastAPI의 백그라운드 태스크. 오래 걸리는 분석 작업을 백그라운드에서 처리합니다.
    """
    try:
        print(f"🚀 Webhook 수신: 규제 분석 워크플로우 시작 (제품: {payload.product_name})")
        
        # Pydantic 모델을 TypedDict로 변환
        business_info = payload.to_typed_dict()

        # 백그라운드에서 전체 에이전트 워크플로우 실행
        background_tasks.add_task(run_regulation_agent, business_info)

        return {
            "status": "accepted",
            "message": "규제 분석 워크플로우가 백그라운드에서 시작되었습니다. 완료 시 regulation_analysis_result.json 파일이 생성됩니다."
        }
    except Exception as e:
        print(f"❌ Webhook 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"워크플로우 트리거에 실패했습니다: {str(e)}")