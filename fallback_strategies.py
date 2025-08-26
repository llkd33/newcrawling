#!/usr/bin/env python3
"""
Fallback strategies for when main crawling methods fail
"""

import logging
import time
import random
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


class FallbackStrategies:
    """Collection of fallback strategies for resilient crawling"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        
    def strategy_direct_api(self, club_id: str, board_id: str) -> List[Dict]:
        """Try direct API calls using browser's fetch"""
        articles = []
        
        try:
            # Try multiple API endpoints
            api_endpoints = [
                f"https://apis.naver.com/cafe-web/cafe-articleapi/v2/cafes/{club_id}/articles",
                f"https://apis.naver.com/cafe-web/cafe2/ArticleList.json?search.clubid={club_id}&search.menuid={board_id}",
                f"https://cafe.naver.com/api/cafes/{club_id}/menus/{board_id}/articles"
            ]
            
            for endpoint in api_endpoints:
                try:
                    # Execute fetch in browser context
                    result = self.driver.execute_script("""
                        return fetch(arguments[0], {
                            credentials: 'include',
                            headers: {
                                'Accept': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        })
                        .then(r => r.json())
                        .catch(e => null);
                    """, endpoint)
                    
                    if result:
                        self.logger.info(f"✅ API endpoint successful: {endpoint}")
                        articles = self._parse_api_response(result)
                        if articles:
                            break
                            
                except Exception as e:
                    self.logger.debug(f"API endpoint failed: {endpoint} - {e}")
                    
        except Exception as e:
            self.logger.error(f"Direct API strategy failed: {e}")
            
        return articles
        
    def strategy_rss_feed(self, club_id: str, board_id: str) -> List[Dict]:
        """Try RSS feed if available"""
        articles = []
        
        try:
            # Naver Cafe RSS format
            rss_urls = [
                f"https://cafe.naver.com/ArticleRss.nhn?clubid={club_id}&menuid={board_id}",
                f"https://rss.blog.naver.com/{club_id}.xml"
            ]
            
            for rss_url in rss_urls:
                try:
                    self.driver.get(rss_url)
                    time.sleep(2)
                    
                    # Parse RSS
                    items = self.driver.find_elements(By.TAG_NAME, "item")
                    
                    for item in items[:10]:
                        try:
                            title = item.find_element(By.TAG_NAME, "title").text
                            link = item.find_element(By.TAG_NAME, "link").text
                            
                            # Extract article ID from link
                            article_id = re.search(r'articleid=(\d+)', link)
                            if article_id:
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'article_id': article_id.group(1)
                                })
                                
                        except:
                            continue
                            
                    if articles:
                        self.logger.info(f"✅ RSS feed successful: {len(articles)} articles")
                        break
                        
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"RSS strategy failed: {e}")
            
        return articles
        
    def strategy_search_crawl(self, club_id: str, keywords: List[str]) -> List[Dict]:
        """Use search functionality to find articles"""
        articles = []
        
        try:
            for keyword in keywords:
                search_url = f"https://cafe.naver.com/ArticleSearch.nhn?search.clubid={club_id}&search.query={keyword}"
                
                self.driver.get(search_url)
                time.sleep(random.uniform(2, 4))
                
                # Try to switch to iframe
                try:
                    iframe = self.driver.find_element(By.ID, "cafe_main")
                    self.driver.switch_to.frame(iframe)
                except:
                    pass
                    
                # Find search results
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='articleid=']")
                
                for link in links[:5]:  # Limit per search
                    try:
                        href = link.get_attribute('href')
                        title = link.text
                        
                        article_id = re.search(r'articleid=(\d+)', href)
                        if article_id:
                            articles.append({
                                'title': title or f"Article {article_id.group(1)}",
                                'url': href,
                                'article_id': article_id.group(1)
                            })
                            
                    except:
                        continue
                        
                # Switch back from iframe
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                    
                if len(articles) >= 10:
                    break
                    
        except Exception as e:
            self.logger.error(f"Search strategy failed: {e}")
            
        return articles
        
    def strategy_incremental_crawl(self, club_id: str, board_id: str, start_id: int = None) -> List[Dict]:
        """Try incremental article IDs"""
        articles = []
        
        try:
            # Get latest article ID if not provided
            if not start_id:
                list_url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={board_id}"
                self.driver.get(list_url)
                time.sleep(3)
                
                # Find highest article ID
                page_source = self.driver.page_source
                article_ids = re.findall(r'articleid=(\d+)', page_source)
                
                if article_ids:
                    start_id = max(int(aid) for aid in article_ids)
                else:
                    start_id = 1000  # Fallback start
                    
            # Try recent article IDs
            for i in range(20):
                article_id = start_id - i
                
                if article_id <= 0:
                    break
                    
                article_url = f"https://cafe.naver.com/ArticleRead.nhn?clubid={club_id}&articleid={article_id}"
                
                # Quick check if article exists
                self.driver.get(article_url)
                time.sleep(1)
                
                # Check if article loaded successfully
                if "오류" not in self.driver.title and "error" not in self.driver.page_source.lower():
                    articles.append({
                        'title': f"Article {article_id}",
                        'url': article_url,
                        'article_id': str(article_id)
                    })
                    
                if len(articles) >= 10:
                    break
                    
        except Exception as e:
            self.logger.error(f"Incremental strategy failed: {e}")
            
        return articles
        
    def strategy_sitemap_crawl(self, club_id: str) -> List[Dict]:
        """Try sitemap if available"""
        articles = []
        
        try:
            sitemap_urls = [
                f"https://cafe.naver.com/sitemap.xml",
                f"https://cafe.naver.com/{club_id}/sitemap.xml"
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    self.driver.get(sitemap_url)
                    time.sleep(2)
                    
                    # Find URLs in sitemap
                    urls = self.driver.find_elements(By.TAG_NAME, "loc")
                    
                    for url_elem in urls:
                        url = url_elem.text
                        
                        if f"clubid={club_id}" in url or f"/cafes/{club_id}" in url:
                            article_id = re.search(r'articleid=(\d+)|/articles/(\d+)', url)
                            
                            if article_id:
                                aid = article_id.group(1) or article_id.group(2)
                                articles.append({
                                    'title': f"Article {aid}",
                                    'url': url,
                                    'article_id': aid
                                })
                                
                    if articles:
                        self.logger.info(f"✅ Sitemap successful: {len(articles)} articles")
                        break
                        
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Sitemap strategy failed: {e}")
            
        return articles[:10]  # Limit results
        
    def strategy_javascript_extraction(self, club_id: str, board_id: str) -> List[Dict]:
        """Extract data from JavaScript variables in page"""
        articles = []
        
        try:
            list_url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={board_id}"
            self.driver.get(list_url)
            time.sleep(3)
            
            # Try to extract from JavaScript objects
            js_extract = """
                var articles = [];
                
                // Try window variables
                if (window.articleList) {
                    articles = window.articleList;
                } else if (window._articleList) {
                    articles = window._articleList;
                } else if (window.cafeArticles) {
                    articles = window.cafeArticles;
                }
                
                // Try to find in script tags
                if (articles.length === 0) {
                    var scripts = document.getElementsByTagName('script');
                    for (var i = 0; i < scripts.length; i++) {
                        var content = scripts[i].innerHTML;
                        
                        // Look for article data patterns
                        var matches = content.match(/"articleid":\s*"?(\d+)"?/g);
                        if (matches) {
                            matches.forEach(function(match) {
                                var id = match.match(/\d+/);
                                if (id) {
                                    articles.push({articleId: id[0]});
                                }
                            });
                        }
                    }
                }
                
                return articles;
            """
            
            result = self.driver.execute_script(js_extract)
            
            if result:
                for item in result[:10]:
                    article_id = item.get('articleId') or item.get('articleid')
                    if article_id:
                        articles.append({
                            'title': item.get('subject', f"Article {article_id}"),
                            'article_id': str(article_id),
                            'url': f"https://cafe.naver.com/ArticleRead.nhn?clubid={club_id}&articleid={article_id}"
                        })
                        
        except Exception as e:
            self.logger.error(f"JavaScript extraction failed: {e}")
            
        return articles
        
    def _parse_api_response(self, response: Dict) -> List[Dict]:
        """Parse various API response formats"""
        articles = []
        
        try:
            # Try different response structures
            article_list = None
            
            if 'result' in response:
                article_list = response['result'].get('articleList', [])
            elif 'articles' in response:
                article_list = response['articles']
            elif 'data' in response:
                article_list = response['data'].get('articles', [])
            elif isinstance(response, list):
                article_list = response
                
            if article_list:
                for item in article_list[:10]:
                    article_id = item.get('articleId') or item.get('articleid') or item.get('id')
                    
                    if article_id:
                        articles.append({
                            'title': item.get('subject') or item.get('title', f"Article {article_id}"),
                            'article_id': str(article_id),
                            'author': item.get('nickname') or item.get('author', 'Unknown'),
                            'date': item.get('writeDate') or item.get('date', ''),
                            'url': item.get('url', '')
                        })
                        
        except Exception as e:
            self.logger.debug(f"API response parsing failed: {e}")
            
        return articles
        
    def execute_all_strategies(self, club_id: str, board_id: str) -> List[Dict]:
        """Execute all strategies and combine results"""
        all_articles = []
        seen_ids = set()
        
        strategies = [
            ('Direct API', lambda: self.strategy_direct_api(club_id, board_id)),
            ('RSS Feed', lambda: self.strategy_rss_feed(club_id, board_id)),
            ('JavaScript', lambda: self.strategy_javascript_extraction(club_id, board_id)),
            ('Search', lambda: self.strategy_search_crawl(club_id, ['공지', '안내', '이벤트'])),
            ('Incremental', lambda: self.strategy_incremental_crawl(club_id, board_id)),
            ('Sitemap', lambda: self.strategy_sitemap_crawl(club_id))
        ]
        
        for name, strategy in strategies:
            try:
                self.logger.info(f"🔄 Trying fallback strategy: {name}")
                
                articles = strategy()
                
                # Deduplicate
                for article in articles:
                    aid = article.get('article_id')
                    if aid and aid not in seen_ids:
                        seen_ids.add(aid)
                        all_articles.append(article)
                        
                if articles:
                    self.logger.info(f"✅ {name} strategy found {len(articles)} articles")
                    
                # Stop if we have enough articles
                if len(all_articles) >= 10:
                    break
                    
                # Delay between strategies
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                self.logger.warning(f"Strategy {name} failed: {e}")
                
        self.logger.info(f"📊 Total unique articles from all strategies: {len(all_articles)}")
        
        return all_articles[:20]  # Return max 20 articles