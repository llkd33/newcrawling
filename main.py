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
        게시물 내용 가져오기 - 혁신적인 JavaScript 실행 방식
        """
        try:
            logging.info(f"🚀 JavaScript 기반 내용 추출 시작: {url}")
            
            # 게시물 페이지로 이동
            self.driver.get(url)
            time.sleep(8)  # 충분한 로딩 시간
            
            # 로그인 체크
            if 'nid.naver.com' in self.driver.current_url:
                if self.login_naver():
                    self.driver.get(url)
                    time.sleep(8)
                else:
                    return "로그인 필요"
            
            # iframe 전환
            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it('cafe_main'))
                time.sleep(5)
                logging.info("✅ iframe 전환 성공")
            except:
                logging.warning("⚠️ iframe 전환 실패")
            
            # 페이지 완전 로딩 대기
            time.sleep(3)
            
            # 디버깅: 현재 페이지 정보 출력
            logging.info(f"🔍 현재 URL: {self.driver.current_url}")
            logging.info(f"🔍 페이지 제목: {self.driver.title}")
            
            # JavaScript로 직접 내용 추출
            content = self._extract_with_javascript()
            
            # iframe에서 나오기
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
            if content and len(content.strip()) > 10:
                # JavaScript 오류 메시지 체크
                if "We're sorry but web-pc doesn't work properly" in content:
                    logging.warning("⚠️ JavaScript 오류 메시지 감지, 대체 방법 시도")
                    content = self._extract_with_alternative_method()
                
                logging.info(f"✅ 내용 추출 성공: {len(content)}자")
                return content[:1500]
            else:
                return "내용 추출 실패"
                
        except Exception as e:
            logging.error(f"❌ JavaScript 추출 오류: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return f"추출 오류: {str(e)[:50]}"
    
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
            
            # 최대 10개 처리 (실제 운영용)
            max_articles = 10
            processed = 0
            
            # 게시물 처리 - 더 견고한 방식
            for i, article in enumerate(actual_articles[:20]):
                if processed >= max_articles:
                    logging.info(f"🎯 목표 달성: {processed}개 처리 완료")
                    break
                
                try:
                    logging.info(f"🔄 [{i+1}/{len(actual_articles[:20])}] 게시물 처리 중...")
                    
                    # 제목과 링크 추출
                    title = ""
                    link = ""
                    
                    # F-E 카페 전용 링크 추출 - JavaScript 사용
                    try:
                        js_extract_link = f"""
                        var articles = document.querySelectorAll('div, tr, li');
                        var result = null;
                        
                        for (var i = {i}; i < articles.length && i < {i+1}; i++) {{
                            var article = articles[i];
                            var links = article.querySelectorAll('a[href*="articles"], a[href*="articleid"]');
                            
                            for (var j = 0; j < links.length; j++) {{
                                var link = links[j];
                                var href = link.href;
                                var text = link.innerText || link.textContent;
                                
                                if (href && text && text.trim().length > 3 && 
                                    (href.includes('articles/') || href.includes('articleid='))) {{
                                    result = {{
                                        title: text.trim(),
                                        url: href
                                    }};
                                    break;
                                }}
                            }}
                            
                            if (result) break;
                        }}
                        
                        return result;
                        """
                        
                        js_result = self.driver.execute_script(js_extract_link)
                        
                        if js_result and js_result.get('title') and js_result.get('url'):
                            title = js_result['title']
                            link = js_result['url']
                            logging.info(f"✅ JavaScript 링크 추출 성공: {title[:30]}")
                        else:
                            # 폴백: 기존 방식
                            selectors = [
                                'a[href*="articles"]',
                                'a[href*="articleid"]', 
                                'td.td_article a',
                                'a.article',
                                'a'
                            ]
                            
                            for selector in selectors:
                                try:
                                    link_elem = article.find_element(By.CSS_SELECTOR, selector)
                                    title = link_elem.text.strip()
                                    link = link_elem.get_attribute('href')
                                    
                                    if title and link and ('articles/' in link or 'articleid=' in link):
                                        break
                                except:
                                    continue
                    except Exception as e:
                        logging.error(f"❌ JavaScript 링크 추출 오류: {e}")
                        continue
                    
                    # 기본 검증
                    if not title or not link:
                        logging.warning(f"⚠️ [{i+1}] 제목 또는 링크 없음, 건너뜀")
                        continue
                    
                    if '공지' in title or len(title) < 3:
                        logging.warning(f"⚠️ [{i+1}] 공지 또는 제목 부적절: {title[:20]}")
                        continue
                    
                    # URL 정리
                    if link.endswith('#'):
                        link = link[:-1]
                    if link.startswith('/'):
                        link = 'https://cafe.naver.com' + link
                    
                    logging.info(f"📝 [{i+1}] 처리 시작: {title[:30]}...")
                    logging.info(f"🔗 [{i+1}] URL: {link}")
                    
                    # 내용 추출
                    try:
                        content = self.get_article_content(link)
                        logging.info(f"📄 [{i+1}] 내용 길이: {len(content)}자")
                    except Exception as content_error:
                        logging.error(f"❌ [{i+1}] 내용 추출 오류: {content_error}")
                        content = f"내용 추출 중 오류 발생: {str(content_error)[:100]}"
                    
                    # 작성자 추출 - JavaScript 방식
                    author = self._extract_author_with_javascript(link)
                    if not author or author == "Unknown":
                        # 폴백: 게시물 목록에서 추출
                        try:
                            author_elem = article.find_element(By.CSS_SELECTOR, 'td.td_name, .name, .author, .nickname')
                            author = author_elem.text.strip() or "Unknown"
                        except:
                            author = "Unknown"
                    
                    # 작성일 추출
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    try:
                        date_elem = article.find_element(By.CSS_SELECTOR, 'td.td_date, .date, .time')
                        date_text = date_elem.text.strip()
                        if date_text:
                            date_str = date_text.replace('.', '-').rstrip('-')
                    except:
                        pass
                    
                    # 데이터 구성
                    data = {
                        'title': title,
                        'author': author,
                        'date': date_str,
                        'url': link,
                        'article_id': link.split('/')[-1].split('?')[0],
                        'content': content,
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
                    # 오류가 발생해도 다음 게시물 계속 처리
                    continue
            
            logging.info(f"🎯 게시물 처리 완료: {processed}개 성공")
            
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
