#!/usr/bin/env python3
"""
PreloadingManager 사용 예제
기존 NaverCafeCrawler의 get_article_content 메서드에서 PreloadingManager를 사용하는 방법을 보여줍니다.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from preloading_manager import PreloadingManager
from content_extraction_models import ExtractionConfig

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def enhanced_get_article_content_example(driver, url: str) -> str:
    """
    PreloadingManager를 사용한 향상된 게시물 내용 추출 예제
    
    이 함수는 기존 NaverCafeCrawler.get_article_content 메서드를 
    PreloadingManager를 사용하도록 개선한 예제입니다.
    """
    # PreloadingManager 초기화
    config = ExtractionConfig(
        timeout_seconds=30,
        scroll_pause_time=2.0,
        enable_lazy_loading_trigger=True
    )
    preloader = PreloadingManager(driver, config)
    
    original_window = driver.current_window_handle
    
    try:
        logging.info(f"🔗 게시물 URL 접근: {url}")
        
        # 새 탭에서 열기
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        
        # PreloadingManager를 사용한 완전한 페이지 로딩 대기
        logging.info("⏳ PreloadingManager로 페이지 로딩 대기...")
        if not preloader.wait_for_complete_loading(timeout=20):
            logging.warning("⚠️ 페이지 로딩 대기 실패, 계속 진행")
        
        # PreloadingManager를 사용한 iframe 전환 및 추가 로딩 대기
        logging.info("🖼️ iframe 전환 및 동적 콘텐츠 로딩...")
        if not preloader.wait_for_iframe_and_switch('cafe_main', timeout=15):
            logging.error("❌ iframe 전환 실패")
            return f"iframe 전환 실패\n원본 링크: {url}"
        
        # 향상된 콘텐츠 대기 (여러 단계 검증)
        logging.info("🔍 향상된 콘텐츠 로딩 대기...")
        content_ready = preloader.enhanced_wait_for_content(max_attempts=3)
        if content_ready:
            logging.info("✅ 동적 콘텐츠 로딩 완료 확인")
        else:
            logging.warning("⚠️ 동적 콘텐츠 로딩 미확인, 추출 시도")
        
        # 이제 기존의 선택자 기반 추출 로직을 사용
        content = extract_content_with_selectors(driver)
        
        if content and len(content) > 30:
            logging.info(f"✅ 콘텐츠 추출 성공: {len(content)}자")
            return content
        else:
            logging.warning("⚠️ 기본 추출 실패, 대체 방법 시도")
            return f"내용을 불러올 수 없습니다.\n원본 링크: {url}"
    
    except Exception as e:
        logging.error(f"❌ 콘텐츠 추출 중 오류: {e}")
        return f"내용을 불러올 수 없습니다.\n원본 링크: {url}"
    
    finally:
        # 탭 닫고 원래 창으로 복귀
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(original_window)


def extract_content_with_selectors(driver) -> str:
    """
    기존 선택자 기반 콘텐츠 추출 로직
    (실제 구현에서는 SelectorStrategy 클래스를 사용할 예정)
    """
    selectors = [
        # SmartEditor 3.0 (최신)
        '.se-main-container',
        '.se-component-content',
        'div.se-module-text',
        
        # SmartEditor 2.0
        '.ContentRenderer',
        '#postViewArea',
        '.NHN_Writeform_Main',
        
        # 일반 에디터
        '#content-area',
        'div[id="content-area"]',
        '.content_view',
        '.board-content',
        
        # 구형 에디터
        '#tbody',
        'td[id="tbody"]',
        '.post_content',
        '.view_content'
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements("css selector", selector)
            if elements:
                element = elements[0]
                text = element.text.strip()
                
                if text and len(text) > 20:
                    logging.info(f"✅ 선택자 '{selector}'로 내용 추출: {len(text)}자")
                    return text
                    
        except Exception as e:
            logging.debug(f"선택자 {selector} 실패: {e}")
            continue
    
    return ""


def demo_preloading_manager():
    """PreloadingManager 데모"""
    logging.info("🚀 PreloadingManager 데모 시작")
    
    # Chrome 드라이버 설정 (헤드리스 모드)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        driver = webdriver.Chrome(options=options)
        
        # PreloadingManager 초기화
        config = ExtractionConfig(
            timeout_seconds=15,
            scroll_pause_time=1.0,
            enable_lazy_loading_trigger=True
        )
        preloader = PreloadingManager(driver, config)
        
        # 테스트 페이지로 이동
        test_url = "https://www.naver.com"
        logging.info(f"📍 테스트 URL 접근: {test_url}")
        driver.get(test_url)
        
        # 기본 로딩 대기 테스트
        logging.info("⏳ 기본 로딩 대기 테스트...")
        success = preloader.wait_for_complete_loading(timeout=10)
        logging.info(f"결과: {'성공' if success else '실패'}")
        
        # Lazy loading 트리거 테스트
        logging.info("🔄 Lazy loading 트리거 테스트...")
        preloader.trigger_lazy_loading()
        logging.info("✅ Lazy loading 트리거 완료")
        
        # 동적 콘텐츠 확인 테스트
        logging.info("🔍 동적 콘텐츠 로드 확인 테스트...")
        content_loaded = preloader.check_dynamic_content_loaded()
        logging.info(f"결과: {'로드됨' if content_loaded else '미로드'}")
        
        # 향상된 콘텐츠 대기 테스트
        logging.info("🚀 향상된 콘텐츠 대기 테스트...")
        enhanced_success = preloader.enhanced_wait_for_content(max_attempts=2)
        logging.info(f"결과: {'성공' if enhanced_success else '실패'}")
        
        logging.info("✅ PreloadingManager 데모 완료")
        
    except Exception as e:
        logging.error(f"❌ 데모 실행 중 오류: {e}")
    
    finally:
        if 'driver' in locals():
            driver.quit()


if __name__ == "__main__":
    demo_preloading_manager()