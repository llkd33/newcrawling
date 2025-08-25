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
            time.sleep(5)  # 로그인 대기 시간 증가
            
            logging.info("✅ 네이버 로그인 성공")
            return True
            
        except Exception as e:
            logging.error(f"❌ 로그인 실패: {e}")
            return False
    
    def crawl_cafe(self, cafe_config: Dict) -> List[Dict]:
        """카페 게시물 크롤링"""
        results = []
        
        try:
            # URL 검증
            if not cafe_config.get('url') or not cafe_config.get('club_id') or not cafe_config.get('board_id'):
                logging.error(f"카페 설정이 올바르지 않습니다: {cafe_config}")
                return results
            
            # 카페 게시판 URL로 이동
            board_url = f"{cafe_config['url']}/ArticleList.nhn?search.clubid={cafe_config['club_id']}&search.menuid={cafe_config['board_id']}"
            logging.info(f"📍 URL 접속: {board_url}")
            self.driver.get(board_url)
            time.sleep(3)
            
            # iframe 전환
            try:
                self.driver.switch_to.frame('cafe_main')
                time.sleep(1)
            except:
                logging.warning("iframe 전환 실패, 직접 접근 시도")
            
            # 여러 선택자 시도 (네이버 카페 구조가 다양함)
            selectors = [
                'div.article-board table tbody tr',  # 구형 카페
                'ul.article-movie-sub li',  # 영화형
                'div.ArticleListItem',  # 새형 카페
                'tr[class*="board-list"]',  # 일반 리스트
                'div.inner_list > a'  # 모바일형
            ]
            
            articles = []
            for selector in selectors:
                try:
                    articles = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if articles:
                        logging.info(f"✅ 게시물 발견: {selector} ({len(articles)}개)")
                        break
                except:
                    continue
            
            if not articles:
                logging.warning("❌ 게시물을 찾을 수 없습니다. HTML 구조 확인 필요")
                # HTML 디버깅 정보
                try:
                    page_source = self.driver.page_source[:500]
                    logging.debug(f"Page HTML: {page_source}")
                except:
                    pass
                return results
            
            # 실제 게시물만 필터링 (공지사항 제외)
            actual_articles = []
            for article in articles:
                try:
                    # 공지사항 클래스 체크
                    class_attr = article.get_attribute('class') or ''
                    if 'notice' in class_attr.lower() or '공지' in class_attr:
                        continue
                    actual_articles.append(article)
                except:
                    actual_articles.append(article)
            
            logging.info(f"📊 공지 제외 실제 게시물: {len(actual_articles)}개")
            
            # 최대 4개씩만 처리
            max_articles = 4
            processed_count = 0
            
            for idx, article in enumerate(actual_articles[:10], 1):  # 최신 10개 중에서
                if processed_count >= max_articles:
                    logging.info(f"✅ 최대 처리 개수({max_articles}개) 도달")
                    break
                    
                try:
                    logging.debug(f"처리 중: {processed_count + 1}/{max_articles}")
                    
                    # 제목 찾기 (여러 방법 시도)
                    title = ""
                    link = ""
                    
                    # 방법 1: a.article
                    try:
                        title_elem = article.find_element(By.CSS_SELECTOR, 'a.article')
                        title = title_elem.text.strip()
                        link = title_elem.get_attribute('href')
                    except:
                        pass
                    
                    # 방법 2: td.td_article
                    if not title:
                        try:
                            title_elem = article.find_element(By.CSS_SELECTOR, 'td.td_article a')
                            title = title_elem.text.strip()
                            link = title_elem.get_attribute('href')
                        except:
                            pass
                    
                    # 방법 3: class="inner_list"
                    if not title:
                        try:
                            title_elem = article.find_element(By.CSS_SELECTOR, '.inner_list a')
                            title = title_elem.text.strip()
                            link = title_elem.get_attribute('href')
                        except:
                            pass
                    
                    # 방법 4: 직접 a 태그
                    if not title:
                        try:
                            title_elem = article.find_element(By.TAG_NAME, 'a')
                            title = title_elem.text.strip()
                            link = title_elem.get_attribute('href')
                        except:
                            continue
                    
                    if not title or not link:
                        continue
                    
                    # 공지사항 제외
                    if '공지' in title or 'notice' in str(article.get_attribute('class')):
                        continue
                    
                    # 작성자
                    author = "Unknown"
                    for author_selector in ['td.td_name a', '.td_name', '.nick', '.p-nick']:
                        try:
                            author = article.find_element(By.CSS_SELECTOR, author_selector).text.strip()
                            if author:
                                break
                        except:
                            pass
                    
                    # 작성일
                    date_str = ""
                    for date_selector in ['td.td_date', '.td_date', '.date']:
                        try:
                            date_str = article.find_element(By.CSS_SELECTOR, date_selector).text.strip()
                            if date_str:
                                break
                        except:
                            pass
                    
                    # 날짜 형식 변환 (YYYY.MM.DD. → YYYY-MM-DD)
                    if date_str:
                        # "2025.08.25." 형식을 "2025-08-25"로 변환
                        date_str = date_str.replace('.', '-').rstrip('-')
                        if len(date_str.split('-')) == 3:
                            year, month, day = date_str.split('-')
                            # 2자리 연도 처리
                            if len(year) == 2:
                                year = '20' + year
                            date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        else:
                            date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        date = datetime.now().strftime('%Y-%m-%d')
                    
                    # 조회수
                    views = "0"
                    for view_selector in ['td.td_view', '.td_view', '.view']:
                        try:
                            views = article.find_element(By.CSS_SELECTOR, view_selector).text.strip()
                            if views:
                                break
                        except:
                            pass
                    
                    # 게시물 ID 추출
                    article_id = link.split('articleid=')[-1].split('&')[0] if 'articleid=' in link else ""
                    
                    # URL로 중복 체크 (크롤링 전에 확인)
                    if link:
                        # 이미 노션에 있는지 먼저 체크
                        try:
                            notion_check = NotionDatabase()
                            if notion_check.check_duplicate(link):
                                logging.info(f"⏭️ 이미 저장된 게시물: {title[:30]}...")
                                continue
                        except:
                            pass
                    
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
                        'hash': hashlib.md5(f"{title}{link}".encode()).hexdigest()
                    }
                    
                    results.append(data)
                    processed_count += 1
                    logging.info(f"📄 [{processed_count:02d}/{max_articles}] 크롤링: {title[:30]}...")
                    
                    # 요청 간격
                    time.sleep(1)
                    
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
            # 해시 필드가 없을 수도 있으므로 URL로 중복 체크
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "or": [
                        {
                            "property": "URL",
                            "url": {
                                "contains": hash_value[:20]  # URL 일부로 체크
                            }
                        }
                    ]
                }
            )
            return len(response['results']) > 0
        except Exception as e:
            logging.debug(f"중복 체크 실패: {e}")
            return False
    
    def save_article(self, article: Dict) -> bool:
        """게시물 저장"""
        try:
            # URL로 중복 체크
            if self.check_duplicate(article['url']):
                logging.info(f"⏭️ 중복 게시물 건너뛰기: {article['title'][:30]}...")
                return False
            
            # 노션 DB의 실제 필드에 맞춰서 저장
            properties = {
                "하윗트 어워드 판매(스위트,Goh,클럽)": {  # 제목 필드
                    "title": [{"text": {"content": article['title']}}]
                },
                "URL": {
                    "url": article['url']
                }
            }
            
            # 선택적 필드들 (있으면 추가)
            if article.get('author'):
                properties["작성자"] = {
                    "rich_text": [{"text": {"content": article['author']}}]
                }
            
            if article.get('date'):
                properties["작성일"] = {
                    "date": {"start": article['date']}
                }
            
            if article.get('cafe_name'):
                properties["카페명"] = {
                    "select": {"name": article['cafe_name']}
                }
            
            # 내용 필드 처리
            content = article.get('content', '')[:2000]
            if content:
                properties["내용"] = {
                    "rich_text": [{"text": {"content": content}}]
                }
            
            # 크롤링 일시
            properties["크롤링 일시"] = {
                "date": {"start": datetime.now().isoformat()}
            }
            
            # uploaded 체크박스
            properties["uploaded"] = {
                "checkbox": False
            }
            
            # 노션 페이지 생성
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
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
    
    # 환경변수 확인
    required_env = ['NAVER_ID', 'NAVER_PW', 'NOTION_TOKEN', 'NOTION_DATABASE_ID']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        logging.error(f"❌ 필수 환경변수가 설정되지 않았습니다: {', '.join(missing_env)}")
        logging.error("GitHub Secrets를 설정해주세요!")
        sys.exit(1)
    
    # 카페 설정 (2곳)
    cafes = []
    
    # 카페 1 설정 확인
    if os.getenv('CAFE1_URL') and os.getenv('CAFE1_CLUB_ID') and os.getenv('CAFE1_BOARD_ID'):
        cafes.append({
            'name': os.getenv('CAFE1_NAME', '카페1'),
            'url': os.getenv('CAFE1_URL'),
            'club_id': os.getenv('CAFE1_CLUB_ID'),
            'board_id': os.getenv('CAFE1_BOARD_ID'),
            'board_name': os.getenv('CAFE1_BOARD_NAME', '게시판')
        })
    
    # 카페 2 설정 확인
    if os.getenv('CAFE2_URL') and os.getenv('CAFE2_CLUB_ID') and os.getenv('CAFE2_BOARD_ID'):
        cafes.append({
            'name': os.getenv('CAFE2_NAME', '카페2'),
            'url': os.getenv('CAFE2_URL'),
            'club_id': os.getenv('CAFE2_CLUB_ID'),
            'board_id': os.getenv('CAFE2_BOARD_ID'),
            'board_name': os.getenv('CAFE2_BOARD_NAME', '게시판')
        })
    
    if not cafes:
        logging.error("❌ 크롤링할 카페가 설정되지 않았습니다!")
        logging.error("최소 1개 이상의 카페 정보를 GitHub Secrets에 설정해주세요:")
        logging.error("CAFE1_URL, CAFE1_CLUB_ID, CAFE1_BOARD_ID")
        sys.exit(1)
    
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
            cafe_saved = 0
            for article in articles:
                if notion.save_article(article):
                    cafe_saved += 1
                    total_saved += 1
            
            logging.info(f"✅ {cafe['name']}: {len(articles)}개 크롤링, {cafe_saved}개 새로 저장")
            time.sleep(2)
        
        logging.info(f"\n🎉 크롤링 완료! 총 {total_saved}개 새 게시물 저장")
        
    except Exception as e:
        logging.error(f"❌ 크롤링 실패: {e}")
        sys.exit(1)
    
    finally:
        crawler.close()


if __name__ == "__main__":
    main()