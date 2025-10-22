"""규제 관련 데이터 모델"""

from typing import List, Optional
from typing_extensions import TypedDict
from enum import Enum


class Priority(str, Enum):
    """규제 우선순위"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(str, Enum):
    """규제 카테고리"""
    SAFETY_ENV = "안전/환경"
    PRODUCT_CERT = "제품 인증"
    FACTORY_OPS = "공장 운영"


class Regulation(TypedDict):
    """규제 정보 데이터 구조"""
    id: str
    name: str
    category: str
    why_applicable: str
    authority: str
    priority: str
    key_requirements: List[str]
    reference_url: Optional[str]
