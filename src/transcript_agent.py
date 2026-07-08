# src/transcript_agent.py
from .transcript_ai_extractor import extract_transcript_data_with_ai

def analyze_transcript_pdf(pdf_path: str) -> dict:
    """
    외부에서 호출하는 메인 함수. 
    PDF 경로를 받아 최종 분석된 JSON(dict) 데이터를 반환합니다.
    """
    print(f"[*] '{pdf_path}' 성적증명서 분석을 시작합니다...")
    
    # AI 추출 로직 호출
    transcript_data = extract_transcript_data_with_ai(pdf_path)
    
    # 기본적인 데이터 무결성 검증 (필요한 경우)
    if transcript_data.get("extraction_confidence") == "low":
        print("[!] AI가 데이터를 추출하는 데 어려움을 겪었거나 오류가 발생했습니다.")
    
    # 빈 값이 들어가면 안 되는 필수 키 확인
    required_keys = ["department", "total_credits", "completed_courses"]
    for key in required_keys:
        if key not in transcript_data:
            transcript_data["warnings"].append(f"필수 누락 데이터: {key}")
            
    print("[*] 성적증명서 분석 완료.")
    return transcript_data

# 단독 실행 테스트용
if __name__ == "__main__":
    test_pdf = "data/samples/sample_transcript_anonymized.pdf"
    result = analyze_transcript_pdf(test_pdf)
    
    # 결과를 보기 좋게 출력
    import json
    print(json.dumps(result, indent=4, ensure_ascii=False))
