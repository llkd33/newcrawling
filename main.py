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
import urllib.parse as urlparse

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

# ---------- 대범한 클래식 엔드포인트 헬퍼들 ----------

def build_classic_list_url(club_id, board_id, user_display=50, page=None):
    """클래식 ArticleList.nhn URL 생성"""
    base = "https://cafe.naver.com/ArticleList.nhn"
    params = {
        "search.clubid": str(club_id),
        "search.menuid": str(board_id), 
        "userDisplay": str(user_display),
    }
    if page:
        params["search.page"] = str(page)
    return f"{base}?{urlparse.urlencode(params)}"

def build_classic_read_url(club_id, article_id):
    """클래식 ArticleRead.nhn URL 생성"""
    return f"https://cafe.naver.com/ArticleRead.nhn?clubid={club_id}&articleid={article_id}"

def is_spa_list_page(driver):
    """리스트가 SPA(Next.js)면 True (cafe_main 미존재 + _next 존재)"""
    try:
        has_iframe = bool(driver.find_elements(By.CSS_SELECTOR, "#cafe_main"))
        next_mark = "/_next/static/" in driver.page_source
        return (not has_iframe) and next_mark
    except Exception:
        return False

def robust_get(driver, url, retries=2, wait_complete=True):
    """견고한 페이지 이동 (재시도 + 차단 감지)"""
    for i in range(retries + 1):
        try:
            driver.get(url)
            if wait_complete:
                try:
                    WebDriverWait(driver, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except:
                    pass
            
            # 차단/오류 페이지 감지
            page_source = driver.page_source.lower()
            title = driver.title.lower()
            
            if any(keyword in page_source or keyword in title for keyword in 
                   ["접근이 제한", "오류", "차단", "blocked", "error"]):
                logging.warning(f"⚠️ 차단/오류 페이지 감지, 재시도 {i+1}/{retries+1}")
                time.sleep(1.5)
                continue
                
            return True
            
        except Exception as e:
            logging.warning(f"⚠️ 페이지 이동 실패 (시도 {i+1}): {e}")
            time.sleep(1)
            
    return False

class NaverCafeCrawler:
    """네이버 카페 크롤러 - 클래식 엔드포인트 우회 버전"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.content_extractor = None
        self.setup_driver()
    
    def collect_article_ids_from_classic_list(self):
        """
        클래식 ArticleList에서 articleid 전수집 (문자열로만 수집)
        """
        ids = set()
        
        # iframe 전환 시도 (클래식 리스트도 iframe 안쪽인 경우가 많음)
        switched = self.switch_to_cafe_iframe(max_tries=2, timeout_each=20, debug_screenshot=False)
        
        if not switched:
            # iframe 없는 경우 페이지 소스에서 직접 파싱
            logging.info("📄 iframe 없음, 페이지 소스에서 직접 articleid 추출")
            html = self.driver.page_source
            found_ids = re.findall(r"articleid=(\d+)", html)
            ids.update(found_ids)
            logging.info(f"✅ 페이지 소스에서 {len(found_ids)}개 articleid 발견")
            return list(ids)
        
        # iframe 내부에서 링크 수집
        try:
            anchors = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='articleid=']")
            logging.info(f"🔍 iframe 내부에서 {len(anchors)}개 링크 발견")
            
            for anchor in anchors:
                try:
                    href = anchor.get_attribute("href") or ""
                    match = re.search(r"articleid=(\d+)", href)
                    if match:
                        article_id = match.group(1)
                        ids.add(article_id)
                        
                        # 제목도 함께 로깅 (디버깅용)
                        title = anchor.text.strip()[:30]
                        if title:
                            logging.debug(f"  📝 ID {article_id}: {title}...")
                            
                except Exception as e:
                    logging.debug(f"링크 처리 중 오류: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"❌ iframe 내부 링크 수집 실패: {e}")
            
        logging.info(f"✅ 총 {len(ids)}개 고유 articleid 수집 완료")
        return list(ids)
        
    def setup_driver(self):
        """Selenium 드라이버 설정 - 봇 탐지 방지 및 안정성 강화"""
        options = Options()
        
        # GitHub Actions 환경
        if os.getenv('GITHUB_ACTIONS'):
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
        
        # 봇 탐지 방지 및 안정성 강화 옵션
        options.add_argument('--window-size=1440,900')  # 일반적인 데스크톱 해상도
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--lang=ko-KR')  # 한국어 환경 강제
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # 이미지 로딩 비활성화로 속도 향상
        
        # 일반 사용자 User-Agent (봇 탐지 방지)
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        
        # 자동화 탐지 방지
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 추가 성능 및 안정성 옵션
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-ipc-flooding-protection')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 25)  # 타임아웃 증가
            
            # 자동화 탐지 방지 스크립트 실행
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko', 'en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                '''
            })
            
            # 새로운 콘텐츠 추출기 초기화
            extraction_config = ExtractionConfig(
                timeout_seconds=int(os.getenv('CONTENT_EXTRACTION_TIMEOUT', '30')),
                min_content_length=int(os.getenv('CONTENT_MIN_LENGTH', '30')),
                max_content_length=int(os.getenv('CONTENT_MAX_LENGTH', '2000')),
                retry_count=int(os.getenv('EXTRACTION_RETRY_COUNT', '3')),
                enable_debug_screenshot=os.getenv('DEBUG_SCREENSHOT_ENABLED', 'true').lower() == 'true'
            )
            
            self.content_extractor = ContentExtractor(self.driver, self.wait, extraction_config)
            
            logging.info("✅ 크롬 드라이버 및 콘텐츠 추출기 초기화 성공 (봇 탐지 방지 적용)")
        except Exception as e:
            logging.error(f"❌ 드라이버 초기화 실패: {e}")
            raise
    
    def login_naver(self):
        """네이버 로그인 - 자동화 탐지 방지 강화"""
        try:
            logging.info("🔐 네이버 로그인 시작")
            
            # 로그인 페이지로 이동
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(5)  # 로딩 시간 증가
            
            # 페이지 로딩 완료 대기
            self.wait_dom_ready(timeout=15)
            
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
        게시물 내용 가져오기 - iframe 컨텍스트 안전 관리
        """
        try:
            logging.info(f"🚀 내용 추출 시작: {url}")
            
            # 현재 URL이 이미 게시물 페이지인지 확인
            current_url = self.driver.current_url
            if url not in current_url:
                # 다른 페이지라면 이동
                self.driver.get(url)
                time.sleep(5)
            
            # 로그인 체크
            if 'nid.naver.com' in self.driver.current_url:
                if self.login_naver():
                    self.driver.get(url)
                    time.sleep(5)
                else:
                    return "로그인 필요"
            
            # iframe 전환 (이미 전환되어 있을 수도 있음)
            if not self.switch_to_cafe_iframe():
                logging.warning("⚠️ iframe 전환 실패, 메인 페이지에서 시도")
            
            # 페이지 완전 로딩 대기
            time.sleep(3)
            
            # 디버깅: 현재 페이지 정보 출력
            logging.info(f"🔍 현재 URL: {self.driver.current_url}")
            logging.info(f"🔍 페이지 제목: {self.driver.title}")
            
            # 강화된 내용 추출
            content = self._extract_content_enhanced()
            
            if content and len(content.strip()) > 10:
                logging.info(f"✅ 내용 추출 성공: {len(content)}자")
                return content[:1500]
            else:
                logging.warning("⚠️ 내용 추출 실패 또는 내용이 너무 짧음")
                return f"내용을 불러올 수 없습니다.\n원본 링크: {url}"
                
        except Exception as e:
            logging.error(f"❌ 내용 추출 오류: {e}")
            return f"추출 오류: {str(e)[:50]}\n원본 링크: {url}"
    
    def _extract_content_enhanced(self) -> str:
        """
        강화된 내용 추출 - 다양한 에디터 형식 지원
        """
        try:
            # JavaScript로 통합 추출
            js_extract_content = """
            var content = [];
            
            // 방법 1: SmartEditor 3.0 (se-main-container)
            var seMainContainer = document.querySelector('.se-main-container');
            if (seMainContainer) {
                var paragraphs = seMainContainer.querySelectorAll('p.se-text-paragraph, .se-component, .se-text');
                for (var p of paragraphs) {
                    var text = p.innerText || p.textContent;
                    if (text && text.trim().length > 3) {
                        content.push(text.trim());
                    }
                }
            }
            
            // 방법 2: SmartEditor 2.0 (ContentRenderer)
            if (content.length === 0) {
                var contentRenderer = document.querySelector('.ContentRenderer, #postViewArea');
                if (contentRenderer) {
                    var text = contentRenderer.innerText || contentRenderer.textContent;
                    if (text && text.trim().length > 10) {
                        content.push(text.trim());
                    }
                }
            }
            
            // 방법 3: 일반 에디터 (#content-area, .article_viewer)
            if (content.length === 0) {
                var selectors = ['#content-area', '.article_viewer', '.post-content', '.article-content', '#tbody'];
                for (var sel of selectors) {
                    var elem = document.querySelector(sel);
                    if (elem) {
                        var text = elem.innerText || elem.textContent;
                        if (text && text.trim().length > 10) {
                            content.push(text.trim());
                            break;
                        }
                    }
                }
            }
            
            // 방법 4: 모든 텍스트 노드 수집 (최후의 수단)
            if (content.length === 0) {
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            var text = node.textContent.trim();
                            var parent = node.parentElement;
                            
                            // 부모 요소 체크
                            if (parent) {
                                var tagName = parent.tagName.toLowerCase();
                                var className = parent.className || '';
                                
                                // 제외할 요소들
                                if (tagName === 'script' || tagName === 'style' || 
                                    className.includes('menu') || className.includes('nav') ||
                                    className.includes('footer') || className.includes('header')) {
                                    return NodeFilter.FILTER_REJECT;
                                }
                            }
                            
                            // 텍스트 내용 체크
                            if (text.length > 5 && 
                                !text.includes('javascript') && 
                                !text.includes('로그인') &&
                                !text.includes('NAVER') &&
                                !text.includes('메뉴') &&
                                !text.includes('댓글')) {
                                return NodeFilter.FILTER_ACCEPT;
                            }
                            return NodeFilter.FILTER_REJECT;
                        }
                    }
                );
                
                var textNodes = [];
                var node;
                while (node = walker.nextNode()) {
                    textNodes.push(node.textContent.trim());
                }
                
                if (textNodes.length > 0) {
                    content = textNodes.slice(0, 15); // 처음 15개만
                }
            }
            
            // 중복 제거 및 정리
            var uniqueContent = [];
            var seen = new Set();
            
            for (var text of content) {
                if (text && text.length > 3 && !seen.has(text)) {
                    seen.add(text);
                    uniqueContent.push(text);
                }
            }
            
            return uniqueContent.join('\\n\\n');
            """
            
            result = self.driver.execute_script(js_extract_content)
            
            if result and len(result.strip()) > 10:
                logging.info(f"✅ 강화된 JavaScript 추출 성공: {len(result)}자")
                return result
            
            # 폴백: 기존 방식
            return self._extract_with_javascript()
            
        except Exception as e:
            logging.error(f"❌ 강화된 추출 실패: {e}")
            return self._extract_with_javascript()
    
    def _extract_with_javascript(self) -> str:
        """JavaScript를 사용한 직접 DOM 조작"""
        try:
            # 1. SmartEditor 텍스트 추출 JavaScript
            js_script = """
            var content = [];
            
            // 방법 1: se-text-paragraph 내의 모든 텍스트
            var paragraphs = document.querySelectorAll('p.se-text-paragraph');
            paragraphs.forEach(function(p) {
                var spans = p.querySelectorAll('span');
                spans.forEach(function(span) {
                    var text = span.innerText || span.textContent;
                    if (text && text.trim().length > 2) {
                        content.push(text.trim());
                    }
                });
                
                // span이 없으면 p 직접 텍스트
                if (spans.length === 0) {
                    var text = p.innerText || p.textContent;
                    if (text && text.trim().length > 2) {
                        content.push(text.trim());
                    }
                }
            });
            
            // 방법 2: se-component 내의 모든 텍스트
            if (content.length === 0) {
                var components = document.querySelectorAll('.se-component');
                components.forEach(function(comp) {
                    var text = comp.innerText || comp.textContent;
                    if (text && text.trim().length > 5) {
                        content.push(text.trim());
                    }
                });
            }
            
            // 방법 3: se-main-container 전체
            if (content.length === 0) {
                var mainContainer = document.querySelector('.se-main-container');
                if (mainContainer) {
                    var text = mainContainer.innerText || mainContainer.textContent;
                    if (text && text.trim().length > 10) {
                        content.push(text.trim());
                    }
                }
            }
            
            // 방법 4: 모든 텍스트 노드 수집 (최후의 수단)
            if (content.length === 0) {
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            var text = node.textContent.trim();
                            if (text.length > 5 && 
                                !text.includes('javascript') && 
                                !text.includes('login') &&
                                !text.includes('NAVER')) {
                                return NodeFilter.FILTER_ACCEPT;
                            }
                            return NodeFilter.FILTER_REJECT;
                        }
                    }
                );
                
                var textNodes = [];
                var node;
                while (node = walker.nextNode()) {
                    textNodes.push(node.textContent.trim());
                }
                
                if (textNodes.length > 0) {
                    content = textNodes.slice(0, 20); // 처음 20개만
                }
            }
            
            return content.join('\\n');
            """
            
            result = self.driver.execute_script(js_script)
            
            if result and len(result.strip()) > 10:
                logging.info(f"✅ JavaScript 스크립트 성공: {len(result)}자")
                return result
            
            # 폴백: 더 간단한 JavaScript
            simple_js = """
            var allText = document.body.innerText || document.body.textContent;
            var lines = allText.split('\\n');
            var goodLines = [];
            
            for (var i = 0; i < lines.length && goodLines.length < 15; i++) {
                var line = lines[i].trim();
                if (line.length > 5 && 
                    !line.includes('javascript') && 
                    !line.includes('login') &&
                    !line.includes('NAVER Corp')) {
                    goodLines.push(line);
                }
            }
            
            return goodLines.join('\\n');
            """
            
            fallback_result = self.driver.execute_script(simple_js)
            if fallback_result:
                logging.info(f"✅ JavaScript 폴백 성공: {len(fallback_result)}자")
                return fallback_result
            
            return ""
            
        except Exception as e:
            logging.error(f"❌ JavaScript 실행 실패: {e}")
            return ""
    
    def _extract_author_with_javascript(self, url: str) -> str:
        """JavaScript로 작성자 추출"""
        try:
            # 현재 URL이 게시물 페이지인지 확인
            current_url = self.driver.current_url
            if url not in current_url:
                return "Unknown"
            
            # JavaScript로 작성자 추출
            author_js = """
            var author = '';
            
            // 방법 1: button.nickname
            var nicknameBtn = document.querySelector('button.nickname');
            if (nicknameBtn) {
                author = nicknameBtn.innerText || nicknameBtn.textContent;
            }
            
            // 방법 2: button[id*="writerInfo"]
            if (!author) {
                var writerBtn = document.querySelector('button[id*="writerInfo"]');
                if (writerBtn) {
                    author = writerBtn.innerText || writerBtn.textContent;
                }
            }
            
            // 방법 3: .nickname 클래스
            if (!author) {
                var nicknameElem = document.querySelector('.nickname');
                if (nicknameElem) {
                    author = nicknameElem.innerText || nicknameElem.textContent;
                }
            }
            
            // 방법 4: 모든 button 태그에서 찾기
            if (!author) {
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = btn.innerText || btn.textContent;
                    if (text && text.trim().length > 0 && text.trim().length < 20) {
                        // 작성자 같은 텍스트인지 확인
                        if (!text.includes('로그인') && !text.includes('메뉴') && 
                            !text.includes('검색') && !text.includes('등록')) {
                            author = text.trim();
                            break;
                        }
                    }
                }
            }
            
            return author ? author.trim() : '';
            """
            
            result = self.driver.execute_script(author_js)
            
            if result and len(result.strip()) > 0:
                logging.info(f"✅ JavaScript 작성자 추출 성공: {result}")
                return result.strip()
            
            return "Unknown"
            
        except Exception as e:
            logging.error(f"❌ JavaScript 작성자 추출 실패: {e}")
            return "Unknown"
    
    def _extract_with_alternative_method(self) -> str:
        """대체 추출 방법 - 더 직접적인 접근"""
        try:
            # 더 간단한 JavaScript로 실제 텍스트만 추출
            simple_js = """
            // 모든 텍스트 노드를 찾아서 실제 내용만 추출
            var walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            var textContent = [];
            var node;
            
            while (node = walker.nextNode()) {
                var text = node.textContent.trim();
                var parent = node.parentElement;
                
                // 부모 요소가 se-text-paragraph인 경우 우선 수집
                if (parent && parent.className && parent.className.includes('se-text-paragraph')) {
                    if (text.length > 3 && !text.includes('javascript') && !text.includes('We\\'re sorry')) {
                        textContent.push(text);
                    }
                }
            }
            
            // se-text-paragraph에서 찾지 못했으면 일반 텍스트 수집
            if (textContent.length === 0) {
                walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                while (node = walker.nextNode()) {
                    var text = node.textContent.trim();
                    if (text.length > 10 && 
                        !text.includes('javascript') && 
                        !text.includes('We\\'re sorry') &&
                        !text.includes('NAVER') &&
                        !text.includes('로그인')) {
                        textContent.push(text);
                    }
                }
            }
            
            return textContent.slice(0, 10).join('\\n');
            """
            
            result = self.driver.execute_script(simple_js)
            
            if result and len(result.strip()) > 20:
                logging.info(f"✅ 대체 방법 성공: {len(result)}자")
                return result
            
            return "대체 방법도 실패"
            
        except Exception as e:
            logging.error(f"❌ 대체 방법 실패: {e}")
            return "대체 방법 오류"
    
    def _is_system_text(self, text: str) -> bool:
        """시스템 텍스트인지 판단"""
        system_keywords = [
            'javascript', 'cookie', 'privacy', 'terms', 'login', 'menu',
            'navigation', 'footer', 'header', 'advertisement', 'loading',
            'ID/Phone number', 'Stay Signed in', 'IP Security', 'Passkey',
            'NAVER Corp', '네이버', '로그인', '메뉴', '광고'
        ]
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in system_keywords)
    
    def _contains_login_text(self, text: str) -> bool:
        """로그인 관련 텍스트 포함 여부"""
        login_keywords = [
            'ID/Phone number', 'Stay Signed in', 'IP Security', 'Passkey login',
            'NAVER Corp', 'All Rights Reserved', 'sign in', 'login'
        ]
        
        return any(keyword in text for keyword in login_keywords)
    

    
    def _extract_real_content(self) -> str:
        """실제 게시물 내용만 추출"""
        try:
            content_parts = []
            
            # F-E 카페 SmartEditor 선택자들 (우선순위 순)
            selectors = [
                # SmartEditor 3.0
                '.se-main-container .se-component .se-text-paragraph',
                '.se-main-container .se-text',
                '.se-main-container p',
                '.se-main-container div',
                
                # SmartEditor 2.0
                '.se-component-content',
                '.se-text-paragraph',
                
                # 일반 게시물
                '.article_viewer .se-main-container',
                '.post-view .article-board-content',
                '.ArticleContentBox',
                '#content-area .se-main-container',
                
                # 레거시
                '.article_viewer',
                '.board-content',
                '.content_text',
                '#content-area'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 10:
                                # 불필요한 텍스트 필터링
                                if not self._is_unwanted_text(text):
                                    content_parts.append(text)
                        
                        if content_parts:
                            content = '\n'.join(content_parts)
                            if len(content) > 50:
                                logging.info(f"✅ 선택자 '{selector}' 성공: {len(content)}자")
                                return content
                except Exception as e:
                    logging.debug(f"선택자 {selector} 실패: {e}")
                    continue
            
            # 모든 선택자 실패 시 텍스트 요소 전체 스캔
            logging.info("🔍 전체 텍스트 요소 스캔 시작")
            all_text_elements = self.driver.find_elements(By.CSS_SELECTOR, 'p, div, span')
            
            for element in all_text_elements:
                try:
                    text = element.text.strip()
                    if text and len(text) > 20 and not self._is_unwanted_text(text):
                        content_parts.append(text)
                except:
                    continue
            
            if content_parts:
                # 중복 제거
                unique_parts = list(dict.fromkeys(content_parts))
                content = '\n'.join(unique_parts[:15])  # 처음 15개만
                if len(content) > 100:
                    logging.info(f"✅ 전체 스캔 성공: {len(content)}자")
                    return content
            
            return ""
            
        except Exception as e:
            logging.error(f"❌ 실제 내용 추출 실패: {e}")
            return ""
    
    def _is_unwanted_text(self, text: str) -> bool:
        """불필요한 텍스트인지 판단"""
        unwanted_keywords = [
            'ID/Phone number', 'Stay Signed in', 'IP Security', 'Passkey login',
            'NAVER Corp', 'All Rights Reserved', 'javascript', 'cookie',
            'privacy', 'terms', 'login', 'sign in', 'forgot', 'customer service',
            'menu', 'navigation', 'footer', 'header', 'sidebar', 'advertisement',
            'loading', 'please wait', 'error', '오류', '로딩', '메뉴', '네비게이션'
        ]
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in unwanted_keywords)

    def _direct_content_extraction(self, url: str) -> str:
        """직접적인 내용 추출 방법"""
        try:
            logging.info(f"🎯 직접 추출 시작: {url}")
            
            # 페이지 이동
            self.driver.get(url)
            time.sleep(8)  # 충분한 로딩 시간
            
            # F-E 카페 특화 추출
            content = ""
            
            # 1. iframe 전환 시도
            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it('cafe_main'))
                logging.info("✅ iframe 전환 성공")
                time.sleep(5)
            except:
                logging.warning("⚠️ iframe 전환 실패, 메인 페이지에서 시도")
            
            # 2. F-E 카페 전용 선택자들
            fe_selectors = [
                '.se-main-container .se-component',
                '.se-main-container',
                '.article_viewer .se-main-container',
                '.post-view .se-main-container',
                '.ArticleContentBox .se-main-container',
                '.se-component-content',
                '.se-text-paragraph',
                '.article-board-content',
                '.post-content',
                '#content-area .se-main-container'
            ]
            
            for selector in fe_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 30:
                                content += text + "\n"
                        
                        if content and len(content.strip()) > 50:
                            logging.info(f"✅ 직접 추출 성공 (선택자: {selector}): {len(content)}자")
                            self.driver.switch_to.default_content()
                            return content.strip()
                except Exception as e:
                    logging.debug(f"선택자 {selector} 실패: {e}")
                    continue
            
            # 3. 일반적인 선택자들
            general_selectors = [
                '.article_viewer',
                '.board-content',
                '.content_text',
                '#content-area',
                '.post-content',
                '.article-content'
            ]
            
            for selector in general_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        text = elements[0].text.strip()
                        if text and len(text) > 50:
                            logging.info(f"✅ 일반 선택자 성공 ({selector}): {len(text)}자")
                            self.driver.switch_to.default_content()
                            return text
                except:
                    continue
            
            self.driver.switch_to.default_content()
            return ""
            
        except Exception as e:
            logging.error(f"❌ 직접 추출 실패: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return ""
    
    def _fallback_content_extraction(self, url: str) -> str:
        """폴백 내용 추출 방법 - 최후의 수단"""
        try:
            logging.info(f"🆘 최후 수단 추출 시도: {url}")
            
            # 페이지 새로고침
            self.driver.refresh()
            time.sleep(10)
            
            # 모든 텍스트 요소에서 추출 시도
            try:
                # 모든 p, div, span 태그에서 텍스트 수집
                text_elements = self.driver.find_elements(By.CSS_SELECTOR, 'p, div, span')
                content_parts = []
                
                for element in text_elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) > 10:
                            # 불필요한 텍스트 필터링
                            if not any(skip in text.lower() for skip in [
                                'javascript', 'cookie', 'privacy', 'terms', 'login', 'menu',
                                'navigation', 'footer', 'header', 'sidebar', 'advertisement'
                            ]):
                                content_parts.append(text)
                    except:
                        continue
                
                if content_parts:
                    # 중복 제거 및 정리
                    unique_parts = []
                    for part in content_parts:
                        if part not in unique_parts and len(part) > 15:
                            unique_parts.append(part)
                    
                    final_content = '\n'.join(unique_parts[:10])  # 처음 10개 문단만
                    if len(final_content) > 100:
                        logging.info(f"✅ 최후 수단 성공: {len(final_content)}자")
                        return final_content
            except:
                pass
            
            # 정말 최후의 수단: 제목만이라도 저장
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, 'h1, h2, h3, .title, .subject')
                title = title_element.text.strip()
                if title:
                    return f"[제목만 추출됨]\n\n{title}\n\n전체 내용을 보려면 링크를 확인하세요: {url}"
            except:
                pass
            
            return f"[내용 추출 완전 실패]\n\n게시물 링크: {url}\n\n수동 확인이 필요합니다."
            
        except Exception as e:
            logging.error(f"❌ 최후 수단도 실패: {e}")
            return f"[시스템 오류]\n\n게시물 링크: {url}\n\n오류: {str(e)[:100]}"
    
    def wait_dom_ready(self, timeout=30):
        """DOM 완전 로딩 대기"""
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except:
            return False
    
    def switch_to_cafe_iframe(self, max_tries=3, timeout_each=25, debug_screenshot=False):
        """
        카페 iframe으로 초탄탄하게 전환 - 다중 셀렉터 + 재시도 + 디버깅
        """
        # 다양한 iframe 셀렉터 (네이버 카페 변형 대응)
        iframe_selectors = [
            "#cafe_main",
            "iframe#cafe_main", 
            "iframe[id*='cafe_main']",
            "iframe[src*='ArticleList']",
            "iframe[src*='ArticleRead']", 
            "iframe[src*='/cafes/'][src*='/articles']",
            "iframe[name='cafe_main']",
            "iframe[id='cafe_main']"
        ]
        
        for attempt in range(1, max_tries + 1):
            try:
                logging.info(f"🔄 iframe 전환 시도 {attempt}/{max_tries}")
                
                # 기본 컨텍스트로 복귀
                self.driver.switch_to.default_content()
                
                # DOM 완전 로딩 대기
                if not self.wait_dom_ready(timeout=timeout_each // 2):
                    logging.warning(f"⚠️ DOM 로딩 대기 타임아웃 (시도 {attempt})")
                
                # 스크롤로 지연 로드 트리거
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(0.5)
                except:
                    pass
                
                # 현재 페이지 상태 로깅
                try:
                    current_info = self.driver.execute_script("""
                        return {
                            url: location.href,
                            title: document.title,
                            readyState: document.readyState,
                            width: window.innerWidth,
                            height: window.innerHeight,
                            userAgent: navigator.userAgent.substring(0, 100)
                        };
                    """)
                    logging.info(f"📊 페이지 상태: {current_info['url'][:80]}...")
                    logging.info(f"📊 제목: {current_info['title'][:50]}...")
                    logging.info(f"📊 해상도: {current_info['width']}x{current_info['height']}")
                except:
                    pass
                
                # 다중 셀렉터로 iframe 찾기 시도
                for selector in iframe_selectors:
                    try:
                        logging.debug(f"🔍 iframe 셀렉터 시도: {selector}")
                        
                        # iframe 존재 확인
                        iframe_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if not iframe_elements:
                            continue
                        
                        logging.info(f"✅ iframe 발견: {selector}")
                        
                        # iframe 전환 시도
                        WebDriverWait(self.driver, timeout_each).until(
                            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, selector))
                        )
                        
                        # 전환 성공 확인
                        time.sleep(2)
                        try:
                            # iframe 내부에서 간단한 JavaScript 실행으로 확인
                            self.driver.execute_script("return document.readyState;")
                            logging.info(f"✅ iframe 전환 성공: {selector}")
                            return True
                        except:
                            # iframe 전환은 됐지만 내부 로딩이 안 된 경우
                            logging.warning(f"⚠️ iframe 전환됐지만 내부 로딩 미완료: {selector}")
                            self.driver.switch_to.default_content()
                            continue
                            
                    except Exception as e:
                        logging.debug(f"❌ {selector} 실패: {e}")
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
                        continue
                
                # 모든 셀렉터 실패 시 페이지 새로고침 후 재시도
                if attempt < max_tries:
                    logging.warning(f"⚠️ 모든 iframe 셀렉터 실패, 페이지 새로고침 후 재시도 (시도 {attempt})")
                    
                    # 현재 URL에 데스크톱 강제 힌트 추가
                    current_url = self.driver.current_url
                    if '&web=1' not in current_url:
                        if '?' in current_url:
                            current_url += '&web=1'
                        else:
                            current_url += '?web=1'
                    
                    self.driver.get(current_url)
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                logging.error(f"❌ iframe 전환 시도 {attempt} 중 오류: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
        
        # 모든 시도 실패 시 디버깅 정보 수집
        if debug_screenshot or os.getenv('DEBUG_SCREENSHOT_ENABLED', 'true').lower() == 'true':
            try:
                timestamp = int(time.time())
                screenshot_path = f"iframe_fail_{timestamp}.png"
                self.driver.save_screenshot(screenshot_path)
                logging.error(f"📷 iframe 실패 스크린샷 저장: {screenshot_path}")
                
                # HTML 일부 로깅
                html_snippet = self.driver.page_source[:2000]
                logging.error(f"🔍 HTML 스니펫: {html_snippet[:500]}...")
                
                # 현재 페이지 정보 상세 로깅
                try:
                    debug_info = self.driver.execute_script("""
                        return {
                            url: location.href,
                            title: document.title,
                            readyState: document.readyState,
                            iframes: Array.from(document.querySelectorAll('iframe')).map(f => ({
                                id: f.id,
                                name: f.name,
                                src: f.src ? f.src.substring(0, 100) : '',
                                className: f.className
                            }))
                        };
                    """)
                    logging.error(f"🔍 디버그 정보: {debug_info}")
                except:
                    pass
                    
            except Exception as debug_error:
                logging.error(f"❌ 디버깅 정보 수집 실패: {debug_error}")
        
        logging.error(f"❌ iframe 전환 완전 실패 (총 {max_tries}회 시도)")
        return False
    
    def crawl_cafe(self, cafe_config: Dict) -> List[Dict]:
        """카페 게시물 크롤링 - 클래식 엔드포인트 우회 버전 💥"""
        results = []
        
        try:
            club_id = cafe_config['club_id']
            board_id = cafe_config['board_id']
            
            # 1단계: SPA vs 클래식 전략 결정
            force_classic = os.getenv("FORCE_CLASSIC", "0") == "1"
            
            if not force_classic:
                # 기존 SPA 메뉴 URL로 먼저 시도
                spa_url = f"{cafe_config['url']}/cafes/{club_id}/menus/{board_id}?viewType=L&web=1"
                logging.info(f"📍 SPA URL 시도: {spa_url}")
                
                if robust_get(self.driver, spa_url):
                    if is_spa_list_page(self.driver):
                        logging.warning("⚠️ SPA 레이아웃 감지, 클래식으로 폴백")
                        force_classic = True
                    else:
                        # SPA가 아니면 iframe 전환 시도
                        if not self.switch_to_cafe_iframe(max_tries=2, timeout_each=15, debug_screenshot=False):
                            logging.warning("⚠️ SPA에서 iframe 전환 실패, 클래식으로 폴백")
                            force_classic = True
                else:
                    logging.warning("⚠️ SPA URL 접근 실패, 클래식으로 폴백")
                    force_classic = True
            
            # 2단계: 클래식 리스트로 강제/폴백
            if force_classic:
                classic_list_url = build_classic_list_url(club_id, board_id, user_display=50)
                logging.info(f"🔧 클래식 URL로 전환: {classic_list_url}")
                
                if not robust_get(self.driver, classic_list_url):
                    logging.error("❌ 클래식 리스트 URL 접근 실패")
                    return results
            
            # 3단계: 리스트에서 articleid를 문자열로 전부 수집
            logging.info("📊 게시물 ID 수집 시작...")
            article_ids = self.collect_article_ids_from_classic_list()
            
            # 수집 실패 시 다중 페이지 탐색
            if not article_ids:
                logging.warning("⚠️ 첫 페이지에서 수집 실패, 다중 페이지 탐색")
                
                for page in range(1, 4):  # 1~3페이지 탐색
                    page_url = build_classic_list_url(club_id, board_id, user_display=50, page=page)
                    logging.info(f"🔍 {page}페이지 탐색: {page_url}")
                    
                    if robust_get(self.driver, page_url):
                        page_ids = self.collect_article_ids_from_classic_list()
                        article_ids.extend(page_ids)
                        logging.info(f"✅ {page}페이지에서 {len(page_ids)}개 ID 수집")
                    
                    if len(article_ids) >= 20:  # 충분히 수집되면 중단
                        break
                
                # 중복 제거
                article_ids = list(dict.fromkeys(article_ids))
            
            if not article_ids:
                logging.error("❌ 모든 페이지에서 articleid 수집 실패")
                return results
            
            logging.info(f"📊 총 {len(article_ids)}개 게시물 ID 수집 완료")
            
            # 4단계: 각 글을 클래식 Read URL로 개별 처리
            max_articles = 10
            processed = 0
            
            for i, article_id in enumerate(article_ids[:20]):
                if processed >= max_articles:
                    logging.info(f"🎯 목표 달성: {processed}개 처리 완료")
                    break
                
                try:
                    logging.info(f"🔄 [{i+1}/{min(len(article_ids), 20)}] 게시물 처리 중 (ID: {article_id})")
                    
                    # 클래식 Read URL로 이동
                    read_url = build_classic_read_url(club_id, article_id)
                    
                    if not robust_get(self.driver, read_url):
                        logging.warning(f"⚠️ [{i+1}] 게시물 페이지 접근 실패: {read_url}")
                        continue
                    
                    # iframe 전환 시도 (실패해도 계속 진행)
                    iframe_success = self.switch_to_cafe_iframe(max_tries=2, timeout_each=20, debug_screenshot=False)
                    if not iframe_success:
                        logging.warning(f"⚠️ [{i+1}] iframe 전환 실패, 페이지 소스에서 직접 추출 시도")
                    
                    # 제목 추출 (다중 셀렉터)
                    title = ""
                    title_selectors = ["#articleTitle", ".title_text", "h3", ".article_title", ".subject", ".title"]
                    for selector in title_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements and elements[0].text.strip():
                                title = elements[0].text.strip()
                                break
                        except:
                            continue
                    
                    if not title:
                        title = f"제목 추출 실패 (ID: {article_id})"
                    
                    # 작성자 추출 (다중 셀렉터)
                    author = ""
                    author_selectors = [".nickname", ".nick", ".writer", ".nick_area", ".article_writer", ".author"]
                    for selector in author_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements and elements[0].text.strip():
                                author = elements[0].text.strip()
                                break
                        except:
                            continue
                    
                    if not author:
                        author = "Unknown"
                    
                    # 본문 추출 (다중 셀렉터)
                    content = ""
                    content_selectors = [
                        "#tbody", ".article_view", ".se-main-container", 
                        ".ContentRenderer", ".content_area", ".post_ct", ".article_content"
                    ]
                    for selector in content_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements and elements[0].text.strip():
                                content = elements[0].text.strip()
                                break
                        except:
                            continue
                    
                    # 셀렉터로 실패 시 JavaScript 백업 추출
                    if not content or len(content) < 20:
                        try:
                            content = self.driver.execute_script(
                                "return document.body.innerText || document.body.textContent || '';"
                            ) or ""
                            
                            # 불필요한 텍스트 필터링
                            if content:
                                lines = content.split('\n')
                                filtered_lines = []
                                for line in lines:
                                    line = line.strip()
                                    if (line and len(line) > 3 and 
                                        not any(skip in line.lower() for skip in 
                                               ['로그인', '메뉴', '댓글', '광고', 'naver', '네이버'])):
                                        filtered_lines.append(line)
                                
                                content = '\n'.join(filtered_lines[:20])  # 처음 20줄만
                        except:
                            pass
                    
                    if not content or len(content) < 10:
                        content = f"내용을 불러올 수 없습니다.\n원본 링크: {read_url}"
                    
                    # 작성일 추출
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    try:
                        date_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                            '.date, .time, .write_date, .article_date, .post_date')
                        for elem in date_elements:
                            date_text = elem.text.strip()
                            if date_text and len(date_text) > 5:
                                date_str = date_text.replace('.', '-').rstrip('-')
                                break
                    except:
                        pass
                    
                    logging.info(f"📝 [{i+1}] 제목: {title[:50]}...")
                    logging.info(f"👤 [{i+1}] 작성자: {author}")
                    logging.info(f"📄 [{i+1}] 내용 길이: {len(content)}자")
                    
                    # 데이터 구성
                    data = {
                        'title': title,
                        'author': author,
                        'date': date_str,
                        'url': read_url,
                        'article_id': article_id,
                        'content': content[:1500],  # 길이 제한
                        'cafe_name': cafe_config['name'],
                        'crawled_at': datetime.now().isoformat()
                    }
                    
                    results.append(data)
                    processed += 1
                    logging.info(f"✅ [{processed}/{max_articles}] 완료: {title[:30]}...")
                    
                    # 다음 게시물 처리 전 잠시 대기
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"❌ [{i+1}] 게시물 처리 오류: {e}")
                    continue
            
            logging.info(f"🎯 클래식 엔드포인트 크롤링 완료: {processed}개 성공 (전체 {len(article_ids)}개 중)")
            
        except Exception as e:
            logging.error(f"❌ 크롤링 오류: {e}")
            
            # 실패 시 상세 디버깅 정보 수집
            try:
                debug_info = {
                    'current_url': self.driver.current_url,
                    'title': self.driver.title,
                    'is_spa': is_spa_list_page(self.driver),
                    'force_classic': os.getenv("FORCE_CLASSIC", "0"),
                    'page_source_length': len(self.driver.page_source)
                }
                logging.error(f"🔍 실패 시 디버깅 정보: {debug_info}")
                
                # 실패 스크린샷 저장
                if os.getenv('DEBUG_SCREENSHOT_ENABLED', 'true').lower() == 'true':
                    timestamp = int(time.time())
                    screenshot_path = f"crawl_fail_{timestamp}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logging.error(f"📷 실패 스크린샷 저장: {screenshot_path}")
                    
            except Exception as debug_error:
                logging.error(f"❌ 디버깅 정보 수집 실패: {debug_error}")
        
        return results
            
    def _collect_article_urls_safely(self, cafe_config: Dict) -> List[Dict]:
        """
        게시물 URL을 안전하게 문자열로 수집 (StaleElement 방지)
        """
        try:
            # JavaScript로 모든 게시물 정보를 한 번에 수집
            js_collect_articles = f"""
            const baseUrl = location.origin;
            const pathParts = location.pathname.split('/');
            const cafeId = pathParts[2]; // f-e
            const clubId = '{cafe_config['club_id']}';
            const menuId = '{cafe_config['board_id']}';
            
            function buildArticleUrl(articleId) {{
                return `${{baseUrl}}/f-e/cafes/${{clubId}}/articles/${{articleId}}?boardtype=L&menuid=${{menuId}}&referrerAllArticles=false`;
            }}
            
            const articles = [];
            
            // 방법 1: div.inner_list 구조 (새로운 네이버 카페)
            const innerListItems = document.querySelectorAll('div.inner_list');
            for (const item of innerListItems) {{
                try {{
                    const link = item.querySelector('a.article, a[href*="articles"]');
                    if (!link) continue;
                    
                    let articleId = '';
                    let url = '';
                    let title = '';
                    let author = '';
                    
                    // URL에서 articleId 추출
                    const href = link.getAttribute('href') || '';
                    const match = href.match(/articles\/(\d+)/);
                    if (match) {{
                        articleId = match[1];
                        url = buildArticleUrl(articleId);
                    }} else {{
                        // onclick에서 추출 시도
                        const onclick = link.getAttribute('onclick') || '';
                        const onclickMatch = onclick.match(/articles\/(\d+)/) || onclick.match(/ArticleRead[^0-9]*([0-9]+)/i);
                        if (onclickMatch) {{
                            articleId = onclickMatch[1];
                            url = buildArticleUrl(articleId);
                        }} else {{
                            url = href.startsWith('http') ? href : baseUrl + href;
                        }}
                    }}
                    
                    // 제목 추출
                    title = link.innerText || link.textContent || '';
                    title = title.replace(/\\[.*?\\]/g, '').trim(); // [팝니다] 같은 태그 제거
                    
                    // 작성자 추출 (같은 행에서)
                    const parentRow = item.closest('tr, li, div');
                    if (parentRow) {{
                        const authorElem = parentRow.querySelector('.nickname, span.nickname, .author, .writer, .nick, td.p-nick, .td_name');
                        if (authorElem) {{
                            author = authorElem.innerText || authorElem.textContent || '';
                        }}
                    }}
                    
                    // 공지사항 필터링
                    const isNotice = (
                        title.includes('공지') || 
                        title.includes('[공지]') || 
                        title.startsWith('공지') ||
                        item.querySelector('.notice, .icon_notice, img[alt="공지"]') ||
                        item.classList.contains('notice')
                    );
                    
                    if (!isNotice && title.length > 2 && url) {{
                        articles.push({{
                            title: title.trim(),
                            url: url,
                            author: author.trim() || 'Unknown',
                            article_id: articleId
                        }});
                    }}
                }} catch (e) {{
                    console.log('게시물 처리 중 오류:', e);
                }}
            }}
            
            // 방법 2: 테이블 구조 (기존 네이버 카페)
            if (articles.length === 0) {{
                const tableRows = document.querySelectorAll('table tr, .board-list tr, .article-board tr');
                for (const row of tableRows) {{
                    try {{
                        const titleCell = row.querySelector('td.td_article, .td_article, .title, .subject');
                        const authorCell = row.querySelector('td.p-nick, .td_name, .author, .writer, .nickname');
                        
                        if (!titleCell) continue;
                        
                        const link = titleCell.querySelector('a[href*="articles"], a[href*="articleid"]');
                        if (!link) continue;
                        
                        let title = link.innerText || link.textContent || '';
                        let author = '';
                        let url = link.href || '';
                        let articleId = '';
                        
                        // articleId 추출
                        const match = url.match(/articles\/(\d+)/) || url.match(/articleid=(\d+)/);
                        if (match) {{
                            articleId = match[1];
                        }}
                        
                        // 작성자 추출
                        if (authorCell) {{
                            const authorSpan = authorCell.querySelector('span.nickname, .nickname, span');
                            if (authorSpan) {{
                                author = authorSpan.innerText || authorSpan.textContent || '';
                            }} else {{
                                author = authorCell.innerText || authorCell.textContent || '';
                            }}
                        }}
                        
                        // 공지사항 필터링
                        const isNotice = (
                            title.includes('공지') || 
                            title.includes('[공지]') || 
                            title.startsWith('공지') ||
                            row.querySelector('.notice, .icon_notice, img[alt="공지"]') ||
                            row.classList.contains('notice')
                        );
                        
                        if (!isNotice && title.length > 2 && url) {{
                            articles.push({{
                                title: title.trim(),
                                url: url,
                                author: author.trim() || 'Unknown',
                                article_id: articleId
                            }});
                        }}
                    }} catch (e) {{
                        console.log('테이블 행 처리 중 오류:', e);
                    }}
                }}
            }}
            
            return articles;
            """
            
            article_data_list = self.driver.execute_script(js_collect_articles)
            
            if article_data_list:
                logging.info(f"✅ JavaScript로 게시물 수집 성공: {len(article_data_list)}개")
                
                # 수집된 데이터 로깅
                for i, article in enumerate(article_data_list[:5]):  # 처음 5개만 로깅
                    logging.info(f"  [{i+1}] {article['title'][:30]}... (작성자: {article['author']})")
                
                return article_data_list
            else:
                logging.warning("⚠️ JavaScript 수집 실패, 폴백 방식 시도")
                return self._collect_articles_fallback()
                
        except Exception as e:
            logging.error(f"❌ 게시물 URL 수집 중 오류: {e}")
            return self._collect_articles_fallback()
    
    def _collect_articles_fallback(self) -> List[Dict]:
        """
        폴백 방식으로 게시물 수집
        """
        try:
            articles = []
            
            # 기본 선택자들로 시도
            selectors = [
                'div.inner_list',
                '.inner_list', 
                'table tr',
                '.board-list tr',
                '.article-board tr'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logging.info(f"폴백: {selector}로 {len(elements)}개 요소 발견")
                        
                        for i, elem in enumerate(elements[:20]):  # 최대 20개만
                            try:
                                # 링크 찾기
                                link_elem = elem.find_element(By.CSS_SELECTOR, 'a[href*="articles"], a[href*="articleid"]')
                                title = link_elem.text.strip()
                                url = link_elem.get_attribute('href')
                                
                                if title and url and len(title) > 2:
                                    # 공지사항 체크
                                    if not ('공지' in title or '[공지]' in title or title.startswith('공지')):
                                        articles.append({{
                                            'title': title,
                                            'url': url,
                                            'author': 'Unknown',
                                            'article_id': url.split('/')[-1].split('?')[0]
                                        }})
                            except:
                                continue
                        
                        if articles:
                            break
                            
                except:
                    continue
            
            logging.info(f"폴백 방식으로 {len(articles)}개 게시물 수집")
            return articles
            
        except Exception as e:
            logging.error(f"❌ 폴백 수집도 실패: {e}")
            return []
    
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
            
            # 노션 속성 (정확한 데이터베이스 구조에 맞춤)
            properties = {}
            
            # 1. 제목 - Title 필드
            title = article.get('title', '').strip() or "제목 없음"
            if len(title) > 100:
                title = title[:97] + "..."
            
            properties["제목"] = {
                "title": [{"text": {"content": title}}]
            }
            
            # 2. 작성자 - Text 필드
            author = article.get('author', 'Unknown').strip()
            properties["작성자"] = {
                "rich_text": [{"text": {"content": author}}]
            }
            
            # 3. 작성일 - Text 필드
            date_str = article.get('date', datetime.now().strftime('%Y-%m-%d'))
            properties["작성일"] = {
                "rich_text": [{"text": {"content": date_str}}]
            }
            
            # 4. URL - URL 필드
            if article.get('url'):
                properties["URL"] = {"url": article['url']}
            
            # 5. 내용 - Text 필드
            content = article.get('content', '').strip()
            if not content:
                content = "[내용 없음]"
            
            # 내용이 너무 길면 자르기 (노션 Rich Text 제한 고려)
            if len(content) > 2000:
                content = content[:1997] + "..."
            
            properties["내용"] = {
                "rich_text": [{"text": {"content": content}}]
            }
            
            # 6. 크롤링 일시 - 날짜 필드 (현재 시간)
            properties["크롤링 일시"] = {
                "date": {"start": datetime.now().isoformat()}
            }
            
            # 7. 카페명 - Select 필드
            cafe_name = article.get('cafe_name', 'Unknown')
            properties["카페명"] = {
                "select": {"name": cafe_name}
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
    
    # 카페 설정 - F-E 카페만 크롤링
    cafes = []
    
    # F-E 카페 설정 (제공된 정보 기반)
    cafes.append({
        'name': 'F-E 카페',
        'url': 'https://cafe.naver.com/f-e',
        'club_id': '18786605',
        'board_id': '105'
    })
    
    # 추가 카페는 환경변수가 명시적으로 설정된 경우에만 추가
    # 현재는 F-E 카페만 크롤링하므로 주석 처리
    # if os.getenv('CAFE1_URL') and os.getenv('CAFE1_CLUB_ID') and os.getenv('CAFE1_BOARD_ID'):
    #     cafes.append({
    #         'name': os.getenv('CAFE1_NAME', '카페1'),
    #         'url': os.getenv('CAFE1_URL'),
    #         'club_id': os.getenv('CAFE1_CLUB_ID'),
    #         'board_id': os.getenv('CAFE1_BOARD_ID')
    #     })
    
    logging.info(f"📋 설정된 카페 수: {len(cafes)}개")
    for i, cafe in enumerate(cafes, 1):
        logging.info(f"  {i}. {cafe['name']} (ID: {cafe['club_id']}, Board: {cafe['board_id']})")
    
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
