import json
import os
import re

import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError


load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-haiku-20240307-v1:0"
)


SCHOLARSHIP_SYSTEM_PROMPT = """
너는 대학교 장학 제도 분석 AI 에이전트다.

목표:
- 학생의 성적 정보와 학교 장학 제도 내용을 비교한다.
- 학생에게 가능성 있는 장학금과 준비 전략을 추천한다.
- 반드시 JSON 형식으로만 응답한다.

주의:
- 이름, 학번, 전화번호, 이메일 같은 개인정보는 절대 출력하지 않는다.
- 확실하지 않은 내용은 warnings에 적는다.
- 장학금 가능성은 높음, 보통, 낮음, 판단 불가 중 하나로 작성한다.
- [중요] 학과 석차, 소득구간, 직전 학기 이수학점 등의 필수 정보가 데이터에 없다면, 절대 GPA만으로 가능성을 유추하지 말고 무조건 "판단 불가" 또는 "추가 확인 필요"로 평가해라!
"""



def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION
    )


def extract_json_from_text(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)

    if not match:
        raise ValueError("AI 응답에서 JSON을 찾지 못했습니다.")

    return json.loads(match.group(0))


def build_scholarship_prompt(
    transcript_data: dict,
    scholarship_policy: dict
) -> str:
    safe_transcript_data = {
        "department": transcript_data.get("department"),
        "student_year": transcript_data.get("student_year"),
        "total_credits": transcript_data.get("total_credits"),
        "major_credits": transcript_data.get("major_credits"),
        "general_credits": transcript_data.get("general_credits"),
        "gpa": transcript_data.get("gpa"),
        "completed_courses": transcript_data.get("completed_courses", []),
        "warnings": transcript_data.get("warnings", []),
        "extraction_confidence": transcript_data.get("extraction_confidence"),
    }

    return f"""
아래는 학생의 성적 데이터와 학교 장학 제도 내용이다.

[학생 성적 데이터]
{json.dumps(safe_transcript_data, ensure_ascii=False, indent=2)}

[학교 장학 제도 내용]
{json.dumps(scholarship_policy, ensure_ascii=False, indent=2)}

위 정보를 비교해서 학생에게 적절한 장학금 가능성과 전략을 분석해라.

반드시 아래 JSON 형식으로만 응답해라.

{{
  "current_gpa": null,
  "possibility": "높음 또는 보통 또는 낮음 또는 판단 불가",
  "recommended_scholarships": [
    {{
      "name": "장학금 이름",
      "possibility": "높음 또는 보통 또는 낮음 또는 판단 불가",
      "reason": "추천 또는 판단 이유",
      "requirements_to_check": ["확인해야 할 조건"]
    }}
  ],
  "advice": "학생에게 줄 장학금 준비 전략",
  "warnings": []
}}

개인정보는 절대 포함하지 마라.
"""

def normalize_scholarship_result(
    result: dict,
    transcript_data: dict
) -> dict:
    recommended_scholarships = result.get("recommended_scholarships") or []

    normalized_scholarships = []

    for scholarship in recommended_scholarships:
        if not isinstance(scholarship, dict):
            continue

        normalized_scholarships.append({
            "name": scholarship.get("name"),
            "possibility": scholarship.get("possibility", "판단 불가"),
            "reason": scholarship.get("reason", ""),
            "requirements_to_check": scholarship.get("requirements_to_check", []),
        })

    return {
        "current_gpa": result.get("current_gpa", transcript_data.get("gpa")),
        "possibility": result.get("possibility", "판단 불가"),
        "recommended_scholarships": normalized_scholarships,
        "advice": result.get("advice", ""),
        "warnings": result.get("warnings") or [],
    }

def fallback_scholarship_analysis(
    transcript_data: dict,
    error_message: str
) -> dict:
    gpa = transcript_data.get("gpa")

    if gpa is None:
        possibility = "판단 불가"
        advice = "GPA 정보가 없어 장학금 가능성을 판단하기 어렵습니다."

    elif gpa >= 4.0:
        possibility = "높음"
        advice = (
            "현재 GPA가 높은 편이므로 성적우수장학금 가능성이 있습니다. "
            "다만 실제 선발 기준은 학과 석차, 직전학기 이수학점, "
            "장학 공지 내용을 함께 확인해야 합니다."
        )

    elif gpa >= 3.5:
        possibility = "보통"
        advice = (
            "현재 GPA는 장학금 가능성이 있는 수준입니다. "
            "직전학기 이수학점과 학과별 세부 기준을 확인하는 것이 좋습니다."
        )

    else:
        possibility = "낮음"
        advice = (
            "현재 GPA 기준으로는 성적우수장학금 가능성이 높지 않습니다. "
            "다음 학기 성적 향상 전략이 필요합니다."
        )

    return {
        "current_gpa": gpa,
        "possibility": possibility,
        "recommended_scholarships": [
            {
                "name": "성적우수장학금",
                "possibility": possibility,
                "reason": "AI 모델 호출에 실패하여 GPA와 장학 제도 내용을 기준으로 예비 판단했습니다.",
                "requirements_to_check": [
                    "직전학기 이수학점 기준",
                    "학과별 석차 기준",
                    "해당 학기 장학 공지",
                    "국가장학금의 경우 소득구간 및 한국장학재단 기준"
                ],
            }
        ],
        "advice": advice,
        "warnings": [
            "Bedrock AI 장학금 분석 호출에 실패하여 예비 분석 결과를 반환했습니다.",
            error_message
        ],
    }

def analyze_scholarship_possibility(
    transcript_data: dict,
    scholarship_policy: dict | None = None
) -> dict:
    if not scholarship_policy:
        return {
            "current_gpa": transcript_data.get("gpa"),
            "possibility": "판단 불가",
            "recommended_scholarships": [],
            "advice": "학교 장학 제도 정보가 없어 장학금 가능성을 정확히 분석할 수 없습니다.",
            "warnings": ["장학 제도 정보가 필요합니다."]
        }

    policy_content = scholarship_policy.get("content")

    if not policy_content:
        return {
            "current_gpa": transcript_data.get("gpa"),
            "possibility": "판단 불가",
            "recommended_scholarships": [],
            "advice": "장학 제도 내용이 비어 있어 분석할 수 없습니다.",
            "warnings": ["scholarship_policy의 content 값이 비어 있습니다."]
        }

    prompt = build_scholarship_prompt(
        transcript_data=transcript_data,
        scholarship_policy=scholarship_policy
    )

    client = get_bedrock_client()

    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[
                {
                    "text": SCHOLARSHIP_SYSTEM_PROMPT
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0.2
            },
        )

    except Exception as e:
        return fallback_scholarship_analysis(
            transcript_data=transcript_data,
            error_message=str(e)
        )

    response_text = response["output"]["message"]["content"][0]["text"]

    result = extract_json_from_text(response_text)

    return normalize_scholarship_result(
        result=result,
        transcript_data=transcript_data
    )

