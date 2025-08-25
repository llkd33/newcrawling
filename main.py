#!/usr/bin/env python3
"""
네이버 카페 크롤링 -> 노션 저장 메인 스크립트
매일 정기적으로 실행되어 새 게시물을 크롤링하고 노션에 저장
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv
import hashlib

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Notion imports
from notion_client import Client

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('crawler.log', encoding='utf-8')
    ]
)

class NaverCafeCrawler:
    """네이버 카페 크롤러"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.setup_driver()
        
    def setup_driver(self):
        """Selenium 드라이버 설정"""
        options = Options()
        
        # GitHub Actions 환경에서는 헤드리스 모드 필수
        if os.getenv('GITHUB_ACTIONS'):
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
        
        # 기본 옵션
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            logging.info("✅ 크롬 드라이버 초기화 성공")
        except Exception as e:
            logging.error(f"❌ 드라이버 초기화 실패: {e}")
            raise
    
    def login_naver(self):
        """네이버 로그인"""
        try:
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            
            # ID 입력
            id_input = self.driver.find_element(By.ID, 'id')
            id_input.send_keys(os.getenv('NAVER_ID'))
            time.sleep(1)
            
            # PW 입력
            pw_input = self.driver.find_element(By.ID, 'pw')
            pw_input.send_keys(os.getenv('NAVER_PW'))
            time.sleep(1)
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, 'log.login')
            login_btn.click()
            time.sleep(3)
            
            logging.info("✅ 네이버 로그인 성공")
            return True
            
        except Exception as e:
            logging.error(f"❌ 로그인 실패: {e}")
            return False
    
    def crawl_cafe(self, cafe_config: Dict) -> List[Dict]:
        """카페 게시물 크롤링"""
        results = []
        
        try:
            # 카페 게시판 URL로 이동
            board_url = f"{cafe_config['url']}/ArticleList.nhn?search.clubid={cafe_config['club_id']}&search.menuid={cafe_config['board_id']}"
            self.driver.get(board_url)
            time.sleep(3)
            
            # iframe 전환
            self.driver.switch_to.frame('cafe_main')
            time.sleep(1)
            
            # 게시물 목록 가져오기
            articles = self.driver.find_elements(By.CSS_SELECTOR, 'div.article-board tr')
            
            for article in articles[:10]:  # 최신 10개만
                try:
                    # 공지사항 제외
                    if 'board-notice' in article.get_attribute('class') or '':
                        continue
                    
                    # 제목과 링크
                    title_elem = article.find_element(By.CSS_SELECTOR, 'a.article')
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute('href')
                    
                    # 작성자
                    try:
                        author = article.find_element(By.CSS_SELECTOR, 'td.td_name a').text.strip()
                    except:
                        author = "Unknown"
                    
                    # 작성일
                    try:
                        date = article.find_element(By.CSS_SELECTOR, 'td.td_date').text.strip()
                    except:
                        date = datetime.now().strftime('%Y.%m.%d.')
                    
                    # 조회수
                    try:
                        views = article.find_element(By.CSS_SELECTOR, 'td.td_view').text.strip()
                    except:
                        views = "0"
                    
                    # 게시물 ID 추출
                    article_id = link.split('articleid=')[-1].split('&')[0] if 'articleid=' in link else ""
                    
                    # 상세 내용 크롤링
                    content = self.get_article_content(link)
                    
                    # 데이터 구성
                    data = {
                        'title': title,
                        'author': author,
                        'date': date,
                        'views': views,
                        'url': link,
                        'article_id': article_id,
                        'content': content,
                        'cafe_name': cafe_config['name'],
                        'board_name': cafe_config['board_name'],
                        'crawled_at': datetime.now().isoformat(),
                        'hash': hashlib.md5(f"{title}{content}".encode()).hexdigest()
                    }
                    
                    results.append(data)
                    logging.info(f"📄 크롤링: {title[:30]}...")
                    time.sleep(1)  # 요청 간격
                    
                except Exception as e:
                    logging.error(f"게시물 크롤링 오류: {e}")
                    continue
            
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logging.error(f"카페 크롤링 오류: {e}")
        
        return results
    
    def get_article_content(self, url: str) -> str:
        """게시물 상세 내용 가져오기"""
        try:
            # 새 탭에서 열기
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(2)
            
            # iframe 전환
            self.driver.switch_to.frame('cafe_main')
            
            # 본문 내용 추출
            content = ""
            try:
                content_elem = self.driver.find_element(By.CSS_SELECTOR, 'div.se-main-container, div.content-box')
                content = content_elem.text.strip()
            except:
                try:
                    content_elem = self.driver.find_element(By.CSS_SELECTOR, 'div#tbody')
                    content = content_elem.text.strip()
                except:
                    content = ""
            
            # 탭 닫기
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            return content[:2000]  # 노션 제한
            
        except Exception as e:
            logging.error(f"내용 추출 오류: {e}")
            return ""
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            logging.info("✅ 드라이버 종료")


