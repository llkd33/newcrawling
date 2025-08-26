#!/usr/bin/env python3
"""
Session Manager for persistent session handling and cookie management
"""

import json
import os
import time
import logging
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class SessionManager:
    """Manages browser sessions and cookies for bot detection evasion"""
    
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = session_dir
        self.logger = logging.getLogger(__name__)
        self.current_session = None
        self.session_data = {
            'cookies': [],
            'local_storage': {},
            'session_storage': {},
            'user_agent': None,
            'created_at': None,
            'last_used': None,
            'request_count': 0,
            'blocked_count': 0
        }
        
        # Create session directory if not exists
        os.makedirs(session_dir, exist_ok=True)
        
    def save_session(self, driver, session_name: str = "default"):
        """Save current browser session"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_name}.json")
            
            # Get cookies
            cookies = driver.get_cookies()
            
            # Get local storage
            local_storage = driver.execute_script("""
                var items = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            """)
            
            # Get session storage
            session_storage = driver.execute_script("""
                var items = {};
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            """)
            
            # Get user agent
            user_agent = driver.execute_script("return navigator.userAgent;")
            
            # Update session data
            self.session_data.update({
                'cookies': cookies,
                'local_storage': local_storage,
                'session_storage': session_storage,
                'user_agent': user_agent,
                'last_used': datetime.now().isoformat()
            })
            
            if not self.session_data.get('created_at'):
                self.session_data['created_at'] = datetime.now().isoformat()
            
            # Save to file
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"✅ Session saved: {session_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save session: {e}")
            return False
            
    def load_session(self, driver, session_name: str = "default"):
        """Load saved browser session"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_name}.json")
            
            if not os.path.exists(session_file):
                self.logger.warning(f"⚠️ Session file not found: {session_name}")
                return False
                
            # Load session data
            with open(session_file, 'r', encoding='utf-8') as f:
                self.session_data = json.load(f)
                
            # Check session age
            if self.is_session_expired():
                self.logger.warning("⚠️ Session expired")
                return False
                
            # Navigate to domain first
            driver.get("https://naver.com")
            time.sleep(2)
            
            # Clear existing cookies
            driver.delete_all_cookies()
            
            # Add saved cookies
            for cookie in self.session_data.get('cookies', []):
                try:
                    # Adjust cookie domain if needed
                    if 'domain' in cookie:
                        cookie['domain'] = cookie['domain'].lstrip('.')
                    driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Cookie add failed: {e}")
                    
            # Set local storage
            local_storage = self.session_data.get('local_storage', {})
            for key, value in local_storage.items():
                try:
                    driver.execute_script(
                        "localStorage.setItem(arguments[0], arguments[1]);",
                        key, value
                    )
                except:
                    pass
                    
            # Set session storage
            session_storage = self.session_data.get('session_storage', {})
            for key, value in session_storage.items():
                try:
                    driver.execute_script(
                        "sessionStorage.setItem(arguments[0], arguments[1]);",
                        key, value
                    )
                except:
                    pass
                    
            # Update last used time
            self.session_data['last_used'] = datetime.now().isoformat()
            
            # Refresh to apply cookies
            driver.refresh()
            time.sleep(2)
            
            self.logger.info(f"✅ Session loaded: {session_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load session: {e}")
            return False
            
    def is_session_expired(self, max_age_hours: int = 24):
        """Check if session is too old"""
        try:
            last_used = self.session_data.get('last_used')
            if not last_used:
                return True
                
            last_used_dt = datetime.fromisoformat(last_used)
            age = datetime.now() - last_used_dt
            
            return age.total_seconds() > (max_age_hours * 3600)
            
        except:
            return True
            
    def rotate_session(self, driver, session_names: List[str]):
        """Rotate through multiple sessions"""
        for session_name in session_names:
            if self.load_session(driver, session_name):
                self.current_session = session_name
                return True
                
        self.logger.warning("⚠️ No valid sessions available")
        return False
        
    def increment_request_count(self):
        """Track request count for current session"""
        self.session_data['request_count'] += 1
        
    def increment_block_count(self):
        """Track blocking events"""
        self.session_data['blocked_count'] += 1
        
    def get_session_health(self):
        """Get health score of current session"""
        if not self.session_data:
            return 0
            
        request_count = self.session_data.get('request_count', 0)
        blocked_count = self.session_data.get('blocked_count', 0)
        
        if request_count == 0:
            return 100
            
        # Calculate block rate
        block_rate = (blocked_count / request_count) * 100
        
        # Health score (100 = perfect, 0 = completely blocked)
        health = max(0, 100 - (block_rate * 2))
        
        return health
        
    def should_rotate_session(self, threshold: int = 30):
        """Determine if session should be rotated"""
        health = self.get_session_health()
        
        # Also check request count
        request_count = self.session_data.get('request_count', 0)
        
        # Rotate if health is low or too many requests
        return health < threshold or request_count > 100


