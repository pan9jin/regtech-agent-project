"""
Checklist Generator Agent - 규제별 체크리스트 생성
"""

from typing import Dict, Any, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import json
from datetime import datetime

from ..models import Regulation
from ..utils import normalize_evidence_payload, ensure_dict_list


@tool
def generate_checklists(regulations: List[Regulation]) -> Dict[str, Any]:
    """각 규제에 대한 실행 가능한 체크리스트를 생성합니다.

    Args:
        regulations: 우선순위가 결정된 규제 목록

    Returns:
        체크리스트 항목 목록
    """
    print("📝 [Checklist Generator Agent] 규제별 체크리스트 생성 중...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    all_checklists = []

    # 현재 시스템 시간 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")

    for reg in regulations:
        print(f"   {reg['name']} - 체크리스트 생성 중...")

        source_summary = "\n".join([
            f"{src.get('source_id','-')} | {src.get('title','제목 없음')}\nURL: {src.get('url','')}\n발췌: {src.get('snippet','')}"
            for src in reg.get('sources', [])
        ]) or "등록된 출처 없음"

        prompt = f"""
다음 규제를 준수하기 위한 실행 가능한 체크리스트를 생성하세요.
각 작업마다 실제 인터넷 출처(source_id)를 evidence 배열에 포함해야 합니다.

[규제 정보]
규제명: {reg['name']}
카테고리: {reg['category']}
관할 기관: {reg['authority']}
우선순위: {reg['priority']}
적용 이유: {reg['why_applicable']}
주요 요구사항:
{chr(10).join('  - ' + req for req in reg['key_requirements'])}

[사용 가능한 출처]
{source_summary}

[현재 날짜]
{current_date}

[생성 지침]
1) 작업 수: 3~5개.
2) method[0]에는 "(매핑: 요구사항 N)" 형식으로 매핑 정보를 기재합니다.
3) evidence에는 [사용 가능한 출처]에서 선택한 source_id와 해당 출처의 핵심 문장을 1~2개 포함합니다.
4) method 단계는 3~5개, 마지막 단계에는 증빙/기록 확보를 포함합니다.
5) deadline은 현재 날짜({current_date})를 기준으로 우선순위에 맞게 YYYY-MM-DD 형식으로 계산합니다.
   - HIGH: 현재일 + 1~3개월
   - MEDIUM: 현재일 + 3~6개월
   - LOW: 현재일 + 6~12개월
6) estimated_time은 실제 소요 시간을 구체적으로 작성합니다 (예: "2주", "1개월").
7) JSON 배열 외 텍스트는 금지합니다.

[출력 스키마]
{{
  "task_name": "구체적인 작업명(명령형)",
  "responsible_dept": "담당 부서",
  "deadline": "YYYY-MM-DD",
  "method": [
    "1. (매핑: 요구사항 N) ...",
    "2. ...",
    "3. ...",
    "4. ...",
    "5. ..."
  ],
  "estimated_time": "소요 시간",
  "evidence": [
    {{
      "source_id": "SRC-001",
      "justification": "출처에서 확인한 핵심 문장"
    }}
  ]
}}
"""

        response = llm.invoke(prompt)

        try:
            # JSON 파싱
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            raw_payload = json.loads(content.strip())
            checklist_items = ensure_dict_list(raw_payload)

            if not checklist_items:
                print("      ⚠️  체크리스트 응답이 비어 있거나 형식이 올바르지 않습니다.")
                continue

            source_lookup = {
                src.get("source_id"): src for src in reg.get("sources", [])
                if src.get("source_id")
            }

            # ChecklistItem 형식으로 변환
            for item in checklist_items:
                if not isinstance(item, dict):
                    continue

                evidence_entries = normalize_evidence_payload(
                    item.get("evidence"),
                    source_lookup
                )

                method_steps = item.get("method") or []
                if isinstance(method_steps, str):
                    method_steps = [method_steps]

                all_checklists.append({
                    "regulation_id": reg['id'],
                    "regulation_name": reg['name'],
                    "task_name": item.get("task_name", ""),
                    "responsible_dept": item.get("responsible_dept", "담당 부서"),
                    "deadline": item.get("deadline", "미정"),
                    "method": method_steps,
                    "estimated_time": item.get("estimated_time", "미정"),
                    "priority": reg['priority'],
                    "status": "pending",
                    "evidence": evidence_entries
                })

        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 파싱 오류: {e}")
            continue

    print(f"   ✓ 체크리스트 생성 완료: 총 {len(all_checklists)}개 항목\n")

    return {"checklists": all_checklists}
