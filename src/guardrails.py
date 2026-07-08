import re


def mask_personal_information(text):
    """
    개인정보를 마스킹하는 함수
    """

    if text is None:
        return text

    # 학번 마스킹
    # 예: 20240001, 20240001이며, 학번20240001 같은 경우도 처리
    text = re.sub(
        r"(?<!\d)\d{8}(?!\d)",
        "********",
        text
    )

    # 전화번호 마스킹
    text = re.sub(
        r"010-\d{4}-\d{4}",
        "010-****-****",
        text
    )

    # 이메일 마스킹
    text = re.sub(
        r"[\w\.-]+@[\w\.-]+\.\w+",
        "[EMAIL]",
        text
    )

    return text


def sanitize_strategy_report(data):
    """
    AI 분석 결과에서 개인정보를 제거하는 함수
    dict, list, str 형태를 모두 처리한다.
    """

    if isinstance(data, dict):
        return {
            key: sanitize_strategy_report(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            sanitize_strategy_report(item)
            for item in data
        ]

    if isinstance(data, str):
        return mask_personal_information(data)

    return data


def apply_guardrails(text):
    """
    Guardrails 적용 함수
    현재는 정규표현식 기반 개인정보 마스킹을 수행하고,
    나중에는 AWS Bedrock Guardrails 호출로 확장할 수 있다.
    """

    return mask_personal_information(text)
def is_forbidden_request(text):
    """
    사용자의 요청이 금지된 요청인지 판단한다.
    다른 학생 정보 조회, 성적 조작, 장학금 부정 수령, 시스템 프롬프트 탈취 요청을 차단한다.
    """

    if text is None:
        return False

    forbidden_keywords = [
        "다른 학생",
        "타인 성적",
        "남의 성적",
        "친구 성적",
        "학생 정보 알려줘",
        "이름 알려줘",
        "학번 알려줘",
        "성적 조작",
        "성적 위조",
        "학점 조작",
        "GPA 조작",
        "평점 조작",
        "장학금 부정",
        "장학금 조작",
        "부정 수령",
        "시스템 프롬프트",
        "프롬프트 보여줘",
        "지시문 보여줘",
        "ignore previous",
        "무시하고 알려줘"
    ]

    lowered_text = text.lower()

    for keyword in forbidden_keywords:
        if keyword.lower() in lowered_text:
            return True

    return False


def validate_user_request(text):
    """
    사용자 요청을 검사하고, 허용 여부와 메시지를 반환한다.
    """

    if is_forbidden_request(text):
        return {
            "allowed": False,
            "message": "개인정보 노출, 성적 조작, 장학금 부정 수령, 시스템 지시문 요청과 관련된 내용은 처리할 수 없습니다."
        }

    return {
        "allowed": True,
        "message": "허용된 요청입니다."
    }