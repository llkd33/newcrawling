#!/usr/bin/env python3
"""
F-E 카페 크롤링 디버깅 스크립트
게시물 목록 추출 및 작성자 정보 확인
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_driver():
    """Chrome 드라이버 설정"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    return driver

def debug_fe_cafe_structure():
    """F-E 카페 구조 디버깅"""
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    
    try:
        # 테스트 URL (실제 F-E 카페 URL로 변경 필요)
        test_url = "https://cafe.naver.com/f-e/cafes/28339259/menus/393?viewType=L"
        
        logging.info(f"🔍 F-E 카페 구조 분석 시작: {test_url}")
        driver.get(test_url)
        time.sleep(5)
        
        # iframe 전환 시도
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'cafe_main')))
            logging.info("✅ iframe 전환 성공")
            time.sleep(3)
        except TimeoutException:
            logging.warning("⚠️ iframe 전환 실패")
        
        # 게시물 목록 구조 분석
        js_analyze = """
        var analysis = {
            totalElements: 0,
            tableRows: 0,
            listItems: 0,
            articleLinks: 0,
            nicknameElements: 0,
            sampleData: []
        };
        
        // 전체 요소 수
        analysis.totalElements = document.querySelectorAll('*').length;
        
        // 테이블 행 수
        var tableRows = document.querySelectorAll('table tr, .board-list tr, .article-board tr');
        analysis.tableRows = tableRows.length;
        
        // 리스트 아이템 수
        var listItems = document.querySelectorAll('.article-list li, .board-list li, ul li');
        analysis.listItems = listItems.length;
        
        // 게시물 링크 수
        var articleLinks = document.querySelectorAll('a[href*="articles"], a[href*="articleid"]');
        analysis.articleLinks = articleLinks.length;
        
        // 닉네임 요소 수
        var nicknames = document.querySelectorAll('.nickname, span.nickname, .author, .writer, td.p-nick, .td_name');
        analysis.nicknameElements = nicknames.length;
        
        // 샘플 데이터 수집 (처음 5개)
        for (var i = 0; i < Math.min(5, tableRows.length); i++) {
            var row = tableRows[i];
            var sample = {
                rowIndex: i,
                rowText: row.innerText ? row.innerText.substring(0, 100) : '',
                titleLink: null,
                author: null
            };
            
            // 제목 링크 찾기
            var titleCell = row.querySelector('td.td_article, .td_article, .title, .subject');
            if (titleCell) {
                var link = titleCell.querySelector('a[href*="articles"], a[href*="articleid"]');
                if (link) {
                    sample.titleLink = {
                        text: link.innerText || link.textContent,
                        href: link.href
                    };
                }
            }
            
            // 작성자 찾기
            var authorCell = row.querySelector('td.p-nick, .td_name, .author, .writer, .nickname');
            if (authorCell) {
                var authorSpan = authorCell.querySelector('span.nickname, .nickname, span');
                if (authorSpan) {
                    sample.author = authorSpan.innerText || authorSpan.textContent;
                } else {
                    sample.author = authorCell.innerText || authorCell.textContent;
                }
            }
            
            analysis.sampleData.push(sample);
        }
        
        return analysis;
        """
        
        analysis = driver.execute_script(js_analyze)
        
        logging.info("📊 F-E 카페 구조 분석 결과:")
        logging.info(f"  - 전체 요소 수: {analysis['totalElements']}")
        logging.info(f"  - 테이블 행 수: {analysis['tableRows']}")
        logging.info(f"  - 리스트 아이템 수: {analysis['listItems']}")
        logging.info(f"  - 게시물 링크 수: {analysis['articleLinks']}")
        logging.info(f"  - 닉네임 요소 수: {analysis['nicknameElements']}")
        
        logging.info("\n📝 샘플 데이터:")
        for i, sample in enumerate(analysis['sampleData']):
            logging.info(f"  [{i+1}] 행 텍스트: {sample['rowText'][:50]}...")
            if sample['titleLink']:
                logging.info(f"      제목: {sample['titleLink']['text']}")
                logging.info(f"      링크: {sample['titleLink']['href']}")
            if sample['author']:
                logging.info(f"      작성자: {sample['author']}")
            logging.info("")
        
        # 페이지 HTML 일부 저장 (디버깅용)
        page_html = driver.execute_script("return document.body.innerHTML;")
        with open("fe_cafe_debug.html", "w", encoding="utf-8") as f:
            f.write(page_html[:10000])  # 처음 10KB만
        logging.info("📄 페이지 HTML 샘플 저장: fe_cafe_debug.html")
        
    except Exception as e:
        logging.error(f"❌ 디버깅 중 오류: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_fe_cafe_structure()