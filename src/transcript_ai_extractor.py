# src/transcript_ai_extractor.py
import json
import base64
import boto3
from .prompts import TRANSCRIPT_EXTRACTION_PROMPT

# 🌟 아까 만든 비밀 금고(config.py)에서 AWS 키 불러오기!
from config import AWS_ACCESS_KEY, AWS_SECRET_KEY

def extract_transcript_data_with_ai(pdf_path: str) -> dict:
    """PDF 파일을 읽고 AWS Bedrock AI 모델을 통해 JSON 데이터를 추출합니다."""
    
    try:
        # 1. AWS Bedrock 클라이언트 설정 (비밀 금고 키 사용)
        client = boto3.client(
            'bedrock-runtime', 
            region_name='ap-northeast-2',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        # 2. 모델 설정 (PDF 멀티모달 인식이 뛰어난 Claude 3.5 Sonnet 사용)
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

        # 3. PDF 파일을 읽어서 Base64 문자열로 인코딩
        with open(pdf_path, "rb") as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')

        # 4. 프롬프트와 파일 전송을 위한 Payload 구성
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": "너는 대학교 성적증명서 분석 AI 에이전트다. 결과를 반드시 JSON 형식으로만 출력해라.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": TRANSCRIPT_EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
        }

        # 5. AWS Bedrock API 호출
        response = client.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(payload)
        )
        
        # 6. 응답 텍스트 추출
        response_body = json.loads(response.get('body').read())
        raw_text = response_body['content'][0]['text'].strip()
        
        # 7. 마크다운 제거 (질문자님 기존 코드 유지)
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        # JSON(dict)으로 파싱
        transcript_data = json.loads(raw_text)
        return transcript_data

    except json.JSONDecodeError:
        return {
            "warnings": ["AI 응답을 JSON으로 변환하는 데 실패했습니다."],
            "extraction_confidence": "low"
        }
    except Exception as e:
        return {
            "warnings": [f"AWS Bedrock 모델 호출 중 오류 발생: {str(e)}"],
            "extraction_confidence": "low"
        }