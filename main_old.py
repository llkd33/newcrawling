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
            
            # 로그인 성공 확인 (여러 방법)
            current_url = self.driver.current_url
            
            # 방법 1: URL 체크
            if any(success_indicator in current_url for success_indicator in ['naver.com', 'main', 'home']):
                logging.info("✅ 네이버 로그인 성공 (URL 확인)")
                
                # 추가 확인: 로그인 상태 체크
                self.driver.get('https://naver.com')
                time.sleep(2)
                
                try:
                    # 로그인된 사용자 요소 찾기
                    login_info = self.driver.find_element(By.CSS_SELECTOR, '.MyView-module__my_menu___eF4ct, .account_info, .user_info')
                    logging.info("✅ 로그인 상태 확인 완료")
                    return True
                except:
                    # 요소를 못 찾아도 URL이 정상이면 진행
                    logging.info("✅ 로그인 것으로 추정 (진행)")
                    return True
            else:
                # 2차 인증 등의 추가 단계가 있을 수 있음
                logging.warning(f"⚠️ 로그인 후 추가 확인 필요: {current_url}")
                time.sleep(5)
                return True
            
        except Exception as e:
            logging.error(f"❌ 로그인 실패: {e}")
            # 스크린샷 저장 (디버깅용)
            try:
                self.driver.save_screenshot('login_error.png')
                logging.info("로그인 오류 스크린샷 저장: login_error.png")
            except:
                pass
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
                    # 빈 행 제외
                    if not article.text.strip():
                        continue
                    actual_articles.append(article)
                except:
                    actual_articles.append(article)
            
            logging.info(f"📊 공지 제외 실제 게시물: {len(actual_articles)}개")
            
            # 최대 4개씩만 처리
            max_articles = 4
            processed_count = 0
            new_articles_found = 0
            
            # 더 많은 게시물 확인 (새 게시물 4개 찾을 때까지)
            for idx, article in enumerate(actual_articles[:20], 1):  # 최신 20개 확인
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
                                logging.info(f"⏭️ [{idx:02d}] 이미 저장된 게시물: {title[:30]}...")
                                continue
                            else:
                                new_articles_found += 1
                                logging.info(f"✨ [{new_articles_found:02d}] 새 게시물 발견: {title[:30]}...")
                        except Exception as e:
                            logging.debug(f"중복 체크 중 오류: {e}")
                            # 오류 시에도 계속 진행
                            new_articles_found += 1
                    
                    # 상세 내용 크롤링
                    logging.info(f"📖 내용 크롤링 중: {title[:30]}...")
                    content = self.get_article_content(link)
                    logging.info(f"📝 내용 길이: {len(content)} 글자")
                    
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
                    
                    # 디버깅 정보
                    logging.debug(f"데이터 구성 완료:")
                    logging.debug(f"  - 제목: {data['title'][:50]}")
                    logging.debug(f"  - 내용: {data['content'][:100]}...")
                    
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
        """게시물 상세 내용 가져오기 - 최종 완성 버전"""
        try:
            # 현재 창 핸들 저장
            original_window = self.driver.current_window_handle
            
            # 새 탭에서 게시물 열기
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 페이지 완전히 로딩 대기
            logging.info(f"📄 게시물 페이지 로딩 중...")
            time.sleep(10)  # 충분한 로딩 시간
            
            # iframe으로 전환 (네이버 카페는 반드시 iframe 사용)
            iframe_success = False
            try:
                self.driver.switch_to.frame('cafe_main')
                logging.info("✅ iframe 전환 성공")
                iframe_success = True
            except Exception as e:
                logging.warning(f"⚠️ iframe 전환 실패: {e}")
                # iframe 없이도 시도
            
            # 내용 추출 - 완전 새로운 접근
            content = ""
            
            # 우선 가장 정확한 방법: se-main-container 찾기
            try:
                # JavaScript로 직접 추출 (가장 안정적)
                content = self.driver.execute_script("""
                    // 디버깅 로그
                    console.log('내용 추출 시작...');
                    
                    // 1. SmartEditor ONE (최신 에디터)
                    var container = document.querySelector('.se-main-container');
                    if (container) {
                        console.log('SmartEditor ONE 발견!');
                        var result = [];
                        
                        // 모든 섹션 순회
                        var sections = container.querySelectorAll('.se-section');
                        sections.forEach(function(section) {
                            // 텍스트 섹션
                            var textParas = section.querySelectorAll('.se-text-paragraph');
                            textParas.forEach(function(para) {
                                var text = para.innerText || para.textContent;
                                if (text && text.trim()) {
                                    result.push(text.trim());
                                }
                            });
                            
                            // 이미지 섹션
                            var images = section.querySelectorAll('img.se-image-resource');
                            images.forEach(function(img) {
                                var src = img.getAttribute('data-src') || img.getAttribute('src');
                                if (src) {
                                    result.push('[이미지] ' + src);
                                }
                            });
                        });
                        
                        if (result.length === 0) {
                            // 섹션이 없으면 전체에서 찾기
                            var allText = container.innerText || container.textContent;
                            if (allText) result.push(allText.trim());
                            
                            // 이미지 전체 찾기
                            var allImages = container.querySelectorAll('img[src]');
                            allImages.forEach(function(img) {
                                var src = img.getAttribute('data-src') || img.getAttribute('src');
                                if (src && !src.includes('cafe_main')) {
                                    result.push('[이미지] ' + src);
                                }
                            });
                        }
                        
                        return result.join('\\n\\n');
                    }
                    
                    // 2. ContentRenderer (중간 버전)
                    var content = document.querySelector('.ContentRenderer');
                    if (content) {
                        console.log('ContentRenderer 발견!');
                        return content.innerText;
                    }
                    
                    // 3. 구형 에디터
                    var oldEditor = document.querySelector('#postViewArea, .NHN_Writeform_Main');
                    if (oldEditor) {
                        console.log('구형 에디터 발견!');
                        return oldEditor.innerText;
                    }
                    
                    // 4. 기타 선택자
                    var others = document.querySelector('#tbody, #content-area, .post_ct, .view_content');
                    if (others) {
                        console.log('기타 영역 발견!');
                        return others.innerText;
                    }
                    
                    console.log('내용을 찾을 수 없음');
                    return '';
                """)
                    
                
                if content:
                    logging.info(f"✅ JavaScript로 내용 추출 성공: {len(content)}자")
                else:
                    logging.warning("⚠️ JavaScript 추출 실패, Selenium으로 재시도")
                    
            except Exception as js_error:
                logging.error(f"JavaScript 실행 오류: {js_error}")
            
            # JavaScript 실패 시 Selenium으로 재시도
            if not content:
                    content = self.driver.execute_script("""
                        var elem = document.querySelector('.ContentRenderer');
                        if (!elem) return '';
                        
                        var result = [];
                        var text = elem.innerText || elem.textContent;
                        if (text) result.push(text.trim());
                        
                        // ContentRenderer 내 이미지도 추출
                        var images = elem.querySelectorAll('img[src]');
                        for (var i = 0; i < images.length; i++) {
                            var src = images[i].getAttribute('data-src') || images[i].getAttribute('src');
                            if (src) result.push('[이미지] ' + src);
                        }
                        
                        return result.join('\\n\\n');
                    """)
                    
                    if content and len(content) > 30:
                        logging.info(f"✅ ContentRenderer에서 내용 추출 (이미지 포함): {len(content)}자")
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                        return content[:2000]
                    
                    # 방법 3: 일반 게시글 영역 - 이미지 URL 포함
                    content = self.driver.execute_script("""
                        var selectors = [
                            '#postViewArea',
                            '#content-area',
                            '.post_ct',
                            '#tbody',
                            '.NHN_Writeform_Main',
                            'div[class*="view_content"]',
                            '.article_viewer',
                            '.board-view-content'
                        ];
                        
                        for (var i = 0; i < selectors.length; i++) {
                            var elem = document.querySelector(selectors[i]);
                            if (elem && elem.innerText && elem.innerText.length > 30) {
                                var result = [elem.innerText.trim()];
                                
                                // 해당 영역 내 이미지도 추출
                                var images = elem.querySelectorAll('img[src]');
                                for (var j = 0; j < images.length; j++) {
                                    var src = images[j].getAttribute('data-src') || images[j].getAttribute('src');
                                    if (src) result.push('[이미지] ' + src);
                                }
                                
                                return result.join('\\n\\n');
                            }
                        }
                        return '';
                    """)
                    
                    if content and len(content) > 30:
                        logging.info(f"✅ 일반 선택자에서 내용 추출 (이미지 포함): {len(content)}자")
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                        return content[:2000]
                    
                    # 방법 4: 사용자 제공 HTML 구조 기반 추출 (h3.title_text와 se-main-container)
                    content = self.driver.execute_script("""
                        // 먼저 제목 확인 (디버깅용)
                        var title = document.querySelector('h3.title_text');
                        if (title) {
                            console.log('제목 찾음:', title.innerText);
                        }
                        
                        // 본문 컨테이너 찾기
                        var container = document.querySelector('.se-main-container') || 
                                       document.querySelector('.ContentRenderer') ||
                                       document.querySelector('#postViewArea');
                        
                        if (!container) {
                            // 폴백: 전체 본문 영역 찾기
                            container = document.querySelector('td.view') ||
                                       document.querySelector('div.view_content') ||
                                       document.querySelector('div#content-area');
                        }
                        
                        if (container) {
                            var result = [];
                            
                            // 텍스트 추출
                            var textNodes = container.querySelectorAll('.se-text-paragraph, p, div');
                            for (var i = 0; i < textNodes.length; i++) {
                                var text = textNodes[i].innerText || textNodes[i].textContent;
                                if (text && text.trim() && text.length > 10) {
                                    // 댓글, 메뉴 등 제외
                                    if (!text.includes('로그인') && !text.includes('메뉴') && !text.includes('댓글')) {
                                        result.push(text.trim());
                                    }
                                }
                            }
                            
                            // 이미지 URL 추출
                            var images = container.querySelectorAll('img.se-image-resource, img[src]');
                            for (var j = 0; j < images.length; j++) {
                                var src = images[j].getAttribute('data-src') || 
                                         images[j].getAttribute('src') ||
                                         images[j].getAttribute('data-lazy-src');
                                if (src && !src.includes('emoticon') && !src.includes('sticker')) {
                                    result.push('[이미지] ' + src);
                                }
                            }
                            
                            return result.join('\\n\\n');
                        }
                        
                        return '';
                    """)
                    
                    if content and len(content) > 30:
                        logging.info(f"✅ 텍스트 노드 수집으로 내용 추출: {len(content)}자")
                        
                except Exception as js_error:
                    logging.error(f"JavaScript 실행 오류: {js_error}")
                    
                    # JavaScript 실패 시 Selenium으로 시도 (이미지 포함)
                    selectors = [
                        'div.se-main-container',
                        'div.ContentRenderer', 
                        '#postViewArea',
                        '#content-area',
                        'td.view',
                        '#tbody'
                    ]
                    
                    for selector in selectors:
                        try:
                            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            content_parts = []
                            
                            # 텍스트 추출
                            text = elem.text.strip()
                            if text:
                                content_parts.append(text)
                            
                            # 이미지 URL 추출
                            try:
                                images = elem.find_elements(By.CSS_SELECTOR, 'img[src], img[data-src]')
                                for img in images:
                                    src = img.get_attribute('data-src') or img.get_attribute('src')
                                    if src and not any(skip in src for skip in ['emoticon', 'sticker', 'icon']):
                                        content_parts.append(f'[이미지] {src}')
                            except Exception as img_error:
                                logging.debug(f"이미지 추출 중 오류: {img_error}")
                            
                            content = '\n\n'.join(content_parts)
                            
                            if content and len(content) > 30:
                                logging.info(f"✅ Selenium으로 내용 추출 (이미지 포함): {selector} ({len(content)}자)")
                                break
                        except:
                            continue
                
            except Exception as iframe_error:
                logging.error(f"iframe 처리 오류: {iframe_error}")
                # iframe 없이 시도 (이미지 URL 포함)
                content = self.driver.execute_script("""
                    var result = [];
                    
                    // 본문 텍스트 추출
                    var bodyText = document.body.innerText || document.body.textContent;
                    if (bodyText) result.push(bodyText);
                    
                    // 모든 이미지 URL 추출
                    var images = document.querySelectorAll('img[src], img[data-src]');
                    for (var i = 0; i < images.length; i++) {
                        var src = images[i].getAttribute('data-src') || images[i].getAttribute('src');
                        if (src && !src.includes('emoticon')) {
                            result.push('[이미지] ' + src);
                        }
                    }
                    
                    return result.join('\\n\\n');
                """)
            
            # 탭 닫기
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            # 내용 검증 및 정리
            if content and len(content.strip()) > 30:
                # 불필요한 공백 정리
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not any(skip in line.lower() for skip in ['로그인', '메뉴', '목록', '이전글', '다음글']):
                        cleaned_lines.append(line)
                
                content = '\n'.join(cleaned_lines)
                
                # 이미지 URL 개수 로깅
                image_count = content.count('[이미지]')
                if image_count > 0:
                    logging.info(f"📷 {image_count}개 이미지 URL 포함")
                
                return content[:2000]
            else:
                logging.warning(f"⚠️ 내용 추출 실패 또는 너무 짧음 (길이: {len(content) if content else 0}) - URL: {url}")
                # 디버깅: 현재 페이지 HTML 일부 출력
                try:
                    page_html = self.driver.page_source[:500]
                    logging.debug(f"페이지 HTML 샘플: {page_html}")
                except:
                    pass
                return "(본문 내용을 가져올 수 없습니다)"
                
        except Exception as e:
            logging.error(f"게시물 내용 크롤링 실패: {e}")
            try:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
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
            
            is_duplicate = len(response['results']) > 0
            if is_duplicate:
                logging.debug(f"중복 확인: {url[:50]}...")
            return is_duplicate
            
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
            # 필드 타입을 정확히 맞춰야 함
            properties = {}
            
            # 제목 필드 - 환경변수로 설정 가능, 기본값은 "새 페이지"
            # 노션의 기본 Title 필드명은 언어 설정에 따라 다름
            title_field = os.getenv('NOTION_TITLE_FIELD', '새 페이지')
            
            # 제목이 비어있지 않도록 확인
            title_text = article.get('title', '').strip()
            if not title_text:
                title_text = f"게시물 - {datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            logging.info(f"📝 노션 저장 시작: 제목={title_text[:30]}...")
            logging.debug(f"📄 내용 미리보기: {article.get('content', '')[:100]}...")
            
            # 가능한 Title 필드명들 시도
            title_fields_to_try = [title_field, '새 페이지', 'Name', '이름', '제목', 'Title']
            title_set = False
            
            for field_name in title_fields_to_try:
                try:
                    properties[field_name] = {
                        "title": [{"text": {"content": title_text}}]
                    }
                    title_set = True
                    logging.debug(f"제목 필드 설정 성공: {field_name}")
                    break
                except:
                    continue
            
            if not title_set:
                logging.error("제목 필드를 설정할 수 없습니다")
            
            # URL 필드
            if article.get('url'):
                properties["URL"] = {
                    "url": article['url']
                }
            
            # 작성자 (Rich Text)
            if article.get('author'):
                properties["작성자"] = {
                    "rich_text": [{"text": {"content": article['author']}}]
                }
            
            # 작성일 (Rich Text로 변경 - 에러 메시지에 따라)
            if article.get('date'):
                properties["작성일"] = {
                    "rich_text": [{"text": {"content": article['date']}}]
                }
            
            # 카페명 (Select)
            if article.get('cafe_name'):
                try:
                    properties["카페명"] = {
                        "select": {"name": article['cafe_name']}
                    }
                except:
                    # Select 필드가 없으면 텍스트로
                    properties["카페명"] = {
                        "rich_text": [{"text": {"content": article['cafe_name']}}]
                    }
            
            # 내용 (Rich Text)
            content = article.get('content', '').strip()
            if not content:
                # 내용이 비어있으면 다시 시도하지 않고 빈 값으로 처리
                content = "(내용을 불러오는 중...)"
                logging.warning(f"내용이 비어있음: {title_text}")
            
            # 노션 Rich Text 제한 (2000자)
            content = content[:2000]
            
            # 내용 필드 설정
            properties["내용"] = {
                "rich_text": [{"text": {"content": content}}]
            }
            
            # 크롤링 일시 (Date)
            try:
                properties["크롤링 일시"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
            except:
                # Date 필드가 없으면 텍스트로
                properties["크롤링 일시"] = {
                    "rich_text": [{"text": {"content": datetime.now().isoformat()}}]
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
            
            # 페이지 내용 추가 (블록으로)
            try:
                # 페이지 본문에 상세 내용 추가
                blocks = []
                
                # 제목 블록
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": title_text}
                        }]
                    }
                })
                
                # 정보 블록
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": f"📅 작성일: {article.get('date', 'N/A')}\n👤 작성자: {article.get('author', 'Unknown')}\n📊 조회수: {article.get('views', '0')}"}
                        }]
                    }
                })
                
                # 구분선
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
                
                # 본문 내용
                if content and content != "내용을 가져올 수 없습니다.":
                    # 내용을 단락으로 나누기
                    paragraphs = content.split('\n\n')
                    for para in paragraphs[:10]:  # 최대 10개 단락
                        if para.strip():
                            blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{
                                        "type": "text",
                                        "text": {"content": para.strip()[:2000]}
                                    }]
                                }
                            })
                
                # 원본 링크
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {
                                "content": "🔗 원본 게시물 보기",
                                "link": {"url": article.get('url', '')}
                            }
                        }]
                    }
                })
                
                # 블록 추가
                self.client.blocks.children.append(
                    block_id=page["id"],
                    children=blocks
                )
            except Exception as e:
                logging.debug(f"페이지 내용 추가 중 오류 (무시): {e}")
            
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