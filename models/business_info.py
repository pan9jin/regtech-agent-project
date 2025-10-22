"""사업 정보 데이터 모델"""

from typing import List
from typing_extensions import TypedDict


class BusinessInfo(TypedDict, total=False):
    """사업 정보 데이터 구조"""
    industry: str
    product_name: str
    raw_materials: str
    processes: List[str]
    employee_count: int
    sales_channels: List[str]
    export_countries: List[str]
