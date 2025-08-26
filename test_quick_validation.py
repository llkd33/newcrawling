#!/usr/bin/env python3
"""
빠른 검증 테스트
Task 11의 핵심 기능들을 빠르게 검증하는 간단한 테스트
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from content_extractor import ContentExtractor
from content_extraction_models import ExtractionConfig

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def quick_validation_test():
    """빠른 검증 테스트"""
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("🚀 Task 11 빠른 검증 테스트 시작")
    logger.info("="*60)
    
    # 환경변수 확인
    if not os.getenv('NAVER_ID') or not os.getenv('NAVER_PW'):
        logger.error("❌ NAVER_ID, NAVER_PW 환경변수가 설정되지 않았습니다")
        return False
    
    # Chrome 드라이버 설정
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)
        
        logger.info("✅ Chrome 드라이버 초기화 성공")
        
        # 네이버 로그인
        logger.info("🔐 네이버 로그인 시도...")
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(2)
        
        # 간단한 로그인 (실제 환경에서는 더 안전한 방법 사용)
        from selenium.webdriver.common.by import By
        
        id_input = driver.find_element(By.ID, 'id')
        pw_input = driver.find_element(By.ID, 'pw')
        
        driver.execute_script(f"arguments[0].value = '{os.getenv('NAVER_ID')}'", id_input)
        time.sleep(1)
        driver.execute_script(f"arguments[0].value = '{os.getenv('NAVER_PW')}'", pw_input)
        time.sleep(1)
        
        login_btn = driver.find_element(By.ID, 'log.login')
        driver.execute_script("arguments[0].click();", login_btn)
        time.sleep(8)
        
        logger.info("✅ 네이버 로그인 완료")
        
        # ContentExtractor 테스트
        logger.info("🧪 ContentExtractor 기능 테스트...")
        
        config = ExtractionConfig(
            timeout_seconds=30,
            min_content_length=30,
            enable_debug_screenshot=True
        )
        
        extractor = ContentExtractor(driver, wait, config)
        
        # 테스트 URL (F-E 카페 게시물)
        test_url = "https://cafe.naver.com/f-e/cafes/18786605/articles/1941841?boardtype=L&menuid=105"
        
        logger.info(f"📖 테스트 URL: {test_url}")
        
        # 콘텐츠 추출 테스트
        start_time = time.time()
        result = extractor.extract_content(test_url)
        extraction_time = time.time() - start_time
        
        # 결과 분석
        logger.info("="*60)
        logger.info("📊 테스트 결과:")
        logger.info("="*60)
        
        logger.info(f"✅ 추출 성공: {result.success}")
        logger.info(f"🔧 추출 방법: {result.extraction_method.value}")
        logger.info(f"⭐ 품질 점수: {result.quality_score:.2f}")
        logger.info(f"⏱️ 추출 시간: {extraction_time:.2f}초")
        logger.info(f"📝 내용 길이: {len(result.content)}자")
        
        if result.debug_info:
            logger.info(f"🔍 에디터 타입: {result.debug_info.get('editor_type_detected', 'Unknown')}")
            logger.info(f"📄 페이지 상태: {result.debug_info.get('page_ready_state', 'Unknown')}")
        
        if result.error_message:
            logger.warning(f"⚠️ 오류 메시지: {result.error_message}")
        
        # 내용 미리보기
        if result.content:
            preview = result.content[:200]
            logger.info(f"\n📖 내용 미리보기:")
            logger.info("-" * 40)
            logger.info(preview)
            if len(result.content) > 200:
                logger.info(f"... (총 {len(result.content)}자)")
            logger.info("-" * 40)
        
        # 성공 조건 확인
        success_conditions = [
            ("추출 성공", result.success),
            ("내용 길이 충족", len(result.content) >= 30),
            ("품질 점수 양호", result.quality_score >= 0.3),
            ("추출 시간 적절", extraction_time <= 60)
        ]
        
        logger.info("\n🎯 성공 조건 확인:")
        all_passed = True
        
        for condition_name, condition_result in success_conditions:
            status = "✅" if condition_result else "❌"
            logger.info(f"  {status} {condition_name}: {condition_result}")
            if not condition_result:
                all_passed = False
        
        # Requirements 충족 여부
        logger.info("\n📋 Requirements 충족 여부:")
        
        # Requirement 1.1, 1.2, 1.3 (에디터 형식 감지)
        editor_detected = result.debug_info.get('editor_type_detected') is not None
        logger.info(f"  ✅ Req 1.1-1.3 (에디터 형식 감지): {editor_detected}")
        
        # Requirement 2.1, 2.2, 2.3 (동적 콘텐츠 로딩)
        page_loaded = result.debug_info.get('page_ready_state') == 'complete'
        logger.info(f"  ✅ Req 2.1-2.3 (동적 콘텐츠 로딩): {page_loaded}")
        
        # 전체 결과
        logger.info("="*60)
        if all_passed and result.success:
            logger.info("🎉 빠른 검증 테스트 성공!")
            logger.info("💡 Task 11의 핵심 기능들이 정상적으로 작동합니다.")
            return True
        else:
            logger.warning("⚠️ 빠른 검증 테스트에서 일부 문제가 발견되었습니다.")
            logger.info("💡 전체 통합 테스트를 실행하여 상세한 분석을 수행하세요.")
            return False
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
        
    finally:
        if driver:
            driver.quit()
            logger.info("✅ 드라이버 종료")


def main():
    """메인 실행 함수"""
    print("Task 11: 통합 테스트 및 실제 데이터 검증 - 빠른 검증")
    print("=" * 60)
    
    success = quick_validation_test()
    
    if success:
        print("\n🎉 빠른 검증 완료! 전체 통합 테스트를 실행할 준비가 되었습니다.")
        print("💡 전체 테스트 실행: python run_integration_tests.py")
    else:
        print("\n❌ 빠른 검증에서 문제가 발견되었습니다.")
        print("💡 환경 설정과 필수 조건을 확인해주세요.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)