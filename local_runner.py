#!/usr/bin/env python3
"""
Local Runner - Run crawler on local machine with residential IP
Then sync results to GitHub/Notion
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Import the main crawler
from main import NaverCafeCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalRunner:
    """Run crawler locally and sync results"""
    
    def __init__(self):
        self.results_dir = Path("crawl_results")
        self.results_dir.mkdir(exist_ok=True)
        
    def run_crawler(self) -> List[Dict]:
        """Run the actual crawler"""
        logger.info("🚀 Starting local crawler...")
        
        # Use the original crawler which works locally
        crawler = NaverCafeCrawler()
        
        try:
            # Login
            if not crawler.login_naver():
                logger.error("Login failed")
                return []
                
            # Get cafe configs
            cafes = []
            if os.getenv('CAFE1_NAME'):
                cafes.append({
                    'name': os.getenv('CAFE1_NAME'),
                    'club_id': os.getenv('CAFE1_CLUB_ID'),
                    'board_id': os.getenv('CAFE1_BOARD_ID'),
                    'url': os.getenv('CAFE1_URL')
                })
                
            all_results = []
            
            for cafe in cafes:
                logger.info(f"📍 Crawling {cafe['name']}...")
                results = crawler.crawl_cafe(cafe)
                all_results.extend(results)
                
            return all_results
            
        finally:
            crawler.cleanup()
            
    def save_results(self, articles: List[Dict]) -> str:
        """Save results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.results_dir / f"crawl_{timestamp}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'count': len(articles),
            'articles': articles
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✅ Results saved to {filename}")
        return str(filename)
        
    def sync_to_github(self, filename: str):
        """Push results to GitHub"""
        try:
            # Add file
            subprocess.run(['git', 'add', filename], check=True)
            
            # Commit
            message = f"crawl: Add results from {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(['git', 'commit', '-m', message], check=True)
            
            # Push
            subprocess.run(['git', 'push'], check=True)
            
            logger.info("✅ Results pushed to GitHub")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git sync failed: {e}")
            return False
            
    def sync_to_notion_direct(self, articles: List[Dict]):
        """Directly sync to Notion without GitHub"""
        try:
            from notion_client import Client
            
            notion = Client(auth=os.getenv('NOTION_TOKEN'))
            database_id = os.getenv('NOTION_DATABASE_ID')
            
            success_count = 0
            
            for article in articles:
                try:
                    # Check if already exists (by URL)
                    existing = notion.databases.query(
                        database_id=database_id,
                        filter={
                            "property": "URL",
                            "url": {"equals": article['url']}
                        }
                    )
                    
                    if existing['results']:
                        logger.info(f"⏭️ Skipping duplicate: {article['title'][:30]}...")
                        continue
                        
                    # Create new page
                    notion.pages.create(
                        parent={'database_id': database_id},
                        properties={
                            os.getenv('NOTION_TITLE_FIELD', 'Title'): {
                                'title': [{'text': {'content': article['title']}}]
                            },
                            'URL': {'url': article['url']},
                            'Date': {'date': {'start': article['date']}},
                            'Cafe': {'select': {'name': article['cafe_name']}}
                        },
                        children=[
                            {
                                'object': 'block',
                                'type': 'paragraph',
                                'paragraph': {
                                    'rich_text': [{'text': {'content': article['content'][:2000]}}]
                                }
                            }
                        ]
                    )
                    
                    success_count += 1
                    logger.info(f"✅ Saved to Notion: {article['title'][:30]}...")
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Failed to save article: {e}")
                    
            logger.info(f"📊 Saved {success_count}/{len(articles)} articles to Notion")
            
        except Exception as e:
            logger.error(f"Notion sync failed: {e}")
            

def main():
    """Main execution"""
    runner = LocalRunner()
    
    # Check if running locally
    if os.getenv('GITHUB_ACTIONS'):
        logger.warning("⚠️ This script is designed to run locally, not on GitHub Actions")
        logger.info("GitHub Actions IPs are blocked by Naver")
        logger.info("Please run this script on your local machine instead")
        return
        
    # Run crawler
    articles = runner.run_crawler()
    
    if not articles:
        logger.warning("No articles extracted")
        return
        
    logger.info(f"✅ Extracted {len(articles)} articles")
    
    # Save results
    filename = runner.save_results(articles)
    
    # Sync options
    sync_method = os.getenv('SYNC_METHOD', 'notion').lower()
    
    if sync_method == 'github':
        # Push to GitHub, let Actions handle Notion
        runner.sync_to_github(filename)
        
    elif sync_method == 'notion':
        # Direct Notion sync (faster, no GitHub needed)
        runner.sync_to_notion_direct(articles)
        
    elif sync_method == 'both':
        # Both GitHub and Notion
        runner.sync_to_github(filename)
        runner.sync_to_notion_direct(articles)
        
    logger.info("🎉 Local crawl complete!")
    

if __name__ == '__main__':
    main()