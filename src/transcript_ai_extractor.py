# src/transcript_ai_extractor.py
import json
# 예시로 google-generativeai 라이브러리를 사용한다고 가정합니다.
import google.generativeai as genai
from .prompts import TRANSCRIPT_EXTRACTION_PROMPT

def extract_transcript_data_with_ai(pdf_path: str) -> dict:
    """PDF 파일을 읽고 AI 모델을 통해 JSON 데이터를 추출합니다."""
    
    try:
        # 1. PDF 파일을 AI 모델에 업로드 (Gemini API 예시)
        pdf_file = genai.upload_file(path=pdf_path)
        
        # 2. 모델 설정 (PDF를 읽을 수 있는 멀티모달 모델 사용 및 JSON 응답 강제)
        # generation_config를 통해 JSON 형태로 반환되도록 유도할 수 있습니다.
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 3. 프롬프트와 파일 전송
        response = model.generate_content([TRANSCRIPT_EXTRACTION_PROMPT, pdf_file])
        
        # 4. 텍스트 응답을 JSON(dict)으로 파싱
        # AI가 혹시라도 코드 블록(```json)을 포함했다면 제거하는 안전장치
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        transcript_data = json.loads(raw_text)
        return transcript_data

    except json.JSONDecodeError:
        return {
            "warnings": ["AI 응답을 JSON으로 변환하는 데 실패했습니다."],
            "extraction_confidence": "low"
        }
    except Exception as e:
        return {
            "warnings": [f"AI 모델 호출 중 오류 발생: {str(e)}"],
            "extraction_confidence": "low"
        }