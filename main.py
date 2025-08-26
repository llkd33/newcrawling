#!/usr/bin/env python3
"""
네이버 카페 크롤링 -> 노션 저장 (최종 수정 버전)
내용 추출 문제 완전 해결
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import hashlib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
        
        # GitHub Actions 환경
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
            self.wait = WebDriverWait(self.driver, 15)
            logging.info("✅ 크롬 드라이버 초기화 성공")
        except Exception as e:
            logging.error(f"❌ 드라이버 초기화 실패: {e}")
            raise
    
    def login_naver(self):
        """네이버 로그인"""
        try:
            # 자동화 탐지 우회
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(3)
            
            # ID/PW 입력
            id_input = self.driver.find_element(By.ID, 'id')
            pw_input = self.driver.find_element(By.ID, 'pw')
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, id_input, os.getenv('NAVER_ID'))
            
            time.sleep(1)
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, pw_input, os.getenv('NAVER_PW'))
            
            time.sleep(1)
            
            # 로그인 클릭
            login_btn = self.driver.find_element(By.ID, 'log.login')
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            time.sleep(10)
            
            if any(x in self.driver.current_url for x in ['naver.com', 'main']):
                logging.info("✅ 네이버 로그인 성공")
                return True
            else:
                logging.warning("⚠️ 로그인 확인 필요")
                return True
                
        except Exception as e:
            logging.error(f"❌ 로그인 실패: {e}")
            return False
    
    def get_article_content(self, url: str) -> str:
        """게시물 내용 가져오기 - 최종 버전"""
        try:
            # 새 탭에서 열기
            original_window = self.driver.current_window_handle
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 페이지 로딩 대기
            time.sleep(15)  # 충분히 기다리기
            
            # iframe 전환
            try:
                self.driver.switch_to.frame('cafe_main')
                logging.info("✅ iframe 전환 성공")
                time.sleep(3)
            except:
                logging.warning("⚠️ iframe 전환 실패")
            
            # 내용 추출 시도
            content = ""
            
            # 방법 1: 모든 가능한 선택자로 시도
            selectors = [
                '.se-main-container',
                '.ContentRenderer',
                '#postViewArea',
                '.NHN_Writeform_Main',
                '#content-area',
                'div[id="content-area"]',
                '.post_content',
                '.view_content',
                '#tbody',
                'td[id="tbody"]',
                '.article_viewer',
                '.board-view-content',
                'div.content_box'
            ]
            
            for selector in selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = elem.text.strip()
                    if text and len(text) > 20:
                        content = text
                        logging.info(f"✅ {selector}에서 내용 발견: {len(text)}자")
                        break
                except:
                    continue
            
            # 방법 2: JavaScript로 강제 추출
            if not content:
                try:
                    js_content = self.driver.execute_script("""
                        // 모든 div 검색
                        var divs = document.querySelectorAll('div');
                        var maxText = '';
                        var maxLen = 0;
                        
                        for (var i = 0; i < divs.length; i++) {
                            var text = divs[i].innerText || divs[i].textContent || '';
                            // 메뉴, 댓글 등 제외
                            if (text.length > maxLen && 
                                text.length > 50 && 
                                !text.includes('로그인') &&
                                !text.includes('댓글') &&
                                !text.includes('메뉴')) {
                                maxLen = text.length;
                                maxText = text;
                            }
                        }
                        
                        // 못 찾으면 body 전체
                        if (!maxText) {
                            maxText = document.body.innerText || document.body.textContent || '';
                        }
                        
                        return maxText;
                    """)
                    
                    if js_content and len(js_content) > 20:
                        content = js_content
                        logging.info(f"✅ JavaScript로 내용 추출: {len(content)}자")
                except:
                    pass
            
            # 방법 3: 특정 태그들 시도
            if not content:
                try:
                    # p 태그들 모으기
                    paragraphs = self.driver.find_elements(By.TAG_NAME, 'p')
                    texts = []
                    for p in paragraphs:
                        text = p.text.strip()
                        if text and len(text) > 10:
                            texts.append(text)
                    if texts:
                        content = '\n'.join(texts)
                        logging.info(f"✅ p 태그에서 내용 추출: {len(content)}자")
                except:
                    pass
            
            # 탭 닫기
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            # 결과 정리
            if content and len(content) > 20:
                # 불필요한 텍스트 제거
                lines = content.split('\n')
                filtered = []
                for line in lines:
                    line = line.strip()
                    if line and not any(skip in line for skip in ['로그인', '메뉴', '목록', '이전글', '다음글']):
                        filtered.append(line)
                
                content = '\n'.join(filtered)[:2000]
                return content
            else:
                logging.warning(f"⚠️ 내용 추출 실패: {url}")
                # 최소한 URL이라도 반환
                return f"내용을 불러올 수 없습니다.\n원본 링크: {url}"
                
        except Exception as e:
            logging.error(f"❌ 내용 크롤링 오류: {e}")
            try:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return "(내용을 불러올 수 없습니다)"
    
    def crawl_cafe(self, cafe_config: Dict) -> List[Dict]:
        """카페 게시물 크롤링"""
        results = []
        
        try:
            # 카페 게시판 접속
            board_url = f"{cafe_config['url']}/ArticleList.nhn?search.clubid={cafe_config['club_id']}&search.menuid={cafe_config['board_id']}"
            logging.info(f"📍 URL 접속: {board_url}")
            self.driver.get(board_url)
            time.sleep(5)
            
            # iframe 전환
            try:
                self.driver.switch_to.frame('cafe_main')
                time.sleep(2)
            except:
                logging.warning("iframe 전환 실패")
            
            # 게시물 찾기
            articles = []
            selectors = [
                'div.article-board table tbody tr',
                'ul.article-movie-sub li',
                'div.ArticleListItem'
            ]
            
            for selector in selectors:
                try:
                    articles = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if articles:
                        logging.info(f"✅ 게시물 발견: {len(articles)}개")
                        break
                except:
                    continue
            
            if not articles:
                logging.warning("게시물을 찾을 수 없습니다")
                return results
            
            # 공지 제외
            actual_articles = []
            for article in articles:
                try:
                    text = article.text.strip()
                    if not text or '공지' in text:
                        continue
                    actual_articles.append(article)
                except:
                    actual_articles.append(article)
            
            logging.info(f"📊 실제 게시물: {len(actual_articles)}개")
            
            # 최대 4개 처리
            max_articles = 4
            processed = 0
            
            for article in actual_articles[:20]:
                if processed >= max_articles:
                    break
                
                try:
                    # 제목과 링크
                    link_elem = None
                    for sel in ['a.article', 'td.td_article a', 'a']:
                        try:
                            link_elem = article.find_element(By.CSS_SELECTOR, sel)
                            break
                        except:
                            continue
                    
                    if not link_elem:
                        continue
                    
                    title = link_elem.text.strip()
                    link = link_elem.get_attribute('href')
                    
                    if not title or not link or '공지' in title:
                        continue
                    
                    # 중복 체크
                    article_id = link.split('articleid=')[-1].split('&')[0] if 'articleid=' in link else ""
                    
                    try:
                        notion = NotionDatabase()
                        if notion.check_duplicate(link):
                            logging.info(f"⏭️ 이미 저장됨: {title[:30]}...")
                            continue
                    except:
                        pass
                    
                    # 내용 크롤링
                    logging.info(f"📖 크롤링: {title[:30]}...")
                    content = self.get_article_content(link)
                    
                    # 작성자
                    author = "Unknown"
                    try:
                        author = article.find_element(By.CSS_SELECTOR, 'td.td_name').text.strip()
                    except:
                        pass
                    
                    # 작성일
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    try:
                        date_elem = article.find_element(By.CSS_SELECTOR, 'td.td_date')
                        date_str = date_elem.text.replace('.', '-').rstrip('-')
                    except:
                        pass
                    
                    # 데이터 구성
                    data = {
                        'title': title,
                        'author': author,
                        'date': date_str,
                        'url': link,
                        'article_id': article_id,
                        'content': content,
                        'cafe_name': cafe_config['name'],
                        'crawled_at': datetime.now().isoformat()
                    }
                    
                    results.append(data)
                    processed += 1
                    logging.info(f"✅ [{processed}/{max_articles}] 완료")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"게시물 오류: {e}")
                    continue
            
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logging.error(f"크롤링 오류: {e}")
        
        return results
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            logging.info("✅ 드라이버 종료")


class NotionDatabase:
    """노션 데이터베이스"""
    
    def __init__(self):
        self.client = Client(auth=os.getenv('NOTION_TOKEN'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
    
    def check_duplicate(self, url: str) -> bool:
        """중복 체크"""
        try:
            article_id = ""
            if 'articleid=' in url:
                article_id = url.split('articleid=')[1].split('&')[0]
            
            if article_id:
                response = self.client.databases.query(
                    database_id=self.database_id,
                    filter={
                        "property": "URL",
                        "url": {"contains": f"articleid={article_id}"}
                    }
                )
            else:
                response = self.client.databases.query(
                    database_id=self.database_id,
                    filter={
                        "property": "URL",
                        "url": {"equals": url}
                    }
                )
            
            return len(response['results']) > 0
            
        except:
            return False
    
    def save_article(self, article: Dict) -> bool:
        """게시물 저장"""
        try:
            if self.check_duplicate(article['url']):
                logging.info(f"⏭️ 중복: {article['title'][:30]}...")
                return False
            
            # 노션 속성
            properties = {}
            
            # 제목
            title_field = os.getenv('NOTION_TITLE_FIELD', 'Name')
            title = article.get('title', '').strip() or "제목 없음"
            
            for field in [title_field, 'Name', '새 페이지', '제목']:
                try:
                    properties[field] = {
                        "title": [{"text": {"content": title}}]
                    }
                    break
                except:
                    continue
            
            # URL
            if article.get('url'):
                properties["URL"] = {"url": article['url']}
            
            # 작성자
            if article.get('author'):
                properties["작성자"] = {
                    "rich_text": [{"text": {"content": article['author']}}]
                }
            
            # 작성일
            if article.get('date'):
                properties["작성일"] = {
                    "rich_text": [{"text": {"content": article['date']}}]
                }
            
            # 카페명
            if article.get('cafe_name'):
                try:
                    properties["카페명"] = {
                        "select": {"name": article['cafe_name']}
                    }
                except:
                    properties["카페명"] = {
                        "rich_text": [{"text": {"content": article['cafe_name']}}]
                    }
            
            # 내용
            content = article.get('content', '').strip()[:2000]
            if not content:
                content = "(내용 없음)"
            
            properties["내용"] = {
                "rich_text": [{"text": {"content": content}}]
            }
            
            # 크롤링 일시
            try:
                properties["크롤링 일시"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
            except:
                properties["크롤링 일시"] = {
                    "rich_text": [{"text": {"content": datetime.now().isoformat()}}]
                }
            
            # uploaded
            properties["uploaded"] = {"checkbox": False}
            
            # 페이지 생성
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            logging.info(f"✅ 노션 저장: {title[:30]}...")
            return True
            
        except Exception as e:
            logging.error(f"❌ 저장 실패: {e}")
            return False


def main():
    """메인"""
    logging.info("="*60)
    logging.info("🚀 네이버 카페 → 노션 크롤링 시작")
    logging.info(f"⏰ {datetime.now()}")
    logging.info("="*60)
    
    # 환경변수 확인
    required = ['NAVER_ID', 'NAVER_PW', 'NOTION_TOKEN', 'NOTION_DATABASE_ID']
    missing = [e for e in required if not os.getenv(e)]
    
    if missing:
        logging.error(f"❌ 환경변수 누락: {', '.join(missing)}")
        sys.exit(1)
    
    # 카페 설정
    cafes = []
    
    if os.getenv('CAFE1_URL'):
        cafes.append({
            'name': os.getenv('CAFE1_NAME', '카페1'),
            'url': os.getenv('CAFE1_URL'),
            'club_id': os.getenv('CAFE1_CLUB_ID'),
            'board_id': os.getenv('CAFE1_BOARD_ID')
        })
    
    if os.getenv('CAFE2_URL'):
        cafes.append({
            'name': os.getenv('CAFE2_NAME', '카페2'),
            'url': os.getenv('CAFE2_URL'),
            'club_id': os.getenv('CAFE2_CLUB_ID'),
            'board_id': os.getenv('CAFE2_BOARD_ID')
        })
    
    if not cafes:
        logging.error("❌ 카페 설정 없음")
        sys.exit(1)
    
    # 크롤러 실행
    crawler = NaverCafeCrawler()
    notion = NotionDatabase()
    
    try:
        if not crawler.login_naver():
            raise Exception("로그인 실패")
        
        total = 0
        
        for cafe in cafes:
            logging.info(f"\n📍 {cafe['name']} 크롤링...")
            articles = crawler.crawl_cafe(cafe)
            
            saved = 0
            for article in articles:
                if notion.save_article(article):
                    saved += 1
                    total += 1
            
            logging.info(f"✅ {cafe['name']}: {saved}개 저장")
            time.sleep(2)
        
        logging.info(f"\n🎉 완료! 총 {total}개 저장")
        
    except Exception as e:
        logging.error(f"❌ 실패: {e}")
        sys.exit(1)
    
    finally:
        crawler.close()


if __name__ == "__main__":
    main()