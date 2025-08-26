#!/usr/bin/env python3
"""
Enhanced Naver Cafe Crawler with Advanced Bot Detection Evasion
"""

import os
import sys
import time
import logging
import random
import re
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import urllib.parse as urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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

class EnhancedCafeCrawler:
    """Enhanced crawler with advanced bot detection evasion"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.session_cookies = []
        self.request_count = 0
        self.last_request_time = 0
        self.setup_driver()
        
    def setup_driver(self):
        """Setup Chrome with advanced anti-detection"""
        options = Options()
        
        # GitHub Actions detection
        is_github = os.getenv('GITHUB_ACTIONS')
        
        if is_github:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        
        # Advanced anti-detection settings
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--lang=ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7')
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add browser preferences
        prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0,
            'profile.managed_default_content_settings.images': 1
        }
        options.add_experimental_option('prefs', prefs)
        
        # Realistic user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Performance settings
        options.add_argument('--disable-gpu-sandbox')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Initialize driver
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Execute anti-detection scripts
        self._inject_anti_detection_scripts()
        
        logging.info("✅ Enhanced driver initialized with anti-detection")
        
    def _inject_anti_detection_scripts(self):
        """Inject scripts to evade bot detection"""
        
        # Remove webdriver property
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin'}
                    ]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Chrome runtime
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
                
                // Mock WebGL
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
                
                // Mock screen properties
                Object.defineProperty(screen, 'availWidth', {get: () => 1920});
                Object.defineProperty(screen, 'availHeight', {get: () => 1040});
                
                // Console overrides
                const originalConsole = window.console;
                window.console.debug = () => {};
                window.console.info = () => {};
                
                // Notification permission
                Object.defineProperty(Notification, 'permission', {
                    get: () => 'default'
                });
            '''
        })
        
    def human_like_delay(self, min_sec=0.5, max_sec=2.0):
        """Human-like random delay"""
        delay = random.uniform(min_sec, max_sec) + random.gauss(0, 0.2)
        time.sleep(max(0.3, delay))
        
    def random_mouse_movement(self):
        """Simulate random mouse movements"""
        try:
            actions = ActionChains(self.driver)
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y)
                actions.perform()
                time.sleep(random.uniform(0.1, 0.3))
        except:
            pass
            
    def random_scroll(self):
        """Random page scrolling"""
        try:
            scroll_amount = random.randint(100, 500)
            direction = random.choice(['down', 'up'])
            
            if direction == 'down':
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            else:
                self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                
            self.human_like_delay(0.3, 0.8)
        except:
            pass
            
    def smart_wait(self, element_locator, timeout=20):
        """Smart wait with human-like behavior"""
        try:
            # Random small movements while waiting
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(element_locator)
            )
            
            # Random actions
            if random.random() > 0.7:
                self.random_mouse_movement()
            if random.random() > 0.8:
                self.random_scroll()
                
            return element
        except TimeoutException:
            return None
            
    def login_with_delays(self):
        """Enhanced login with human-like behavior"""
        try:
            logging.info("🔐 Starting enhanced login process...")
            
            # Navigate to login page
            self.driver.get('https://nid.naver.com/nidlogin.login')
            self.human_like_delay(3, 5)
            
            # Wait for page load
            self.smart_wait((By.ID, 'id'), 10)
            
            # Type ID with delays between keystrokes
            id_input = self.driver.find_element(By.ID, 'id')
            id_input.click()
            self.human_like_delay(0.5, 1)
            
            for char in os.getenv('NAVER_ID'):
                id_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            self.human_like_delay(0.5, 1)
            
            # Type password
            pw_input = self.driver.find_element(By.ID, 'pw')
            pw_input.click()
            self.human_like_delay(0.5, 1)
            
            for char in os.getenv('NAVER_PW'):
                pw_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            self.human_like_delay(1, 2)
            
            # Click login with random position
            login_btn = self.driver.find_element(By.ID, 'log.login')
            ActionChains(self.driver).move_to_element(login_btn).click().perform()
            
            # Wait for login completion
            self.human_like_delay(5, 8)
            
            # Save cookies
            self.session_cookies = self.driver.get_cookies()
            
            logging.info("✅ Login successful with human-like behavior")
            return True
            
        except Exception as e:
            logging.error(f"❌ Login failed: {e}")
            return False
            
    def navigate_with_referrer(self, url: str):
        """Navigate maintaining referrer chain"""
        try:
            # Use JavaScript navigation to preserve referrer
            self.driver.execute_script("""
                var link = document.createElement('a');
                link.href = arguments[0];
                link.rel = 'noreferrer noopener';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            """, url)
            
            self.human_like_delay(2, 4)
            
            # Wait for page load
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
        except Exception as e:
            logging.warning(f"Navigation with referrer failed, using fallback: {e}")
            self.driver.get(url)
            
    def detect_and_bypass_captcha(self):
        """Detect and handle CAPTCHA challenges"""
        try:
            # Check for common CAPTCHA indicators
            captcha_indicators = [
                "captcha", "recaptcha", "challenge", "verify", "robot",
                "자동입력방지", "보안문자", "인증"
            ]
            
            page_source = self.driver.page_source.lower()
            
            for indicator in captcha_indicators:
                if indicator in page_source:
                    logging.warning(f"⚠️ CAPTCHA detected: {indicator}")
                    
                    # Wait for manual resolution
                    logging.info("⏸️ Waiting for manual CAPTCHA resolution...")
                    time.sleep(30)
                    
                    return True
                    
            return False
            
        except Exception as e:
            logging.error(f"CAPTCHA detection error: {e}")
            return False
            
    def build_session_gradually(self, club_id: str):
        """Build session gradually to avoid detection"""
        try:
            logging.info("🔧 Building session gradually...")
            
            # Visit Naver main page
            self.driver.get("https://www.naver.com")
            self.human_like_delay(2, 4)
            self.random_scroll()
            
            # Visit cafe main page
            self.driver.get("https://cafe.naver.com")
            self.human_like_delay(2, 4)
            self.random_scroll()
            
            # Visit specific cafe home
            cafe_home = f"https://cafe.naver.com/ca-fe/cafes/{club_id}"
            self.navigate_with_referrer(cafe_home)
            self.human_like_delay(2, 4)
            
            # Simulate reading behavior
            self.random_scroll()
            self.random_mouse_movement()
            
            logging.info("✅ Session built successfully")
            
        except Exception as e:
            logging.warning(f"Session building warning: {e}")
            
    def extract_articles_safely(self, club_id: str, board_id: str, max_articles: int = 10):
        """Extract articles with safety measures"""
        results = []
        
        try:
            # Build session first
            self.build_session_gradually(club_id)
            
            # Try different approaches
            approaches = [
                self._extract_via_api,
                self._extract_via_mobile,
                self._extract_via_classic_careful,
                self._extract_via_spa
            ]
            
            for approach in approaches:
                logging.info(f"🔄 Trying approach: {approach.__name__}")
                
                try:
                    articles = approach(club_id, board_id, max_articles)
                    
                    if articles:
                        logging.info(f"✅ Success with {approach.__name__}: {len(articles)} articles")
                        return articles
                        
                except Exception as e:
                    logging.warning(f"Approach {approach.__name__} failed: {e}")
                    self.human_like_delay(3, 5)
                    
            logging.warning("⚠️ All approaches failed")
            return []
            
        except Exception as e:
            logging.error(f"❌ Safe extraction failed: {e}")
            return []
            
    def _extract_via_api(self, club_id: str, board_id: str, max_articles: int):
        """Try to extract via API-like endpoints"""
        articles = []
        
        # Build API-like URL
        api_url = f"https://apis.naver.com/cafe-web/cafe-articleapi/v2/cafes/{club_id}/articles"
        
        try:
            # Add required headers
            self.driver.execute_script("""
                fetch(arguments[0], {
                    headers: {
                        'Accept': 'application/json',
                        'Referer': 'https://cafe.naver.com'
                    }
                }).then(r => r.json()).then(data => window.apiData = data);
            """, api_url)
            
            self.human_like_delay(2, 3)
            
            # Get API data
            data = self.driver.execute_script("return window.apiData;")
            
            if data and 'result' in data:
                for item in data['result'].get('articleList', [])[:max_articles]:
                    articles.append({
                        'title': item.get('subject', ''),
                        'article_id': str(item.get('articleId', '')),
                        'author': item.get('nickname', 'Unknown'),
                        'date': item.get('writeDateTimestamp', ''),
                        'url': f"https://cafe.naver.com/ca-fe/cafes/{club_id}/articles/{item.get('articleId')}"
                    })
                    
        except Exception as e:
            logging.debug(f"API extraction failed: {e}")
            
        return articles
        
    def _extract_via_mobile(self, club_id: str, board_id: str, max_articles: int):
        """Extract via mobile version"""
        articles = []
        
        try:
            # Mobile URL
            mobile_url = f"https://m.cafe.naver.com/ca-fe/{club_id}?menuId={board_id}"
            
            # Set mobile user agent
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
            })
            
            self.driver.get(mobile_url)
            self.human_like_delay(3, 5)
            
            # Extract article links
            article_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/ca-fe/'][href*='/articles/']")
            
            for elem in article_elements[:max_articles]:
                try:
                    href = elem.get_attribute('href')
                    title = elem.text.strip()
                    
                    # Extract article ID from URL
                    match = re.search(r'/articles/(\d+)', href)
                    if match:
                        article_id = match.group(1)
                        
                        articles.append({
                            'title': title or f"Article {article_id}",
                            'article_id': article_id,
                            'url': href,
                            'author': 'Unknown',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        
                except Exception as e:
                    logging.debug(f"Mobile article extraction error: {e}")
                    
            # Reset user agent
            self.setup_driver()
            
        except Exception as e:
            logging.warning(f"Mobile extraction failed: {e}")
            
        return articles
        
    def _extract_via_classic_careful(self, club_id: str, board_id: str, max_articles: int):
        """Carefully extract via classic endpoints"""
        articles = []
        
        try:
            # Use ArticleList.nhn with careful timing
            list_url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={board_id}&userDisplay=50"
            
            # Navigate with delay
            self.navigate_with_referrer(list_url)
            self.human_like_delay(4, 6)
            
            # Check for blocking
            if self._is_blocked():
                logging.warning("⚠️ Classic endpoint blocked")
                return []
                
            # Try iframe switch
            self._switch_to_iframe_safely()
            
            # Extract article IDs
            id_pattern = re.compile(r'articleid=(\d+)')
            page_source = self.driver.page_source
            
            article_ids = list(set(id_pattern.findall(page_source)))[:max_articles]
            
            for aid in article_ids:
                articles.append({
                    'article_id': aid,
                    'title': f"Article {aid}",
                    'url': f"https://cafe.naver.com/ArticleRead.nhn?clubid={club_id}&articleid={aid}",
                    'author': 'Unknown',
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
                
        except Exception as e:
            logging.warning(f"Classic extraction failed: {e}")
            
        finally:
            try:
                self.driver.switch_to.default_content()
            except:
                pass
                
        return articles
        
    def _extract_via_spa(self, club_id: str, board_id: str, max_articles: int):
        """Extract via SPA interface"""
        articles = []
        
        try:
            # SPA URL format
            spa_url = f"https://cafe.naver.com/ca-fe/cafes/{club_id}/menus/{board_id}/articles"
            
            self.driver.get(spa_url)
            self.human_like_delay(4, 6)
            
            # Wait for React/Next.js to render
            self.smart_wait((By.CSS_SELECTOR, "a[href*='/articles/']"), 15)
            
            # Extract articles
            article_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/articles/']")
            
            for link in article_links[:max_articles]:
                try:
                    href = link.get_attribute('href')
                    title = link.text.strip()
                    
                    # Extract article ID
                    match = re.search(r'/articles/(\d+)', href)
                    if match:
                        article_id = match.group(1)
                        
                        articles.append({
                            'title': title or f"Article {article_id}",
                            'article_id': article_id,
                            'url': href,
                            'author': 'Unknown',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        
                except Exception as e:
                    logging.debug(f"SPA article extraction error: {e}")
                    
        except Exception as e:
            logging.warning(f"SPA extraction failed: {e}")
            
        return articles
        
    def _is_blocked(self):
        """Check if page shows blocking signs"""
        try:
            blocking_signs = [
                "차단", "blocked", "접근", "제한", "오류", 
                "error", "보안", "security", "captcha", "인증"
            ]
            
            page_text = self.driver.page_source.lower()
            title = self.driver.title.lower()
            
            for sign in blocking_signs:
                if sign in page_text or sign in title:
                    return True
                    
            return False
            
        except:
            return False
            
    def _switch_to_iframe_safely(self):
        """Safely switch to iframe if exists"""
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            
            for iframe in iframes:
                iframe_id = iframe.get_attribute('id')
                iframe_name = iframe.get_attribute('name')
                
                if 'cafe_main' in str(iframe_id) or 'cafe_main' in str(iframe_name):
                    self.driver.switch_to.frame(iframe)
                    logging.info("✅ Switched to cafe_main iframe")
                    return True
                    
            return False
            
        except Exception as e:
            logging.debug(f"Iframe switch failed: {e}")
            return False
            
    def extract_content_safely(self, url: str):
        """Safely extract article content"""
        try:
            # Navigate to article
            self.navigate_with_referrer(url)
            self.human_like_delay(3, 5)
            
            # Check for blocking
            if self._is_blocked():
                return "Content blocked"
                
            # Try iframe
            self._switch_to_iframe_safely()
            
            # Multiple content selectors
            content_selectors = [
                '.se-main-container',
                '.ContentRenderer',
                '#postViewArea',
                '.article_viewer',
                '#content-area',
                '.post-content'
            ]
            
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content = elements[0].text.strip()
                        if content and len(content) > 20:
                            return content[:1500]
                except:
                    continue
                    
            # Fallback to body text
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            if body_text:
                return body_text[:1500]
                
            return "Content extraction failed"
            
        except Exception as e:
            logging.error(f"Content extraction error: {e}")
            return f"Error: {str(e)[:100]}"
        finally:
            try:
                self.driver.switch_to.default_content()
            except:
                pass
                
    def crawl_cafe(self, cafe_config: Dict):
        """Main crawling function with all safety measures"""
        results = []
        
        try:
            club_id = cafe_config['club_id']
            board_id = cafe_config['board_id']
            cafe_name = cafe_config['name']
            
            logging.info(f"🚀 Starting safe crawl for {cafe_name}")
            
            # Login first
            if not self.login_with_delays():
                logging.error("Login failed, aborting")
                return []
                
            # Extract article list
            articles = self.extract_articles_safely(club_id, board_id)
            
            if not articles:
                logging.warning("No articles extracted")
                return []
                
            # Extract content for each article
            for i, article in enumerate(articles, 1):
                logging.info(f"📄 Processing article {i}/{len(articles)}: {article.get('title', 'Unknown')[:30]}...")
                
                # Rate limiting
                self.human_like_delay(3, 6)
                
                # Extract content
                content = self.extract_content_safely(article['url'])
                
                article['content'] = content
                article['cafe_name'] = cafe_name
                article['crawled_at'] = datetime.now().isoformat()
                
                results.append(article)
                
                # Random behavior between articles
                if random.random() > 0.7:
                    self.random_scroll()
                if random.random() > 0.8:
                    self.random_mouse_movement()
                    
            logging.info(f"✅ Crawled {len(results)} articles from {cafe_name}")
            
        except Exception as e:
            logging.error(f"❌ Crawling failed: {e}")
            
        return results
        
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
                logging.info("✅ Driver closed")
        except:
            pass


def main():
    """Main execution function"""
    
    # Initialize
    crawler = EnhancedCafeCrawler()
    
    try:
        # Load cafe configurations
        cafes = []
        
        # Add configured cafes
        if os.getenv('CAFE1_NAME'):
            cafes.append({
                'name': os.getenv('CAFE1_NAME'),
                'club_id': os.getenv('CAFE1_CLUB_ID'),
                'board_id': os.getenv('CAFE1_BOARD_ID')
            })
            
        if os.getenv('CAFE2_NAME'):
            cafes.append({
                'name': os.getenv('CAFE2_NAME'),
                'club_id': os.getenv('CAFE2_CLUB_ID'),
                'board_id': os.getenv('CAFE2_BOARD_ID')
            })
            
        logging.info(f"📋 Configured cafes: {len(cafes)}")
        
        all_results = []
        
        # Crawl each cafe
        for cafe in cafes:
            logging.info(f"\n📍 Crawling {cafe['name']}...")
            results = crawler.crawl_cafe(cafe)
            all_results.extend(results)
            
            # Delay between cafes
            if len(cafes) > 1:
                crawler.human_like_delay(10, 15)
                
        # Save to Notion if configured
        if all_results and os.getenv('NOTION_TOKEN'):
            save_to_notion(all_results)
            
        logging.info(f"\n🎉 Complete! Total articles: {len(all_results)}")
        
    except Exception as e:
        logging.error(f"❌ Main execution failed: {e}")
        
    finally:
        crawler.cleanup()
        

def save_to_notion(articles: List[Dict]):
    """Save articles to Notion database"""
    try:
        notion = Client(auth=os.getenv('NOTION_TOKEN'))
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        for article in articles:
            try:
                # Create page in Notion
                notion.pages.create(
                    parent={'database_id': database_id},
                    properties={
                        os.getenv('NOTION_TITLE_FIELD', 'Title'): {
                            'title': [{'text': {'content': article.get('title', 'Untitled')[:100]}}]
                        }
                    },
                    children=[
                        {
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {
                                'rich_text': [{'type': 'text', 'text': {'content': article.get('content', '')[:2000]}}]
                            }
                        }
                    ]
                )
                
                logging.info(f"✅ Saved to Notion: {article.get('title', 'Untitled')[:50]}...")
                
            except Exception as e:
                logging.error(f"Failed to save article to Notion: {e}")
                
    except Exception as e:
        logging.error(f"Notion save failed: {e}")


if __name__ == '__main__':
    main()