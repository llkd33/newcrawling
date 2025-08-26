#!/usr/bin/env python3
"""
네이버 카페 크롤링 -> 노션 저장 메인 스크립트 (개선 버전)
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
        """네이버 로그인 - 자동화 탐지 우회 강화"""
        try:
            # 자동화 탐지 우회 설정
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                '''
            })
            
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(3)
            
            # ID 입력 (JavaScript로 직접 값 설정)
            id_input = self.driver.find_element(By.ID, 'id')
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, id_input, os.getenv('NAVER_ID'))
            time.sleep(2)  # 입력 후 대기
            
            # PW 입력
            pw_input = self.driver.find_element(By.ID, 'pw')
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, pw_input, os.getenv('NAVER_PW'))
            time.sleep(2)
            
            # 로그인 상태 유지 체크 (선택사항)
            try:
                keep_login = self.driver.find_element(By.CSS_SELECTOR, '.keep_check')
                if not keep_login.is_selected():
                    keep_login.click()
            except:
                pass
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, 'log.login')
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            # 로그인 완료 대기 (더 긴 시간)
            time.sleep(10)
            
            # 로그인 성공 확인
            current_url = self.driver.current_url
            if any(success_indicator in current_url for success_indicator in ['naver.com', 'main', 'home']):
                logging.info("✅ 네이버 로그인 성공")
                return True
            else:
                logging.warning(f"⚠️ 로그인 후 추가 확인 필요: {current_url}")
                return True
            
        except Exception as e:
            logging.error(f"❌ 로그인 실패: {e}")
            return False
    
    def get_article_content(self, url: str) -> str:
        """게시물 상세 내용 가져오기 - 최종 강화 버전"""
        try:
            logging.info(f"📖 게시물 내용 크롤링 시작: {url}")
            
            # 새 탭에서 열기 (안정성 향상)
            original_window = self.driver.current_window_handle
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 충분한 로딩 시간 (더 길게)
            time.sleep(12)
            
            # iframe 전환 필수
            iframe_switched = False
            try:
                self.driver.switch_to.frame('cafe_main')
                iframe_switched = True
                logging.info("✅ iframe 전환 성공")
                time.sleep(2)  # iframe 로드 대기
            except Exception as e:
                logging.warning(f"⚠️ iframe 전환 실패: {e}")
            
            # 내용 추출 - 다양한 방법 시도
            content = ""
            
            # 방법 1: 페이지 소스에서 직접 추출
            try:
                # 잠시 더 기다리기
                time.sleep(3)
                
                # 페이지 소스 가져오기
                page_source = self.driver.page_source
                
                # se-main-container가 있는지 확인
                if 'se-main-container' in page_source:
                    # JavaScript로 추출
                    js_content = self.driver.execute_script("""
                        var container = document.querySelector('.se-main-container');
                        if (!container) return '';
                        
                        // 모든 텍스트 수집
                        var result = [];
                        
                        // 방법 1: 전체 텍스트
                        var fullText = container.innerText || container.textContent;
                        if (fullText && fullText.length > 10) {
                            return fullText;
                        }
                        
                        // 방법 2: 개별 요소
                        var elements = container.querySelectorAll('*');
                        for (var i = 0; i < elements.length; i++) {
                            var text = elements[i].innerText || elements[i].textContent;
                            if (text && text.trim() && text.length > 10) {
                                result.push(text.trim());
                            }
                        }
                        
                        return result.join('\\n');
                    """)
                    
                    if js_content and len(js_content) > 10:
                        content = js_content
                        logging.info(f"✅ se-main-container에서 내용 추출: {len(content)}자")
                
                # ContentRenderer 확인
                elif 'ContentRenderer' in page_source:
                    js_content = self.driver.execute_script("""
                        var container = document.querySelector('.ContentRenderer');
                        if (container) {
                            return container.innerText || container.textContent || '';
                        }
                        return '';
                    """)
                    
                    if js_content and len(js_content) > 10:
                        content = js_content
                        logging.info(f"✅ ContentRenderer에서 내용 추출: {len(content)}자")
                    
                    // 2. 다른 에디터들
                    var other_selectors = [
                        '.ContentRenderer',
                        '#postViewArea', 
                        '.NHN_Writeform_Main',
                        '#content-area',
                        '#tbody',
                        '.post_ct',
                        '.board-read-body',
                        '.view_content',
                        'td.view'
                    ];
                    
                    for (var k = 0; k < other_selectors.length; k++) {
                        var elem = document.querySelector(other_selectors[k]);
                        if (elem) {
                            var content = elem.innerText || elem.textContent;
                            if (content && content.length > 50) {
                                console.log('내용 발견:', other_selectors[k]);
                                
                                // 이미지 추가
                                var imgs = elem.querySelectorAll('img');
                                for (var m = 0; m < imgs.length; m++) {
                                    var src = imgs[m].src || imgs[m].getAttribute('data-src');
                                    if (src) content += '\\n[이미지] ' + src;
                                }
                                
                                return content;
                            }
                        }
                    }
                    
                    // 3. 최후의 수단: body 전체에서 본문 영역 찾기
                    console.log('최후의 수단: body 전체 검색');
                    
                    // 제목, 댓글 등을 제외한 본문만
                    var all_divs = document.querySelectorAll('div');
                    var max_text = '';
                    var max_length = 0;
                    
                    for (var n = 0; n < all_divs.length; n++) {
                        var div = all_divs[n];
                        // 댓글, 메뉴 등 제외
                        if (div.className && (
                            div.className.includes('comment') || 
                            div.className.includes('reply') ||
                            div.className.includes('menu') ||
                            div.className.includes('nav')
                        )) continue;
                        
                        var text = div.innerText || div.textContent;
                        if (text && text.length > max_length && text.length > 100) {
                            max_length = text.length;
                            max_text = text;
                        }
                    }
                    
                    return max_text || '';
                """)
                
                if js_content and len(js_content) > 30:
                    logging.info(f"✅ JavaScript로 내용 추출 성공: {len(js_content)}자")
                    content = js_content
                    
            except Exception as js_error:
                logging.error(f"JavaScript 추출 오류: {js_error}")
            
            # 방법 2: JavaScript 실패시 Selenium으로 재시도
            if not content or len(content) < 30:
                selectors = [
                    '.se-main-container',
                    '.ContentRenderer',
                    '#postViewArea',
                    '.NHN_Writeform_Main',
                    '#content-area',
                    '.post_ct',
                    '#tbody',
                    'td.view',
                    '.view_content'
                ]
                
                for selector in selectors:
                    try:
                        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        text = elem.text.strip()
                        if text and len(text) > 30:
                            logging.info(f"✅ Selenium {selector}에서 내용 발견: {len(text)}자")
                            
                            # 이미지도 찾기
                            try:
                                images = elem.find_elements(By.CSS_SELECTOR, 'img[src], img[data-src]')
                                for img in images:
                                    src = img.get_attribute('data-src') or img.get_attribute('src')
                                    if src and 'emoticon' not in src:
                                        text += f"\n[이미지] {src}"
                            except:
                                pass
                            
                            content = text
                            break
                    except:
                        continue
            
            
            # 탭 닫고 원래 창으로 돌아가기
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            # 결과 처리
            if content and len(content) > 30:
                # 불필요한 텍스트 제거
                lines = content.split('\n')
                filtered = []
                for line in lines:
                    line = line.strip()
                    if line and not any(skip in line for skip in ['로그인', '메뉴', '목록', '이전글', '다음글', '댓글']):
                        filtered.append(line)
                
                content = '\n'.join(filtered)[:2000]
                
                # 이미지 개수 확인
                img_count = content.count('[이미지]')
                if img_count > 0:
                    logging.info(f"📷 {img_count}개 이미지 URL 포함")
                
                return content
            else:
                logging.warning(f"⚠️ 내용을 가져올 수 없음: {url}")
                return "(본문 내용을 가져올 수 없습니다)"
                
        except Exception as e:
            logging.error(f"❌ 내용 크롤링 실패: {e}")
            # 페이지 소스 일부 출력 (디버깅)
            try:
                page_source = self.driver.page_source[:500]
                logging.debug(f"페이지 HTML: {page_source}")
            except:
                pass
            return "(본문 내용을 가져올 수 없습니다)"
    
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
            
            # 게시물 찾기
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
                logging.warning("❌ 게시물을 찾을 수 없습니다.")
                return results
            
            # 공지사항 제외
            actual_articles = []
            for article in articles:
                try:
                    class_attr = article.get_attribute('class') or ''
                    if 'notice' in class_attr.lower() or '공지' in class_attr:
                        continue
                    if not article.text.strip():
                        continue
                    actual_articles.append(article)
                except:
                    actual_articles.append(article)
            
            logging.info(f"📊 공지 제외 실제 게시물: {len(actual_articles)}개")
            
            # 최대 4개씩만 처리
            max_articles = 4
            processed_count = 0
            
            for idx, article in enumerate(actual_articles[:20], 1):  # 최신 20개 확인
                if processed_count >= max_articles:
                    break
                    
                try:
                    # 제목과 링크 찾기
                    title = ""
                    link = ""
                    
                    # 여러 방법으로 시도
                    link_selectors = ['a.article', 'td.td_article a', '.inner_list a', 'a']
                    for sel in link_selectors:
                        try:
                            elem = article.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip()
                            link = elem.get_attribute('href')
                            if title and link:
                                break
                        except:
                            pass
                    
                    if not title or not link:
                        continue
                    
                    # 공지사항 제외
                    if '공지' in title:
                        continue
                    
                    # 게시물 ID 추출
                    article_id = link.split('articleid=')[-1].split('&')[0] if 'articleid=' in link else ""
                    
                    # 중복 체크
                    try:
                        notion_check = NotionDatabase()
                        if notion_check.check_duplicate(link):
                            logging.info(f"⏭️ 이미 저장된 게시물: {title[:30]}...")
                            continue
                    except:
                        pass
                    
                    # 상세 내용 크롤링
                    logging.info(f"📖 내용 크롤링 중: {title[:30]}...")
                    content = self.get_article_content(link)
                    
                    # 작성자
                    author = "Unknown"
                    for author_sel in ['td.td_name a', '.td_name', '.nick', '.p-nick']:
                        try:
                            author = article.find_element(By.CSS_SELECTOR, author_sel).text.strip()
                            if author:
                                break
                        except:
                            pass
                    
                    # 작성일
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    for date_sel in ['td.td_date', '.td_date', '.date']:
                        try:
                            date_text = article.find_element(By.CSS_SELECTOR, date_sel).text.strip()
                            if date_text:
                                # YYYY.MM.DD. -> YYYY-MM-DD
                                date_str = date_text.replace('.', '-').rstrip('-')
                                break
                        except:
                            pass
                    
                    # 조회수
                    views = "0"
                    for view_sel in ['td.td_view', '.td_view', '.view']:
                        try:
                            views = article.find_element(By.CSS_SELECTOR, view_sel).text.strip()
                            if views:
                                break
                        except:
                            pass
                    
                    # 데이터 구성
                    data = {
                        'title': title,
                        'author': author,
                        'date': date_str,
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
                    logging.info(f"📄 [{processed_count}/{max_articles}] 크롤링 완료: {title[:30]}...")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"게시물 크롤링 오류: {e}")
                    continue
            
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logging.error(f"카페 크롤링 오류: {e}")
        
        return results
    
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
    
    def check_duplicate(self, url: str) -> bool:
        """URL로 중복 체크"""
        try:
            # URL에서 articleid 추출
            article_id = ""
            if 'articleid=' in url:
                article_id = url.split('articleid=')[1].split('&')[0]
            
            if article_id:
                # articleid로 정확한 중복 체크
                response = self.client.databases.query(
                    database_id=self.database_id,
                    filter={
                        "property": "URL",
                        "url": {
                            "contains": f"articleid={article_id}"
                        }
                    }
                )
            else:
                # articleid가 없으면 전체 URL로 체크
                response = self.client.databases.query(
                    database_id=self.database_id,
                    filter={
                        "property": "URL",
                        "url": {
                            "equals": url
                        }
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
            
            # 노션 DB 저장
            properties = {}
            
            # 제목 필드
            title_field = os.getenv('NOTION_TITLE_FIELD', 'Name')
            title_text = article.get('title', '').strip() or f"게시물 - {datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 여러 필드명 시도
            for field_name in [title_field, '새 페이지', 'Name', '이름', '제목', 'Title']:
                try:
                    properties[field_name] = {
                        "title": [{"text": {"content": title_text}}]
                    }
                    break
                except:
                    continue
            
            # 다른 필드들
            if article.get('url'):
                properties["URL"] = {"url": article['url']}
            
            if article.get('author'):
                properties["작성자"] = {
                    "rich_text": [{"text": {"content": article['author']}}]
                }
            
            if article.get('date'):
                properties["작성일"] = {
                    "rich_text": [{"text": {"content": article['date']}}]
                }
            
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
            
            # uploaded 체크박스
            properties["uploaded"] = {"checkbox": False}
            
            # 페이지 생성
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            logging.info(f"✅ 노션 저장 성공: {title_text[:30]}...")
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
        sys.exit(1)
    
    # 카페 설정
    cafes = []
    
    # 카페 1
    if os.getenv('CAFE1_URL') and os.getenv('CAFE1_CLUB_ID') and os.getenv('CAFE1_BOARD_ID'):
        cafes.append({
            'name': os.getenv('CAFE1_NAME', '카페1'),
            'url': os.getenv('CAFE1_URL'),
            'club_id': os.getenv('CAFE1_CLUB_ID'),
            'board_id': os.getenv('CAFE1_BOARD_ID'),
            'board_name': os.getenv('CAFE1_BOARD_NAME', '게시판')
        })
    
    # 카페 2
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