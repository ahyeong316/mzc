# check_pdf_models.py
"""
서울 리전에서 어떤 Claude 모델이 PDF 직접 첨부 호출을 지원하는지 진단하는 스크립트.

실행 (mzc 폴더에서):
    python check_pdf_models.py "성적증명서.pdf 경로"

예:
    python check_pdf_models.py C:\\Users\\hae96\\Downloads\\성적증명서.pdf

각 모델에 아주 짧은 질문("문서 제목 한 줄")만 보내므로 비용은 거의 들지 않는다.
"""

import base64
import json
import sys

import boto3

from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION

# 시험할 모델 목록 (서울 리전 기준, 최신 모델 우선)
MODELS_TO_TEST = [
    # (표시 이름, 모델 ID)
    ("Sonnet 4.5 (global 프로필)",  "global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    ("Haiku 4.5 (global 프로필)",   "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
    ("Sonnet 4.5 (apac 프로필)",    "apac.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    ("Sonnet 4 (apac 프로필)",      "apac.anthropic.claude-sonnet-4-20250514-v1:0"),
    ("Haiku 4.5 (apac 프로필)",     "apac.anthropic.claude-haiku-4-5-20251001-v1:0"),
    ("3.7 Sonnet (apac 프로필)",    "apac.anthropic.claude-3-7-sonnet-20250219-v1:0"),
    ("3.5 Sonnet v2 (apac 프로필)", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"),
    ("3.5 Sonnet v1 (apac 프로필)", "apac.anthropic.claude-3-5-sonnet-20240620-v1:0"),
    ("3.5 Sonnet v1 (일반)",        "anthropic.claude-3-5-sonnet-20240620-v1:0"),
    ("3 Haiku (일반)",              "anthropic.claude-3-haiku-20240307-v1:0"),
]


def get_client():
    client_kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return boto3.client("bedrock-runtime", **client_kwargs)


def test_pdf_attach(client, model_id: str, pdf_base64: str):
    """PDF 직접 첨부 방식(invoke_model)을 시험한다."""
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        },
                    },
                    {"type": "text", "text": "이 문서의 제목을 딱 한 줄로만 답해라."},
                ],
            }
        ],
    }

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    body = json.loads(response["body"].read())
    return body["content"][0]["text"].strip()


def main():
    if len(sys.argv) < 2:
        print("사용법: python check_pdf_models.py <PDF 파일 경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

    client = get_client()

    print(f"리전: {AWS_REGION}")
    print(f"PDF: {pdf_path}")
    print("=" * 60)

    success_models = []

    for name, model_id in MODELS_TO_TEST:
        print(f"\n[시험] {name}")
        print(f"       {model_id}")
        try:
            answer = test_pdf_attach(client, model_id, pdf_base64)
            print(f"  ✅ 성공! 모델 응답: {answer[:80]}")
            success_models.append((name, model_id))
        except Exception as e:
            # 에러 메시지의 핵심 부분만 출력
            msg = str(e)
            if len(msg) > 200:
                msg = msg[:200] + "..."
            print(f"  ❌ 실패: {msg}")

    print("\n" + "=" * 60)
    if success_models:
        print("PDF 직접 첨부가 가능한 모델:")
        for name, model_id in success_models:
            print(f"  ✅ {name} → {model_id}")
        print("\n이 중 첫 번째 모델 ID를 알려주면 추출 코드에 반영하면 된다.")
    else:
        print("PDF 직접 첨부가 가능한 모델이 없습니다.")
        print("→ AWS 콘솔(서울 리전) > Bedrock > Model access에서")
        print("  Claude 3.5 Sonnet v2 권한이 켜져 있는지 확인이 필요합니다.")


if __name__ == "__main__":
    main()
