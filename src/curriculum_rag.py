import boto3
import json
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
KB_ID = os.getenv("KB_ID", "UX5APWPITZ")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
MODEL_ARN = os.getenv("BEDROCK_MODEL_ID", f"arn:aws:bedrock:{AWS_REGION}::foundation-model/global.anthropic.claude-sonnet-4-5-20250929-v1:0")

def get_client():
    client_kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
    return boto3.client("bedrock-agent-runtime", **client_kwargs)

def get_curriculum_requirements(department: str, student_year: str = None):
    client = get_client()
    
    year_text = f"{student_year} 학번(입학생) 기준 " if student_year else ""
    
    query = f"""
    {year_text}{department}의 졸업 요건(졸업 인정 학점, 전공 이수 학점 등)을 검색해서 아래의 JSON 형식으로만 응답해줘. 다른 설명은 붙이지 마.
    [중요 힌트]
    1. 이 정보는 PDF 내에서 표(Table) 형태로 되어 있을 가능성이 높습니다. '학과(부)' 열에서 '{department}'를 찾고, 해당 가로줄에 있는 '졸업 인정 학점'을 전체 졸업학점으로, '전공(최소이수학점)'의 합계를 전공학점으로 파악하세요.
    2. 교양 학점은 '교양 합계'를 확인하세요.
    3. 정확한 숫자를 찾을 수 없다면 절대 지어내지 말고 반드시 null 로 설정해라.
    {{
        "required_total_credits": 숫자 또는 null,
        "required_major_credits": 숫자 또는 null,
        "required_general_credits": 숫자 또는 null,
        "required_courses": ["과목명1", "과목명2"] 또는 null
    }}
    """
    
    try:
        response = client.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': MODEL_ARN
                }
            }
        )
        
        response_text = response['output']['text']
        match = re.search(r"\{[\s\S]*\}", response_text)
        
        if match:
            # AI가 반환한 텍스트에서 JSON 추출
            result = json.loads(match.group(0), strict=False)
            result["department"] = department
            result["status"] = "success"
            return json.dumps(result, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "message": "AI 응답에서 JSON을 찾지 못했습니다."})
            
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    dept = "컴퓨터공학과"
    print(f"--- {dept} 데이터 추출 시작 ---")
    json_data = get_curriculum_requirements(dept)
    print(json_data)