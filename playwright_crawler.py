#!/usr/bin/env python3
"""
Playwright-based crawler with better anti-detection
Playwright has better anti-detection than Selenium
"""

import os
import asyncio
import logging
from playwright.async_api import async_playwright
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaywrightCrawler:
    """Crawler using Playwright for better evasion"""
    
    async def crawl(self, cafe_config):
        """Main crawling function using Playwright"""
        async with async_playwright() as p:
            # Launch browser with stealth settings
            browser = await p.chromium.launch(
                headless=os.getenv('GITHUB_ACTIONS') == 'true',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            
            # Create context with anti-detection settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                # Extra headers
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )
            
            # Add stealth scripts to every page
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
            """)
            
            page = await context.new_page()
            
            try:
                # Login
                await self.login_with_playwright(page)
                
                # Build session gradually
                await self.build_session(page, cafe_config['club_id'])
                
                # Extract articles
                articles = await self.extract_articles(page, cafe_config)
                
                return articles
                
            except Exception as e:
                logger.error(f"Crawling failed: {e}")
                # Take screenshot for debugging
                await page.screenshot(path="error_screenshot.png")
                return []
                
            finally:
                await browser.close()
                
    async def login_with_playwright(self, page):
        """Login using Playwright with human-like behavior"""
        await page.goto('https://nid.naver.com/nidlogin.login')
        await page.wait_for_load_state('networkidle')
        
        # Type slowly like a human
        await page.fill('#id', os.getenv('NAVER_ID'), timeout=30000)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        await page.fill('#pw', os.getenv('NAVER_PW'), timeout=30000)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Click login
        await page.click('#log\\.login')
        
        # Wait for navigation
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(5)
        
        logger.info("✅ Login completed")
        
    async def build_session(self, page, club_id):
        """Build session gradually"""
        # Visit Naver main
        await page.goto('https://www.naver.com')
        await asyncio.sleep(random.uniform(2, 4))
        
        # Visit cafe main
        await page.goto('https://cafe.naver.com')
        await asyncio.sleep(random.uniform(2, 4))
        
        # Visit specific cafe
        await page.goto(f'https://cafe.naver.com/ca-fe/cafes/{club_id}')
        await asyncio.sleep(random.uniform(2, 4))
        
        logger.info("✅ Session built")
        
    async def extract_articles(self, page, cafe_config):
        """Extract articles using multiple strategies"""
        articles = []
        
        # Try mobile version first (usually less protected)
        mobile_url = f"https://m.cafe.naver.com/ca-fe/{cafe_config['club_id']}?menuId={cafe_config['board_id']}"
        
        await page.goto(mobile_url)
        await page.wait_for_load_state('networkidle')
        
        # Extract article links
        links = await page.query_selector_all('a[href*="/articles/"]')
        
        for link in links[:10]:
            try:
                href = await link.get_attribute('href')
                title = await link.inner_text()
                
                articles.append({
                    'title': title,
                    'url': href,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
            except:
                continue
                
        logger.info(f"✅ Extracted {len(articles)} articles")
        return articles


async def main():
    """Main function"""
    crawler = PlaywrightCrawler()
    
    cafe_config = {
        'name': os.getenv('CAFE1_NAME'),
        'club_id': os.getenv('CAFE1_CLUB_ID'),
        'board_id': os.getenv('CAFE1_BOARD_ID')
    }
    
    articles = await crawler.crawl(cafe_config)
    
    for article in articles:
        print(f"- {article['title']}")
        
    print(f"\nTotal: {len(articles)} articles")


if __name__ == '__main__':
    asyncio.run(main()