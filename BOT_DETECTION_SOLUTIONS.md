# Bot Detection Solutions for Naver Cafe Crawler

## Problem Analysis

Your GitHub Actions crawler is being blocked by Naver's WAF (Web Application Firewall) because:
1. **Immediate detection** when accessing classic endpoints (`ArticleList.nhn`)
2. **Pattern recognition** from automated behavior
3. **Missing session context** and referrer chain
4. **Insufficient randomization** in request timing

## Solutions Implemented

### 1. Enhanced Anti-Detection Measures (`enhanced_main.py`)

#### Key Features:
- **Advanced Chrome Options**: Disables automation flags and detection vectors
- **JavaScript Injection**: Removes `navigator.webdriver` property and mocks browser APIs
- **Realistic User Agents**: Rotates through real browser user agents
- **WebGL & Screen Spoofing**: Mimics real hardware profiles

#### Implementation:
```python
# Remove webdriver detection
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

# Mock plugins and languages
Object.defineProperty(navigator, 'plugins', {
    get: () => [/* realistic plugin list */]
});
```

### 2. Human-Like Behavior Simulation

#### Features:
- **Typing Delays**: Random delays between keystrokes (50-150ms)
- **Mouse Movements**: Random cursor movements to simulate human interaction
- **Random Scrolling**: Periodic page scrolls with varied amounts
- **Reading Pauses**: Natural delays when "reading" content

#### Benefits:
- Breaks predictable automation patterns
- Mimics natural user browsing behavior
- Reduces detection confidence score

### 3. Session Management (`session_manager.py`)

#### Components:
- **Cookie Persistence**: Saves and loads browser cookies across sessions
- **Local/Session Storage**: Preserves browser storage for session continuity
- **Session Health Tracking**: Monitors block rates and rotates unhealthy sessions
- **Multi-Session Support**: Rotates between multiple saved sessions

#### Usage:
```python
session_manager = SessionManager()
session_manager.save_session(driver, "session_1")
# Later...
session_manager.load_session(driver, "session_1")
```

### 4. Request Rate Limiting

#### Intelligent Throttling:
- **Burst Control**: Max 10 requests per 60-second window
- **Minimum Intervals**: 2+ seconds between requests
- **Random Jitter**: Adds ±50% randomness to delays
- **Adaptive Waiting**: Increases delays after detection events

### 5. Multi-Strategy Fallback System (`fallback_strategies.py`)

#### Strategies (in order):
1. **Direct API Calls**: Uses browser's fetch to access API endpoints
2. **RSS Feeds**: Attempts to parse cafe RSS feeds
3. **Search Crawling**: Uses search function with keywords
4. **Mobile Version**: Switches to m.cafe.naver.com (weaker WAF)
5. **Incremental IDs**: Tries sequential article IDs
6. **JavaScript Extraction**: Parses data from page JavaScript
7. **Sitemap Parsing**: Checks for XML sitemaps

#### Benefits:
- Multiple paths to success
- Automatic strategy rotation on failure
- Combines results from successful strategies

### 6. Navigation Improvements

#### Referrer Chain Building:
```python
# Gradual session building
1. Visit naver.com
2. Visit cafe.naver.com  
3. Visit specific cafe home
4. Finally access article list
```

#### Soft Navigation:
- Uses JavaScript `location.assign()` instead of direct navigation
- Preserves referrer headers
- Mimics user link clicking

### 7. GitHub Actions Enhancements (`.github/workflows/enhanced_crawl.yml`)

#### Features:
- **Random Start Delays**: 0-300 second random delay before execution
- **Session Caching**: Preserves sessions between runs
- **Retry Logic**: Automatic retry on failure
- **Flexible Scheduling**: Runs at irregular intervals (cron with offset)

## Usage Instructions

### 1. Update Your Repository

```bash
# Use the enhanced crawler
cp enhanced_main.py main.py

# Or run directly
python enhanced_main.py
```

### 2. Configure Environment Variables

Add these to your GitHub Secrets:
```
MAX_RETRIES=5
REQUEST_DELAY_MIN=3
REQUEST_DELAY_MAX=8
ENABLE_SESSION_ROTATION=true
ENABLE_USER_AGENT_ROTATION=true
```

### 3. Use the Enhanced Workflow

```bash
# Replace existing workflow
cp .github/workflows/enhanced_crawl.yml .github/workflows/crawl.yml
```

### 4. Monitor and Adjust

Check logs for success indicators:
- `✅ Session built successfully`
- `✅ Success with [strategy_name]`
- `✅ Crawled X articles`

## Troubleshooting

### If Still Blocked:

1. **Increase Delays**:
   ```python
   self.human_like_delay(5, 10)  # Longer waits
   ```

2. **Use Mobile-Only**:
   ```python
   return self.mobile_fallback_crawl(club_id, board_id, cafe_name)
   ```

3. **Try Different Times**:
   - Avoid peak hours (9-11 AM, 7-9 PM KST)
   - Run during Korean business hours

4. **Rotate IPs** (if possible):
   - Use GitHub Actions self-hosted runners in different regions
   - Consider proxy services

### Success Metrics:

- **Good**: >50% articles extracted
- **Acceptable**: >30% articles extracted  
- **Poor**: <30% articles extracted (needs adjustment)

## Best Practices

1. **Never** access classic endpoints directly without session warmup
2. **Always** add random delays between requests
3. **Rotate** between multiple strategies
4. **Monitor** session health and rotate when degraded
5. **Respect** rate limits and avoid aggressive crawling

## Testing Locally

```bash
# Test with debug output
DEBUG_MODE=true python enhanced_main.py

# Test mobile strategy only  
USE_MOBILE=true python enhanced_main.py

# Test with specific cafe
CAFE1_CLUB_ID=your_id CAFE1_BOARD_ID=your_board python enhanced_main.py
```

## Additional Recommendations

1. **Consider Official APIs**: Check if Naver provides official APIs for your use case
2. **Respect robots.txt**: Follow crawling guidelines
3. **Add delays between runs**: Don't run too frequently
4. **Monitor for changes**: Naver may update their detection methods
5. **Have backup plans**: Store partial data, handle failures gracefully

## Summary

The enhanced crawler addresses bot detection through:
- **Technical evasion**: Removing automation signatures
- **Behavioral mimicry**: Acting like a real user
- **Strategic diversity**: Multiple extraction methods
- **Session persistence**: Building trust over time
- **Intelligent fallbacks**: Graceful degradation

This multi-layered approach significantly improves success rates while respecting the target website's resources.