class NotionDatabase:
    """노션 데이터베이스 핸들러"""
    
    def __init__(self):
        self.client = Client(auth=os.getenv('NOTION_TOKEN'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
    
    def check_duplicate(self, hash_value: str) -> bool:
        """중복 체크"""
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "해시",
                    "rich_text": {
                        "contains": hash_value
                    }
                }
            )
            return len(response['results']) > 0
        except:
            return False
    
    def save_article(self, article: Dict) -> bool:
        """게시물 저장"""
        try:
            # 중복 체크
            if self.check_duplicate(article['hash']):
                logging.info(f"⏭️ 중복 게시물 건너뛰기: {article['title'][:30]}...")
                return False
            
            # 노션 페이지 생성
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "제목": {
                        "title": [{"text": {"content": article['title']}}]
                    },
                    "URL": {
                        "url": article['url']
                    },
                    "작성자": {
                        "rich_text": [{"text": {"content": article['author']}}]
                    },
                    "작성일": {
                        "date": {"start": article['date']}
                    },
                    "카페명": {
                        "select": {"name": article['cafe_name']}
                    },
                    "내용": {
                        "rich_text": [{"text": {"content": article['content'][:2000]}}]
                    },
                    "크롤링 일시": {
                        "date": {"start": article['crawled_at']}
                    },
                    "조회수": {
                        "number": int(article.get('views', 0))
                    },
                    "게시물 ID": {
                        "rich_text": [{"text": {"content": article.get('article_id', '')}}]
                    },
                    "해시": {
                        "rich_text": [{"text": {"content": article['hash']}}]
                    },
                    "uploaded": {
                        "checkbox": False
                    }
                }
            )
            
            logging.info(f"✅ 노션 저장 성공: {article['title'][:30]}...")
            return True
            
        except Exception as e:
            logging.error(f"❌ 노션 저장 실패: {e}")
            return False


def main():
    """메인 실행 함수"""
    logging.info("="*60)
    logging.info("🚀 네이버 카페 -> 노션 크롤링 시작")
    logging.info(f"⏰ 실행 시간: {datetime.now()}")
    logging.info("="*60)
    
    # 카페 설정 (2곳)
    cafes = [
        {
            'name': os.getenv('CAFE1_NAME', '카페1'),
            'url': os.getenv('CAFE1_URL'),
            'club_id': os.getenv('CAFE1_CLUB_ID'),
            'board_id': os.getenv('CAFE1_BOARD_ID'),
            'board_name': os.getenv('CAFE1_BOARD_NAME', '게시판')
        },
        {
            'name': os.getenv('CAFE2_NAME', '카페2'),
            'url': os.getenv('CAFE2_URL'),
            'club_id': os.getenv('CAFE2_CLUB_ID'),
            'board_id': os.getenv('CAFE2_BOARD_ID'),
            'board_name': os.getenv('CAFE2_BOARD_NAME', '게시판')
        }
    ]
    
    # 크롤러 초기화
    crawler = NaverCafeCrawler()
    notion = NotionDatabase()
    
    try:
        # 네이버 로그인
        if not crawler.login_naver():
            raise Exception("로그인 실패")
        
        total_saved = 0
        
        # 각 카페 크롤링
        for cafe in cafes:
            logging.info(f"\n📍 {cafe['name']} 크롤링 시작...")
            articles = crawler.crawl_cafe(cafe)
            
            # 노션에 저장
            for article in articles:
                if notion.save_article(article):
                    total_saved += 1
            
            logging.info(f"✅ {cafe['name']}: {len(articles)}개 크롤링, {total_saved}개 저장")
            time.sleep(2)
        
        logging.info(f"\n🎉 크롤링 완료! 총 {total_saved}개 새 게시물 저장")
        
    except Exception as e:
        logging.error(f"❌ 크롤링 실패: {e}")
        sys.exit(1)
    
    finally:
        crawler.close()


if __name__ == "__main__":
    main()