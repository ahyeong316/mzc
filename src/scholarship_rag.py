import boto3
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
KB_ID = os.getenv("KB_ID", "UX5APWPITZ")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

def get_client():
    client_kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return boto3.client("bedrock-agent-runtime", **client_kwargs)

def get_scholarship_policy() -> dict:
    client = get_client()
    query = "순천대학교 성적우수장학금 및 국가장학금 등 주요 장학금 선발 기준과 요건"
    
    response = client.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 3}},
    )
    
    context_text = "\n".join([item['content']['text'] for item in response.get('retrievalResults', [])])
    
    if not context_text.strip():
        raise ValueError("검색된 장학금 정보가 없습니다.")
        
    return {
        "source": "bedrock_knowledge_base",
        "last_synced_at": datetime.now().strftime("%Y-%m-%d"),
        "content": context_text
    }

if __name__ == "__main__":
    print(get_scholarship_policy())
