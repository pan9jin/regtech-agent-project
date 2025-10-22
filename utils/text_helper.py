"""텍스트 처리 관련 헬퍼 함수"""


def truncate(text: str, limit: int = 300) -> str:
    """텍스트를 지정된 길이로 자릅니다.

    Args:
        text: 원본 텍스트
        limit: 최대 길이

    Returns:
        잘린 텍스트 (필요시 '...' 추가)
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
