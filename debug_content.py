#!/usr/bin/env python3
"""
내용 추출 디버깅 스크립트
어디서 문제가 발생하는지 정확히 파악
"""

import os
import sys
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

load_dotenv()

def debug_content_extraction():
    """내용 추출 디버깅"""
    # 환경변수 확인 (필수값 누락 시 빠르게 종료)
    required_env = ['NAVER_ID', 'NAVER_PW', 'CAFE1_URL', 'CAFE1_CLUB_ID', 'CAFE1_BOARD_ID']
    missing = [k for k in required_env if not os.getenv(k)]
    if missing:
        print(f"❌ 환경변수 누락: {', '.join(missing)}")
        print("해결 방법:")
        print("  1) 루트에 .env 파일 생성")
        print("  2) .env.example 참고해 값 채우기")
        print("  3) 예시: NAVER_ID=your_id, NAVER_PW=your_pw, CAFE1_URL=... 등")
        return

    # 크롬 드라이버 설정
    options = Options()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # 네이버 로그인
        print("🔐 네이버 로그인...")
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(2)
        
        # 로그인
        naver_id = os.getenv('NAVER_ID')
        naver_pw = os.getenv('NAVER_PW')
        driver.find_element(By.ID, 'id').send_keys(naver_id)
        driver.find_element(By.ID, 'pw').send_keys(naver_pw)
        driver.find_element(By.ID, 'log.login').click()
        
        print("⏳ 로그인 대기...")
        time.sleep(8)
        
        # 카페로 이동
        cafe_url = os.getenv('CAFE1_URL')
        club_id = os.getenv('CAFE1_CLUB_ID')
        board_id = os.getenv('CAFE1_BOARD_ID')
        
        board_url = f"{cafe_url}/ArticleList.nhn?search.clubid={club_id}&search.menuid={board_id}"
        print(f"📍 카페 접속: {board_url}")
        driver.get(board_url)
        time.sleep(3)
        
        # iframe 전환
        try:
            driver.switch_to.frame('cafe_main')
            print("✅ 게시판 iframe 전환 성공")
        except:
            print("❌ 게시판 iframe 전환 실패")
        
        # 첫 번째 게시물 찾기
        article_link = None
        selectors = ['a.article', 'td.td_article a', '.inner_list a']
        for sel in selectors:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, sel)
                article_link = elem.get_attribute('href')
                article_title = elem.text
                print(f"✅ 게시물 발견: {article_title}")
                print(f"   링크: {article_link}")
                break
            except:
                continue
        
        if not article_link:
            print("❌ 게시물을 찾을 수 없습니다")
            return
        
        # 게시물 페이지로 이동
        driver.switch_to.default_content()
        driver.get(article_link)
        time.sleep(5)
        
        print("\n" + "="*60)
        print("📄 게시물 페이지 분석")
        print("="*60)
        
        # 1. iframe 체크
        iframe_found = False
        try:
            driver.switch_to.frame('cafe_main')
            iframe_found = True
            print("✅ 게시물 iframe 전환 성공")
        except:
            print("❌ 게시물 iframe 없음")
        
        # 2. 페이지 소스 일부 확인
        page_source = driver.page_source
        print(f"\n📋 페이지 소스 길이: {len(page_source)} 자")
        
        # 3. 모든 가능한 선택자 테스트
        print("\n🔍 선택자 테스트:")
        test_selectors = [
            '.se-main-container',
            '.se-section',
            '.se-text-paragraph',
            '.ContentRenderer',
            '#postViewArea',
            '.NHN_Writeform_Main',
            '#content-area',
            '.post_ct',
            '#tbody',
            'td.view',
            '.view_content',
            'div.content_box',
            'div.board-read-body'
        ]
        
        for selector in test_selectors:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                text = elem.text[:100] if elem.text else "(빈 텍스트)"
                print(f"  ✅ {selector}: {text}...")
            except:
                print(f"  ❌ {selector}: 없음")
        
        # 4. JavaScript로 디버깅
        print("\n📜 JavaScript 디버깅:")
        js_result = driver.execute_script("""
            var result = {
                'se-main-container': document.querySelector('.se-main-container') ? '있음' : '없음',
                'se-text-paragraph': document.querySelectorAll('.se-text-paragraph').length,
                'images': document.querySelectorAll('img').length,
                'body_text_length': document.body.innerText.length,
                'iframes': document.querySelectorAll('iframe').length
            };
            
            // 실제 내용 찾기
            var content = null;
            
            // 방법 1: se-main-container
            var container = document.querySelector('.se-main-container');
            if (container) {
                content = container.innerText || container.textContent;
                result['se_content_length'] = content ? content.length : 0;
                result['se_content_preview'] = content ? content.substring(0, 100) : '';
            }
            
            // 방법 2: 모든 p 태그
            if (!content) {
                var paragraphs = document.querySelectorAll('p');
                var texts = [];
                for (var i = 0; i < paragraphs.length; i++) {
                    var text = paragraphs[i].innerText || paragraphs[i].textContent;
                    if (text && text.length > 50) {
                        texts.push(text);
                    }
                }
                if (texts.length > 0) {
                    content = texts.join(' ');
                    result['p_content_length'] = content.length;
                    result['p_content_preview'] = content.substring(0, 100);
                }
            }
            
            return JSON.stringify(result, null, 2);
        """)
        
        print(js_result)
        
        # 5. 실제 내용 추출 시도
        print("\n📝 실제 내용 추출 시도:")
        
        # 방법 1: 직접 선택
        content = None
        for selector in ['.se-main-container', '.ContentRenderer', '#postViewArea']:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                content = elem.text
                if content and len(content) > 30:
                    print(f"✅ {selector}에서 추출 성공!")
                    print(f"   내용 길이: {len(content)} 자")
                    print(f"   미리보기: {content[:200]}...")
                    break
            except:
                continue
        
        if not content:
            # 방법 2: JavaScript
            content = driver.execute_script("""
                var selectors = ['.se-main-container', '.ContentRenderer', '#postViewArea', '#tbody', '.view_content'];
                for (var i = 0; i < selectors.length; i++) {
                    var elem = document.querySelector(selectors[i]);
                    if (elem) {
                        var text = elem.innerText || elem.textContent;
                        if (text && text.length > 30) {
                            return text;
                        }
                    }
                }
                return document.body.innerText || '';
            """)
            
            if content:
                print(f"✅ JavaScript로 추출 성공!")
                print(f"   내용 길이: {len(content)} 자")
                print(f"   미리보기: {content[:200]}...")
        
        if not content:
            print("❌ 내용을 추출할 수 없습니다")
            
            # 스크린샷 저장
            driver.save_screenshot('debug_screenshot.png')
            print("\n📸 스크린샷 저장: debug_screenshot.png")
            
            # HTML 저장
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("📄 HTML 저장: debug_page.html")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        input("\n엔터를 눌러서 종료...")
        driver.quit()

if __name__ == "__main__":
    debug_content_extraction()
