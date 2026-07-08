# src/config.py
# 공통 설정 파일.
# 보안 규칙: AWS 키를 이 파일에 직접 쓰지 말 것! (공개 저장소 노출 위험)
# 키는 프로젝트 루트의 .env 파일이나 환경변수로 설정한다.
#   .env 예시:
#     AWS_ACCESS_KEY=발급받은키
#     AWS_SECRET_KEY=발급받은시크릿키

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

TEMPERATURE = 0

MAX_TOKENS = 2048

# 환경변수에서 읽는다. 없으면 빈 문자열 → boto3 기본 자격증명 체인 사용
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
