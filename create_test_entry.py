#!/usr/bin/env python3
"""
노션 데이터베이스에 테스트 항목 생성
Title 필드를 찾기 위한 스크립트
"""

import os
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime

load_dotenv()

def create_test_entry():
    """테스트 항목 생성"""
    client = Client(auth=os.getenv('NOTION_TOKEN'))
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    # 가능한 Title 필드명들
    possible_titles = [
        'Name', 'name', '이름', '제목', 'Title', 'title',
        '하윗트 어워드 판매(스위트,Goh,클럽)', 
        'Name (Title)', 'Title (Name)'
    ]
    
    for title_field in possible_titles:
        try:
            print(f"시도: {title_field}")
            
            # 최소한의 필드로 테스트
            properties = {
                title_field: {
                    "title": [{"text": {"content": "테스트 항목"}}]
                }
            }
            
            # URL 필드도 추가 (있으면)
            try:
                properties["URL"] = {"url": "https://example.com"}
            except:
                pass
            
            # 페이지 생성 시도
            page = client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            
            print(f"✅ 성공! Title 필드명: {title_field}")
            print(f"생성된 페이지 ID: {page['id']}")
            
            # 성공하면 환경변수 설정 안내
            print("\n" + "="*60)
            print("GitHub Secrets에 추가하세요:")
            print(f"NOTION_TITLE_FIELD: {title_field}")
            print("="*60)
            
            return title_field
            
        except Exception as e:
            print(f"  ❌ 실패: {str(e)[:100]}")
            continue
    
    print("\n❌ Title 필드를 찾을 수 없습니다.")
    print("노션 데이터베이스를 확인하세요.")

if __name__ == "__main__":
    create_test_entry()