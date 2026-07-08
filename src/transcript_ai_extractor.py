# src/transcript_ai_extractor.py
import json
import base64
import boto3
from .prompt import TRANSCRIPT_EXTRACTION_PROMPT
from .config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION

import os

# 진단 결과(2026-07 서울 리전 기준) 시도 순서:
#   1순위: Sonnet 4.5 (global 프로필) - 최신, 문서 판독 정확도 최상
#   2순위: 3.5 Sonnet v2 (apac 프로필) - PDF 첨부 성공 확인됨
#   3순위: 3.5 Sonnet v1 (apac 프로필) - PDF 첨부 성공 확인됨
#   예비:  Haiku 3 - PDF 첨부 미지원, 텍스트 방식 예비용
# ※ global 프로필은 요청이 해외 리전에서 처리될 수 있음 (개인정보 처리 위치 유의)
# .env에 TRANSCRIPT_MODEL_ID를 넣으면 그 모델을 가장 먼저 시도한다.
MODEL_ID_CANDIDATES = [
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
]

_env_model = os.getenv("TRANSCRIPT_MODEL_ID")
if _env_model:
    MODEL_ID_CANDIDATES = [_env_model] + [
        m for m in MODEL_ID_CANDIDATES if m != _env_model
    ]


def _get_client():
    # 키가 .env에 있으면 사용, 없으면 boto3 기본 자격증명 체인 사용
    client_kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return boto3.client("bedrock-runtime", **client_kwargs)


def _invoke_model(client, model_id: str, content: list) -> str:
    """Bedrock 모델을 호출하고 응답 텍스트를 반환한다."""
    # 과목 수가 많으면 JSON이 길어지므로 출력 한도를 넉넉히 잡는다.
    # (Claude 3 Haiku는 최대 4096까지만 지원)
    max_tokens = 4096 if "haiku" in model_id else 8192

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": "너는 대학교 성적증명서 분석 AI 에이전트다. 결과를 반드시 JSON 형식으로만 출력해라.",
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )

    response_body = json.loads(response.get("body").read())
    return response_body["content"][0]["text"].strip()


def _extract_pdf_text(pdf_path: str) -> str:
    """PDF에서 텍스트를 직접 추출한다 (PDF 첨부 호출 실패 시 예비 경로)."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _parse_json_response(raw_text: str) -> dict:
    """마크다운 코드블록을 제거하고 JSON으로 파싱한다."""
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:-3].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:-3].strip()

    return json.loads(raw_text)


def extract_transcript_data_with_ai(pdf_path: str) -> dict:
    """PDF 파일을 읽고 AWS Bedrock AI 모델을 통해 JSON 데이터를 추출합니다.

    1차 시도: PDF 파일을 그대로 첨부해서 분석 (멀티모달)
    2차 시도: PDF에서 텍스트를 추출해서 텍스트로 분석
    모델 ID는 서울 리전용 교차리전 프로필(apac.)부터 순서대로 시도한다.
    """
    errors = []

    try:
        client = _get_client()

        with open(pdf_path, "rb") as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode("utf-8")

        # ── 1차: PDF 직접 첨부 ──
        pdf_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_base64,
                },
            },
            {"type": "text", "text": TRANSCRIPT_EXTRACTION_PROMPT},
        ]

        for model_id in MODEL_ID_CANDIDATES:
            try:
                raw_text = _invoke_model(client, model_id, pdf_content)
                return _parse_json_response(raw_text)
            except json.JSONDecodeError:
                errors.append(f"[{model_id}] AI 응답 JSON 파싱 실패")
            except Exception as e:
                errors.append(f"[{model_id}] PDF 첨부 호출 실패: {e}")

        # ── 2차: PDF 텍스트 추출 후 텍스트로 분석 ──
        pdf_text = _extract_pdf_text(pdf_path)

        if pdf_text:
            text_content = [
                {
                    "type": "text",
                    "text": (
                        TRANSCRIPT_EXTRACTION_PROMPT
                        + "\n\n[성적증명서 내용]\n"
                        + pdf_text[:15000]
                    ),
                },
            ]

            for model_id in MODEL_ID_CANDIDATES:
                try:
                    raw_text = _invoke_model(client, model_id, text_content)
                    result = _parse_json_response(raw_text)
                    result.setdefault("warnings", []).append(
                        "PDF 첨부 분석이 실패하여 텍스트 추출 방식으로 분석했습니다."
                    )
                    return result
                except json.JSONDecodeError:
                    errors.append(f"[{model_id}] 텍스트 방식 JSON 파싱 실패")
                except Exception as e:
                    errors.append(f"[{model_id}] 텍스트 방식 호출 실패: {e}")
        else:
            errors.append("PDF에서 텍스트를 추출하지 못했습니다 (스캔 이미지 PDF일 수 있음).")

    except Exception as e:
        errors.append(f"AWS Bedrock 준비 중 오류 발생: {e}")

    return {
        "warnings": errors,
        "extraction_confidence": "low",
    }
