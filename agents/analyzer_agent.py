"""Analyzer Agent - 사업 정보 분석 및 키워드 추출"""

from typing import Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from models import BusinessInfo


@tool
def analyze_business(business_info: BusinessInfo) -> Dict[str, Any]:
    """사업 정보를 분석하여 규제 검색용 키워드를 추출합니다.

    Args:
        business_info: 사업 정보 (업종, 제품명, 원자재 등)

    Returns:
        추출된 키워드 목록
    """
    print("🔍 [Analyzer Agent] 사업 정보 분석 중...")
    print(f"   업종: {business_info['industry']}")
    print(f"   제품: {business_info['product_name']}")
    print(f"   원자재: {business_info['raw_materials']}")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
다음 사업 정보를 분석하여 규제 검색에 필요한 핵심 키워드를 추출하세요.

업종: {business_info['industry']}
제품명: {business_info['product_name']}
원자재: {business_info['raw_materials']}
제조 공정: {', '.join(business_info.get('processes', []))}
직원 수: {business_info.get('employee_count', 0)}
판매 방식: {', '.join(business_info.get('sales_channels', []))}

규제와 관련된 키워드를 5-7개 추출하되, 다음을 포함해야 합니다:
- 제품/산업 관련 키워드
- 안전/환경 관련 키워드
- 인증/허가 관련 키워드

출력 형식: 키워드를 쉼표로 구분하여 나열하세요.
예시: 배터리, 화학물질, 산업안전, 제품인증, 유해물질
"""

    response = llm.invoke(prompt)
    keywords = [k.strip() for k in response.content.split(',')]

    print(f"   ✓ 추출된 키워드 ({len(keywords)}개): {keywords}\n")

    return {"keywords": keywords}
