# src/curriculum_rag.py
import boto3
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 보안 규칙: 키를 코드에 직접 쓰지 말 것! .env 파일에서 읽는다.
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
KB_ID = os.getenv("KB_ID", "UX5APWPITZ")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

def get_client():
    # 키가 .env에 있으면 사용, 없으면 boto3 기본 자격증명 체인 사용
    client_kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return boto3.client("bedrock-agent-runtime", **client_kwargs)

def get_curriculum_requirements(department: str):
    client = get_client()
    query = f"{department}의 졸업 요건과 전공 필수, 전공 선택, 총 졸업 학점을 정리해줘."
    
    response = client.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 3}},
    )
    
    # 검색된 텍스트 합치기
    context_text = "\n".join([item['content']['text'] for item in response['retrievalResults']])
    
    # 팀원에게 줄 JSON 구조 만들기
    # 실제로는 여기서 AI에게 요약을 시키지만, 일단은 검색된 데이터를 구조화합니다
    result = {
        "department": department,
        "summary": context_text[:100] + "...", # 검색된 데이터 요약
        "status": "success",
        "data_format": "structured"
    }
    
    return json.dumps(result, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    dept = "컴퓨터공학과"
    print(f"--- {dept} 데이터 추출 시작 ---")
    json_data = get_curriculum_requirements(dept)
    print(json_data)