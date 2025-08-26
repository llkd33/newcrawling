#!/usr/bin/env python3
"""
Optimized Naver Cafe Crawler with Memory Management and Stability
Based on proven production techniques
"""

import os
import sys
import time
import pickle
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimizedCrawler:
    """Production-ready crawler with memory management and stability features"""
    
    def __init__(self):
        self.driver = None
        self.data = []
        self.processed_urls = set()
        self.checkpoint_file = "checkpoint.pkl"
        self.data_file = "crawl_data.pkl"
        
    def open_browser(self) -> webdriver.Chrome:
        """Open browser with optimized settings"""
        options = Options()
        
        if os.getenv('GITHUB_ACTIONS'):
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
        # Memory optimization
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-gpu-sandbox')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)  # Default wait time
        
        # Anti-detection script
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        logger.info("✅ Browser opened successfully")
        return driver
        
    def naver_login(self) -> bool:
        """Login to Naver with improved stability"""
        try:
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(3)
            
            # Check if already logged in
            if "naver.com" in self.driver.current_url and "login" not in self.driver.current_url:
                logger.info("✅ Already logged in")
                return True
                
            # Wait for login form
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id"))
            )
            
            # Type ID and PW slowly to avoid detection
            id_input = self.driver.find_element(By.ID, "id")
            for char in os.getenv('NAVER_ID'):
                id_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
                
            time.sleep(1)
            
            pw_input = self.driver.find_element(By.ID, "pw")
            for char in os.getenv('NAVER_PW'):
                pw_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
                
            time.sleep(1)
            
            # Click login
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            time.sleep(5)
            
            # Check login success
            if "naver.com" in self.driver.current_url:
                logger.info("✅ Login successful")
                return True
            else:
                logger.warning("⚠️ Login may have failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
            
    def build_board_url(self, club_id: str, board_id: str, page: int = 1) -> str:
        """Build board URL with userDisplay=50 for maximum efficiency"""
        base_url = "https://cafe.naver.com/ArticleList.nhn"
        params = f"?search.clubid={club_id}&search.menuid={board_id}&userDisplay=50&search.page={page}"
        return base_url + params
        
    def extract_post_in_new_tab(self, post_element) -> Dict:
        """Extract post data by opening in new tab"""
        data = {}
        
        try:
            # Open in new tab (Ctrl+Enter)
            post_element.send_keys(Keys.CONTROL + "\n")
            time.sleep(1)
            
            # Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(2)
            
            # Switch to iframe if exists
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.frame_to_be_available_and_switch_to_it("cafe_main")
                )
            except:
                pass
                
            # Extract data
            try:
                data['url'] = self.driver.current_url
                data['title'] = self.driver.find_element(By.CLASS_NAME, 'title_text').text
                data['author'] = self.driver.find_element(By.CLASS_NAME, 'nickname').text
                data['date'] = self.driver.find_element(By.CLASS_NAME, 'date').text
                
                # Try multiple content selectors
                content_selectors = [
                    '.se-main-container',
                    '.ContentRenderer',
                    '#postViewArea',
                    '.article_viewer',
                    '#content-area'
                ]
                
                content = ""
                for selector in content_selectors:
                    try:
                        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        content = elem.text
                        if content and len(content) > 20:
                            break
                    except:
                        continue
                        
                data['content'] = content[:2000] if content else "Content not found"
                
            except Exception as e:
                logger.debug(f"Data extraction error: {e}")
                
        except Exception as e:
            logger.error(f"Tab handling error: {e}")
            
        finally:
            # Close tab and return to main
            try:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                # Switch back to iframe in main window
                try:
                    self.driver.switch_to.frame("cafe_main")
                except:
                    pass
            except:
                pass
                
        return data
        
    def crawl_board_page(self, club_id: str, board_id: str, page: int) -> List[Dict]:
        """Crawl a single board page with 50 posts"""
        page_data = []
        
        try:
            # Navigate to board page
            url = self.build_board_url(club_id, board_id, page)
            self.driver.get(url)
            time.sleep(3)
            
            # Switch to iframe
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it("cafe_main")
                )
            except:
                logger.warning("No iframe found, continuing...")
                
            # Find all post links (up to 50)
            for i in range(1, 51):
                try:
                    # XPath for each post
                    xpath = f'//*[@id="main-area"]/div[4]/table/tbody/tr[{i}]/td[1]/div[2]/div/a[1]'
                    post_element = self.driver.find_element(By.XPATH, xpath)
                    
                    # Extract in new tab
                    post_data = self.extract_post_in_new_tab(post_element)
                    
                    if post_data and post_data.get('url'):
                        # Check if already processed
                        if post_data['url'] not in self.processed_urls:
                            page_data.append(post_data)
                            self.processed_urls.add(post_data['url'])
                            logger.info(f"✅ Extracted: {post_data.get('title', 'Unknown')[:30]}...")
                            
                    # Random delay between posts
                    time.sleep(random.uniform(0.5, 1.5))
                    
                except NoSuchElementException:
                    # No more posts on this page
                    break
                except Exception as e:
                    logger.debug(f"Post {i} extraction failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Page crawl failed: {e}")
            
        return page_data
        
    def save_checkpoint(self):
        """Save current progress"""
        checkpoint = {
            'data': self.data,
            'processed_urls': self.processed_urls,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
            
        logger.info(f"💾 Checkpoint saved: {len(self.data)} posts")
        
    def load_checkpoint(self) -> bool:
        """Load previous progress if exists"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                    
                self.data = checkpoint.get('data', [])
                self.processed_urls = checkpoint.get('processed_urls', set())
                
                logger.info(f"📥 Loaded checkpoint: {len(self.data)} posts")
                return True
            except Exception as e:
                logger.error(f"Checkpoint load failed: {e}")
                
        return False
        
    def restart_browser(self):
        """Restart browser to prevent memory leaks"""
        logger.info("🔄 Restarting browser to clear memory...")
        
        if self.driver:
            self.driver.quit()
            
        time.sleep(2)
        self.driver = self.open_browser()
        time.sleep(2)
        
        # Re-login
        self.naver_login()
        time.sleep(2)
        
        logger.info("✅ Browser restarted successfully")
        
    def crawl_cafe(self, cafe_config: Dict, max_pages: int = 100):
        """Main crawling function with memory management"""
        
        club_id = cafe_config['club_id']
        board_id = cafe_config['board_id']
        cafe_name = cafe_config['name']
        
        # Load checkpoint if exists
        self.load_checkpoint()
        
        # Initial browser setup
        if not self.driver:
            self.driver = self.open_browser()
            self.naver_login()
            
        pages_since_restart = 0
        
        for page in range(1, max_pages + 1):
            logger.info(f"📄 Crawling page {page}/{max_pages}")
            
            # Crawl page
            page_data = self.crawl_board_page(club_id, board_id, page)
            
            # Add cafe info to each post
            for post in page_data:
                post['cafe_name'] = cafe_name
                post['crawled_at'] = datetime.now().isoformat()
                
            self.data.extend(page_data)
            
            # Check if we should stop (old posts)
            if page_data:
                last_date = page_data[-1].get('date', '')
                if last_date and last_date[:4] <= '2020':
                    logger.info(f"⏹️ Reached 2020 posts, stopping...")
                    break
                    
            pages_since_restart += 1
            
            # Save checkpoint and restart browser every 2 pages (100 posts)
            if pages_since_restart >= 2:
                self.save_checkpoint()
                self.restart_browser()
                pages_since_restart = 0
                
            # Random delay between pages
            time.sleep(random.uniform(2, 4))
            
        # Final save
        self.save_checkpoint()
        
        # Save as pickle
        with open(self.data_file, 'wb') as f:
            pickle.dump(self.data, f)
            
        logger.info(f"✅ Crawling complete: {len(self.data)} posts")
        
        return self.data
        
    def save_to_notion(self):
        """Save crawled data to Notion"""
        if not os.getenv('NOTION_TOKEN'):
            logger.warning("No Notion token configured")
            return
            
        try:
            notion = Client(auth=os.getenv('NOTION_TOKEN'))
            database_id = os.getenv('NOTION_DATABASE_ID')
            
            success_count = 0
            
            for post in self.data:
                try:
                    notion.pages.create(
                        parent={'database_id': database_id},
                        properties={
                            os.getenv('NOTION_TITLE_FIELD', 'Title'): {
                                'title': [{'text': {'content': post.get('title', 'Untitled')}}]
                            }
                        },
                        children=[
                            {
                                'object': 'block',
                                'type': 'paragraph',
                                'paragraph': {
                                    'rich_text': [{'text': {'content': post.get('content', '')}}]
                                }
                            }
                        ]
                    )
                    
                    success_count += 1
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to save post: {e}")
                    
            logger.info(f"✅ Saved {success_count}/{len(self.data)} posts to Notion")
            
        except Exception as e:
            logger.error(f"Notion connection failed: {e}")
            
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            logger.info("✅ Browser closed")


def main():
    """Main execution"""
    crawler = OptimizedCrawler()
    
    try:
        # Cafe configuration
        cafes = []
        
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
            
        # Crawl each cafe
        for cafe in cafes:
            logger.info(f"\n🏠 Crawling {cafe['name']}...")
            crawler.crawl_cafe(cafe, max_pages=100)
            
        # Save to Notion
        crawler.save_to_notion()
        
        logger.info(f"\n🎉 All complete! Total: {len(crawler.data)} posts")
        
    except KeyboardInterrupt:
        logger.info("\n⏸️ Crawling interrupted by user")
        crawler.save_checkpoint()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        crawler.save_checkpoint()
        
    finally:
        crawler.cleanup()


if __name__ == '__main__':
    # Check if running locally (recommended)
    if os.getenv('GITHUB_ACTIONS'):
        logger.warning("⚠️ Running on GitHub Actions - may be blocked!")
        logger.info("Recommend running locally instead")
        
    main()