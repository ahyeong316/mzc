# src/curriculum_sync.py
import requests
from bs4 import BeautifulSoup

# 게시판 페이지 URL
BOARD_URL = "https://www.scnu.ac.kr/haksa/na/ntt/selectNttList.do?mi=1424&bbsId=1158"

def sync_latest_curriculum_pdf():
    print("홈페이지 전체에서 PDF 파일을 탐색하는 중...")
    
    try:
        # User-Agent를 추가해서 브라우저인 것처럼 위장 (봇 차단 방지)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(BOARD_URL, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 페이지 내의 모든 <a> 태그 중 href에 .pdf가 포함된 것을 찾음
        pdf_links = soup.find_all('a', href=True)
        
        found = False
        for link in pdf_links:
            if '.pdf' in link['href'].lower():
                full_url = link['href']
                # 상대 경로라면 도메인을 붙여줌
                if not full_url.startswith('http'):
                    full_url = "https://www.scnu.ac.kr" + full_url
                
                print(f"찾았다! PDF 링크: {full_url}")
                found = True
        
        if not found:
            print("현재 페이지에서는 PDF 링크를 직접 찾지 못했습니다.")
            print("아마도 PDF 링크가 자바스크립트 함수(onclick) 안에 들어있을 가능성이 높습니다.")
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    sync_latest_curriculum_pdf()