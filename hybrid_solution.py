#!/usr/bin/env python3
"""
Hybrid Solution: The Ultimate Naver Cafe Crawler
Combines multiple strategies to maximize success rate
"""

import os
import sys
import time
import json
import logging
import random
import asyncio
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Try to import Playwright (better anti-detection)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Import Selenium as fallback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HybridCrawler:
    """Ultimate crawler with multiple strategies"""
    
    def __init__(self):
        self.results = []
        self.session_cookies = None
        
    def crawl_all_strategies(self, cafe_config: Dict) -> List[Dict]:
        """Try all available strategies in order of likelihood to succeed"""
        
        strategies = [
            ("Mobile API Direct", self.strategy_mobile_api),
            ("Playwright Stealth", self.strategy_playwright),
            ("Selenium with Proxy", self.strategy_selenium_proxy),
            ("RSS Feed", self.strategy_rss),
            ("Cached Data", self.strategy_cached),
        ]
        
        for name, strategy in strategies:
            try:
                logger.info(f"🔄 Trying strategy: {name}")
                articles = strategy(cafe_config)
                
                if articles:
                    logger.info(f"✅ {name} succeeded: {len(articles)} articles")
                    return articles
                    
            except Exception as e:
                logger.warning(f"❌ {name} failed: {e}")
                continue
                
        logger.error("⚠️ All strategies failed")
        return []
        
    def strategy_mobile_api(self, cafe_config: Dict) -> List[Dict]:
        """Try to access mobile API directly"""
        articles = []
        
        # Mobile API endpoints
        endpoints = [
            f"https://m.cafe.naver.com/api/cafes/{cafe_config['club_id']}/menus/{cafe_config['board_id']}/articles",
            f"https://apis.naver.com/cafe-mobile/cafe-home/v3/cafes/{cafe_config['club_id']}/menus/{cafe_config['board_id']}/articles"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Referer': 'https://m.cafe.naver.com',
        }
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse response based on structure
                    article_list = data.get('articles', data.get('result', {}).get('articleList', []))
                    
                    for item in article_list[:10]:
                        articles.append({
                            'title': item.get('subject', item.get('title', 'Unknown')),
                            'article_id': str(item.get('articleId', item.get('id', ''))),
                            'url': f"https://m.cafe.naver.com/ca-fe/{cafe_config['club_id']}/{item.get('articleId', '')}",
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        
                    if articles:
                        return articles
                        
            except Exception as e:
                logger.debug(f"Mobile API endpoint failed: {e}")
                
        return articles
        
    def strategy_playwright(self, cafe_config: Dict) -> List[Dict]:
        """Use Playwright with stealth mode"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available")
            return []
            
        articles = []
        
        with sync_playwright() as p:
            # Use Firefox - often less detected than Chrome
            browser = p.firefox.launch(
                headless=os.getenv('GITHUB_ACTIONS') == 'true'
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR',
                timezone_id='Asia/Seoul',
            )
            
            # Add stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = context.new_page()
            
            try:
                # Try mobile version (less protected)
                url = f"https://m.cafe.naver.com/ca-fe/{cafe_config['club_id']}?menuId={cafe_config['board_id']}"
                page.goto(url, wait_until='networkidle')
                
                # Wait for content
                page.wait_for_timeout(3000)
                
                # Extract links
                links = page.query_selector_all('a[href*="/articles/"], a[href*="articleid="]')
                
                for link in links[:10]:
                    try:
                        href = link.get_attribute('href')
                        title = link.inner_text()
                        
                        if href and title:
                            articles.append({
                                'title': title,
                                'url': href if href.startswith('http') else f"https://m.cafe.naver.com{href}",
                                'date': datetime.now().strftime('%Y-%m-%d')
                            })
                    except:
                        continue
                        
            finally:
                browser.close()
                
        return articles
        
    def strategy_selenium_proxy(self, cafe_config: Dict) -> List[Dict]:
        """Use Selenium with proxy if available"""
        articles = []
        
        options = Options()
        if os.getenv('GITHUB_ACTIONS'):
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            
        # Check for proxy in environment
        if os.getenv('PROXY_URL'):
            options.add_argument(f'--proxy-server={os.getenv("PROXY_URL")}')
            logger.info(f"Using proxy: {os.getenv('PROXY_URL')}")
            
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        driver = webdriver.Chrome(options=options)
        
        try:
            # Mobile site is less protected
            url = f"https://m.cafe.naver.com/ca-fe/{cafe_config['club_id']}?menuId={cafe_config['board_id']}"
            driver.get(url)
            time.sleep(5)
            
            # Find article links
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/articles/"], a[href*="articleid="]')
            
            for link in links[:10]:
                try:
                    href = link.get_attribute('href')
                    title = link.text
                    
                    if href and title:
                        articles.append({
                            'title': title,
                            'url': href,
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                except:
                    continue
                    
        finally:
            driver.quit()
            
        return articles
        
    def strategy_rss(self, cafe_config: Dict) -> List[Dict]:
        """Try RSS feeds"""
        articles = []
        
        rss_url = f"https://cafe.naver.com/ArticleRss.nhn?clubid={cafe_config['club_id']}&menuid={cafe_config['board_id']}"
        
        try:
            response = requests.get(rss_url, timeout=10)
            if response.status_code == 200:
                # Parse RSS (simplified)
                import re
                
                # Find all items
                items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
                
                for item in items[:10]:
                    title_match = re.search(r'<title>(.*?)</title>', item)
                    link_match = re.search(r'<link>(.*?)</link>', item)
                    
                    if title_match and link_match:
                        articles.append({
                            'title': title_match.group(1),
                            'url': link_match.group(1),
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        
        except Exception as e:
            logger.debug(f"RSS strategy failed: {e}")
            
        return articles
        
    def strategy_cached(self, cafe_config: Dict) -> List[Dict]:
        """Load from cache file if available"""
        cache_file = f"cache_{cafe_config['club_id']}_{cafe_config['board_id']}.json"
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Check if cache is recent (within 24 hours)
                cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                if (datetime.now() - cache_time).days < 1:
                    logger.info(f"Using cached data from {cache_time}")
                    return data.get('articles', [])
                    
            except Exception as e:
                logger.debug(f"Cache read failed: {e}")
                
        return []
        
    def save_cache(self, cafe_config: Dict, articles: List[Dict]):
        """Save results to cache"""
        cache_file = f"cache_{cafe_config['club_id']}_{cafe_config['board_id']}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'articles': articles
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"✅ Cache saved: {cache_file}")
        except Exception as e:
            logger.error(f"Cache save failed: {e}")


def main():
    """Main execution"""
    crawler = HybridCrawler()
    
    # Load cafe config
    cafe_config = {
        'name': os.getenv('CAFE1_NAME', 'TestCafe'),
        'club_id': os.getenv('CAFE1_CLUB_ID', ''),
        'board_id': os.getenv('CAFE1_BOARD_ID', '')
    }
    
    if not cafe_config['club_id']:
        logger.error("No cafe configuration found")
        return
        
    # Try all strategies
    articles = crawler.crawl_all_strategies(cafe_config)
    
    if articles:
        # Save to cache
        crawler.save_cache(cafe_config, articles)
        
        # Save to Notion if configured
        if os.getenv('NOTION_TOKEN'):
            save_to_notion(articles)
            
        logger.info(f"✅ Success! Extracted {len(articles)} articles")
        
        # Print for verification
        for article in articles[:5]:
            print(f"📄 {article['title'][:50]}...")
            
    else:
        logger.error("❌ Failed to extract any articles")
        
        # If on GitHub Actions, suggest alternative
        if os.getenv('GITHUB_ACTIONS'):
            logger.info("\n💡 SUGGESTION: Run crawler locally and push results")
            logger.info("GitHub Actions IPs are likely blocked by Naver")
            logger.info("Consider:")
            logger.info("1. Using a proxy service (BrightData, Smartproxy)")
            logger.info("2. Running on a residential IP (home computer)")
            logger.info("3. Using a cloud service with residential IPs")
            

def save_to_notion(articles: List[Dict]):
    """Save to Notion database"""
    try:
        from notion_client import Client
        
        notion = Client(auth=os.getenv('NOTION_TOKEN'))
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        for article in articles:
            try:
                notion.pages.create(
                    parent={'database_id': database_id},
                    properties={
                        os.getenv('NOTION_TITLE_FIELD', 'Title'): {
                            'title': [{'text': {'content': article['title'][:100]}}]
                        }
                    }
                )
                logger.info(f"✅ Saved to Notion: {article['title'][:30]}...")
            except Exception as e:
                logger.error(f"Notion save failed: {e}")
                
    except Exception as e:
        logger.error(f"Notion connection failed: {e}")


if __name__ == '__main__':
    main()