# src/sync_kb.py
import boto3

# 본인의 ID로 수정하세요
KB_ID = "UX5APWPITZ" 
DS_ID = "SY2DOGJFWX" 

def trigger_kb_sync():
    client = boto3.client("bedrock-agent")
    try:
        response = client.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DS_ID
        )
        print("=== 데이터 동기화 시작 ===")
        print(f"작업 ID: {response['ingestionJob']['ingestionJobId']}")
        print("AWS Knowledge Base가 최신 PDF를 학습하기 시작했습니다.")
    except Exception as e:
        print(f"동기화 실패: {e}")

if __name__ == "__main__":
    trigger_kb_sync()