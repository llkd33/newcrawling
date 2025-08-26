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
import re
from typing import List, Dict
from dotenv import load_dotenv
import hashlib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from notion_client import Client

# 새로운 콘텐츠 추출 시스템 import
from content_extractor import ContentExtractor
from content_extraction_models import ExtractionConfig

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
        self.content_extractor = None
        self.setup_driver()
        
    def setup_driver(self):
        """Selenium 드라이버 설정"""
        options = Options()
        
        # GitHub Actions 환경
        if os.getenv('GITHUB_ACTIONS'):
            # Use new headless for better JS rendering in CI
            options.add_argument('--headless=new')
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
            
            # 새로운 콘텐츠 추출기 초기화
            extraction_config = ExtractionConfig(
                timeout_seconds=int(os.getenv('CONTENT_EXTRACTION_TIMEOUT', '30')),
                min_content_length=int(os.getenv('CONTENT_MIN_LENGTH', '30')),
                max_content_length=int(os.getenv('CONTENT_MAX_LENGTH', '2000')),
                retry_count=int(os.getenv('EXTRACTION_RETRY_COUNT', '3')),
                enable_debug_screenshot=os.getenv('DEBUG_SCREENSHOT_ENABLED', 'true').lower() == 'true'
            )
            
            self.content_extractor = ContentExtractor(self.driver, self.wait, extraction_config)
            
            logging.info("✅ 크롬 드라이버 및 콘텐츠 추출기 초기화 성공")
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
        """
        게시물 내용 가져오기 - 새로운 ContentExtractor 사용
        기존의 복잡한 로직을 모듈화된 시스템으로 교체
        """
        try:
            logging.info(f"📖 새로운 ContentExtractor로 내용 추출: {url}")
            
            # 새로운 ContentExtractor 사용
            result = self.content_extractor.extract_content(url)
            
            if result.success:
                logging.info(f"✅ 내용 추출 성공: {len(result.content)}자 (방법: {result.extraction_method.value}, 품질: {result.quality_score:.2f})")
                return result.content
            else:
                logging.warning(f"⚠️ 내용 추출 실패: {result.error_message}")
                return result.content  # 실패 시에도 기본 메시지 반환
                
        except Exception as e:
            logging.error(f"❌ ContentExtractor 사용 중 오류: {e}")
            # 기존 방식으로 폴백 (안전장치)
            return f"내용을 불러올 수 없습니다.\n원본 링크: {url}"
    
    def crawl_cafe(self, cafe_config: Dict) -> List[Dict]:
        """카페 게시물 크롤링"""
        results = []
        
        try:
            # 카페 게시판 접속 - F-E 카페 URL 구조에 맞춤
            if cafe_config['name'] == 'F-E 카페':
                # F-E 카페 전용 URL 구조
                board_url = f"{cafe_config['url']}/cafes/{cafe_config['club_id']}/menus/{cafe_config['board_id']}?viewType=L"
            else:
                # 일반 카페 URL 구조
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
            
            # 공지 제외 (여러 패턴 처리)
            actual_articles = []
            for article in articles:
                try:
                    is_notice = False
                    # 클래스 기반
                    try:
                        cls = (article.get_attribute('class') or '').lower()
                        if 'notice' in cls:
                            is_notice = True
                    except:
                        pass

                    # 시각적 아이콘/표시 기반
                    if not is_notice:
                        try:
                            if article.find_elements(By.CSS_SELECTOR, 'img[alt="공지"], .notice, .icon_notice, .board-notice, .ArticleList__notice'):
                                is_notice = True
                        except:
                            pass

                    # 셀 텍스트 기반
                    if not is_notice:
                        try:
                            td_article_elems = article.find_elements(By.CSS_SELECTOR, 'td, th, .td_article')
                            for td in td_article_elems[:2]:
                                t = td.text.strip()
                                if t == '공지' or t.startswith('공지') or '[공지]' in t:
                                    is_notice = True
                                    break
                        except:
                            pass

                    # 전체 텍스트 검사 (최후의 수단)
                    if not is_notice:
                        text = (article.text or '').strip()
                        if not text or '공지' in text:
                            # 공백이거나 공지 포함이면 제외
                            if '공지' in text:
                                is_notice = True
                            else:
                                # 공백은 제외하지 않고 계속 진행
                                pass

                    if is_notice:
                        continue
                    actual_articles.append(article)
                except:
                    # 오류 시에는 보수적으로 포함
                    actual_articles.append(article)
            
            logging.info(f"📊 공지 제외 실제 게시물: {len(actual_articles)}개")
            
            # 최대 3개 처리 (테스트용으로 줄임)
            max_articles = 3
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
                    
                    # 중복 체크 (임시 비활성화 - 테스트용)
                    article_id = link.split('articleid=')[-1].split('&')[0] if 'articleid=' in link else ""
                    
                    # TODO: 테스트 완료 후 중복 체크 다시 활성화
                    # try:
                    #     notion = NotionDatabase()
                    #     if notion.check_duplicate(link):
                    #         logging.info(f"⏭️ 이미 저장됨: {title[:30]}...")
                    #         continue
                    # except:
                    #     pass
                    
                    logging.info(f"🔄 중복 체크 비활성화 - 강제 처리: {title[:30]}...")
                    
                    # 내용 크롤링
                    logging.info(f"📖 크롤링 시작: {title[:30]}...")
                    logging.info(f"🔗 URL: {link}")
                    
                    content = self.get_article_content(link)
                    
                    logging.info(f"📝 추출된 내용 길이: {len(content)}자")
                    logging.info(f"📄 내용 미리보기: {content[:100]}...")

                    # 내용 추출 실패 시 재시도 후 저장
                    if "내용을 불러올 수 없습니다" in content:
                        logging.warning(f"⚠️ 내용 추출 실패, 제목과 링크만 저장: {title[:30]}...")
                        content = f"[내용 자동 추출 실패]\n\n제목: {title}\n\n원본 게시글을 확인하려면 URL을 클릭하세요."
                    else:
                        logging.info(f"✅ 내용 추출 성공: {title[:30]}...")
                    
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
        """중복 체크 - URL 필드 기반"""
        try:
            logging.debug(f"🔍 중복 체크: {url}")
            
            # URL로 중복 체크
            query_filter = {
                "property": "URL",
                "url": {"equals": url}
            }

            response = self.client.databases.query(
                database_id=self.database_id,
                filter=query_filter
            )
            
            num_results = len(response.get('results', []))
            is_duplicate = num_results > 0
            
            if is_duplicate:
                logging.debug(f"  🔴 중복 발견: {num_results}개")
            else:
                logging.debug(f"  🟢 새로운 게시물")
            
            return is_duplicate

        except Exception as e:
            logging.error(f"❌ 중복 체크 오류: {e}")
            # 오류 시에는 중복이 아니라고 판단 (안전장치)
            return False
    
    def save_article(self, article: Dict) -> bool:
        """게시물 저장 - 노션 DB 구조에 맞춤"""
        try:
            # TODO: 테스트 완료 후 중복 체크 다시 활성화
            # if self.check_duplicate(article['url']):
            #     logging.info(f"⏭️ 중복: {article['title'][:30]}...")
            #     return False
            
            logging.info(f"💾 중복 체크 비활성화 - 강제 저장 시도: {article['title'][:30]}...")
            
            # 노션 속성 (이미지 구조에 정확히 맞춤)
            properties = {}
            
            # 1. 이름 (제목) - Title 필드
            title = article.get('title', '').strip() or "제목 없음"
            if len(title) > 100:
                title = title[:97] + "..."
            
            properties["이름"] = {
                "title": [{"text": {"content": title}}]
            }
            
            # 2. 작성자 - Rich Text 필드
            author = article.get('author', 'Unknown').strip()
            if author and author != 'Unknown':
                properties["작성자"] = {
                    "rich_text": [{"text": {"content": author}}]
                }
            
            # 3. 작성일 - Date 필드 (이미지에서 Date 타입으로 확인됨)
            date_str = article.get('date', datetime.now().strftime('%Y-%m-%d'))
            try:
                # 날짜 형식 변환 (YYYY-MM-DD)
                if '.' in date_str:
                    date_str = date_str.replace('.', '-')
                if len(date_str.split('-')[0]) == 2:  # YY-MM-DD 형식인 경우
                    year = '20' + date_str.split('-')[0]
                    date_str = year + '-' + '-'.join(date_str.split('-')[1:])
                
                properties["작성일"] = {
                    "date": {"start": date_str}
                }
            except:
                # 날짜 파싱 실패 시 오늘 날짜 사용
                properties["작성일"] = {
                    "date": {"start": datetime.now().strftime('%Y-%m-%d')}
                }
            
            # 4. URL - URL 필드
            if article.get('url'):
                properties["URL"] = {"url": article['url']}
            
            # 5. 내용 - Rich Text 필드
            content = article.get('content', '').strip()
            if not content:
                content = "[내용 없음]"
            
            # 내용이 너무 길면 자르기 (노션 Rich Text 제한 고려)
            if len(content) > 2000:
                content = content[:1997] + "..."
            
            properties["내용"] = {
                "rich_text": [{"text": {"content": content}}]
            }
            
            # 6. 크롤링일시 - Date 필드 (현재 시간)
            properties["크롤링일시"] = {
                "date": {"start": datetime.now().isoformat()}
            }
            
            # 7. 카페 - Rich Text 필드
            cafe_name = article.get('cafe_name', 'Unknown')
            properties["카페"] = {
                "rich_text": [{"text": {"content": cafe_name}}]
            }
            
            # 8. uploaded - Checkbox 필드 (기본값: false)
            properties["uploaded"] = {"checkbox": False}
            
            # 페이지 생성
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            logging.info(f"✅ 노션 저장 성공: {title[:30]}...")
            return True
            
        except Exception as e:
            logging.error(f"❌ 노션 저장 실패: {e}")
            logging.error(f"   게시물 정보: {article.get('title', 'Unknown')[:50]}")
            
            # 디버깅을 위한 상세 오류 정보
            import traceback
            logging.debug(f"   상세 오류: {traceback.format_exc()}")
            
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
    
    # 카페 설정 - 실제 F-E 카페 정보로 업데이트
    cafes = []
    
    # F-E 카페 설정 (제공된 정보 기반)
    cafes.append({
        'name': 'F-E 카페',
        'url': 'https://cafe.naver.com/f-e',
        'club_id': '18786605',
        'board_id': '105'
    })
    
    # 환경변수로 추가 카페 설정 가능
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