class RateLimiter:
    """Intelligent rate limiting to avoid detection"""
    
    def __init__(self):
        self.request_times = []
        self.burst_window = 60  # seconds
        self.max_burst = 10  # max requests per burst window
        self.min_interval = 2  # minimum seconds between requests
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Clean old request times
        self.request_times = [t for t in self.request_times if now - t < self.burst_window]
        
        # Check burst limit
        if len(self.request_times) >= self.max_burst:
            # Wait until oldest request exits window
            wait_time = self.burst_window - (now - self.request_times[0]) + 1
            logging.info(f"⏸️ Rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
            
        # Check minimum interval
        if self.request_times:
            last_request = self.request_times[-1]
            elapsed = now - last_request
            
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                time.sleep(wait_time)
                
        # Record this request
        self.request_times.append(time.time())
        
    def add_jitter(self, base_delay: float):
        """Add random jitter to delay"""
        import random
        jitter = random.uniform(-0.5, 0.5) * base_delay
        return max(0.1, base_delay + jitter)


class ProxyRotator:
    """Rotate through proxy servers if available"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.proxy_health = {proxy: 100 for proxy in self.proxies}
        
    def get_next_proxy(self) -> Optional[str]:
        """Get next healthy proxy"""
        if not self.proxies:
            return None
            
        # Find healthy proxies
        healthy_proxies = [p for p in self.proxies if self.proxy_health[p] > 50]
        
        if not healthy_proxies:
            # Reset all proxies if none are healthy
            for proxy in self.proxies:
                self.proxy_health[proxy] = 100
            healthy_proxies = self.proxies
            
        # Round-robin through healthy proxies
        if healthy_proxies:
            proxy = healthy_proxies[self.current_index % len(healthy_proxies)]
            self.current_index += 1
            return proxy
            
        return None
        
    def mark_proxy_success(self, proxy: str):
        """Mark proxy as successful"""
        if proxy in self.proxy_health:
            self.proxy_health[proxy] = min(100, self.proxy_health[proxy] + 5)
            
    def mark_proxy_failure(self, proxy: str):
        """Mark proxy as failed"""
        if proxy in self.proxy_health:
            self.proxy_health[proxy] = max(0, self.proxy_health[proxy] - 20)


class UserAgentRotator:
    """Rotate through different user agents"""
    
    def __init__(self):
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            
            # Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Gecko/20100101 Firefox/125.0',
            
            # Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
            
            # Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15'
        ]
        
        self.mobile_user_agents = [
            # iPhone
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
            
            # Android Chrome
            'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            
            # Samsung Browser
            'Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36'
        ]
        
        self.current_index = 0
        
    def get_random_desktop_agent(self) -> str:
        """Get random desktop user agent"""
        import random
        return random.choice(self.user_agents)
        
    def get_random_mobile_agent(self) -> str:
        """Get random mobile user agent"""
        import random
        return random.choice(self.mobile_user_agents)
        
    def get_next_agent(self, mobile: bool = False) -> str:
        """Get next user agent in rotation"""
        agents = self.mobile_user_agents if mobile else self.user_agents
        agent = agents[self.current_index % len(agents)]
        self.current_index += 1
        return agent