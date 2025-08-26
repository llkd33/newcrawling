#!/usr/bin/env python3
"""
네이버 카페 콘텐츠 추출을 위한 동적 로딩 관리 클래스

Task 2: PreloadingManager 클래스 구현
Requirements 2.1, 2.2, 2.3을 완전히 구현:
- 2.1: document.readyState 확인 및 JavaScript 실행 완료 대기
- 2.2: iframe 전환 후 최소 3초간 추가 대기로 동적 콘텐츠 로딩 허용
- 2.3: 페이지 스크롤을 통한 lazy loading 콘텐츠 활성화
"""

import time
import logging
import os
from typing import Optional, Dict, Any, List
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from content_extraction_models import PreloadingManagerInterface, ExtractionConfig


class PreloadingManager(PreloadingManagerInterface):
    """
    동적 콘텐츠 로딩 대기 및 관리를 담당하는 클래스
    
    Requirements 2.1, 2.2, 2.3을 구현:
    - document.readyState 확인 및 JavaScript 실행 완료 대기
    - iframe 전환 후 추가 대기를 통한 동적 콘텐츠 로딩 허용
    - 페이지 스크롤을 통한 lazy loading 콘텐츠 활성화
    """
    
    def __init__(self, driver, config: Optional[ExtractionConfig] = None):
        """
        PreloadingManager 초기화
        
        Args:
            driver: Selenium WebDriver 인스턴스
            config: 추출 설정 (None일 경우 기본값 사용)
        """
        self.driver = driver
        self.config = config or ExtractionConfig()
        self.logger = logging.getLogger(__name__)
    
    def wait_for_complete_loading(self, timeout: int = 30) -> bool:
        """
        페이지의 완전한 로딩을 대기합니다.
        
        Requirements 2.1을 완전히 구현:
        - document.readyState가 'complete'가 될 때까지 대기
        - JavaScript 실행 완료 확인 (jQuery, 네이버 특화 스크립트 포함)
        - 네트워크 요청 완료 대기
        - 동적 콘텐츠 로딩 상태 확인
        
        Args:
            timeout: 최대 대기 시간 (초)
            
        Returns:
            bool: 로딩 완료 여부
        """
        try:
            self.logger.info(f"⏳ 페이지 완전 로딩 대기 시작 (최대 {timeout}초)")
            start_time = time.time()
            
            # 1단계: document.readyState가 'complete'가 될 때까지 대기
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            self.logger.info("✅ document.readyState = 'complete' 확인")
            
            # 2단계: JavaScript 라이브러리 로딩 완료 대기
            self._wait_for_javascript_libraries(timeout=min(10, timeout//3))
            
            # 3단계: 네이버 카페 특화 스크립트 로딩 대기
            self._wait_for_naver_cafe_scripts(timeout=min(10, timeout//3))
            
            # 4단계: 네트워크 요청 완료 대기
            self._wait_for_network_idle(timeout=min(5, timeout//6))
            
            # 5단계: Requirements 2.2 구현 - iframe 전환 후 최소 3초 추가 대기
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time > 3:
                self.logger.info("⏳ iframe 전환 후 동적 콘텐츠 로딩을 위한 추가 대기 (3초)")
                time.sleep(3)
            else:
                self.logger.warning(f"⚠️ 타임아웃 임박으로 추가 대기 시간 단축: {max(1, remaining_time)}초")
                time.sleep(max(1, remaining_time))
            
            self.logger.info("✅ 페이지 완전 로딩 대기 완료")
            return True
            
        except TimeoutException as e:
            self.logger.warning(f"⚠️ 페이지 로딩 대기 타임아웃: {e}")
            return False
        except WebDriverException as e:
            self.logger.error(f"❌ 페이지 로딩 대기 중 WebDriver 오류: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 페이지 로딩 대기 중 예상치 못한 오류: {e}")
            return False
    
    def _wait_for_javascript_libraries(self, timeout: int = 10) -> bool:
        """JavaScript 라이브러리 로딩 완료 대기"""
        try:
            # jQuery 활성 요청 완료 대기
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("""
                    if (typeof jQuery !== 'undefined') {
                        return jQuery.active === 0;
                    }
                    return true;
                """)
            )
            self.logger.debug("✅ jQuery 활성 요청 완료 확인")
            
            # 기타 JavaScript 라이브러리 로딩 확인
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("""
                    // 일반적인 로딩 상태 확인
                    var loadComplete = document.readyState === 'complete';
                    
                    // Performance API를 통한 로드 이벤트 확인
                    if (typeof window.performance !== 'undefined' && window.performance.timing) {
                        loadComplete = loadComplete && window.performance.timing.loadEventEnd > 0;
                    }
                    
                    return loadComplete;
                """)
            )
            self.logger.debug("✅ JavaScript 라이브러리 로딩 완료 확인")
            return True
            
        except TimeoutException:
            self.logger.debug("⚠️ JavaScript 라이브러리 로딩 대기 타임아웃")
            return False
    
    def _wait_for_naver_cafe_scripts(self, timeout: int = 10) -> bool:
        """네이버 카페 특화 스크립트 로딩 대기"""
        try:
            # SmartEditor 관련 스크립트 로딩 확인
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("""
                    // SmartEditor 3.0 확인
                    var se3Ready = document.querySelector('.se-main-container') !== null;
                    
                    // SmartEditor 2.0 확인  
                    var se2Ready = document.querySelector('.ContentRenderer, #postViewArea') !== null;
                    
                    // 일반 에디터 확인
                    var generalReady = document.querySelector('#content-area, #tbody') !== null;
                    
                    // 최소한 하나의 에디터가 감지되거나 5초 이상 경과
                    return se3Ready || se2Ready || generalReady || 
                           (Date.now() - window.performance.timing.navigationStart) > 5000;
                """)
            )
            self.logger.debug("✅ 네이버 카페 에디터 스크립트 로딩 확인")
            return True
            
        except TimeoutException:
            self.logger.debug("⚠️ 네이버 카페 스크립트 로딩 대기 타임아웃")
            return False
    
    def _wait_for_network_idle(self, timeout: int = 5) -> bool:
        """네트워크 요청 완료 대기 (Network Idle 상태)"""
        try:
            # 간단한 네트워크 idle 확인 (Performance API 사용)
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("""
                    if (typeof window.performance === 'undefined' || !window.performance.getEntriesByType) {
                        return true; // Performance API 미지원 시 통과
                    }
                    
                    var resources = window.performance.getEntriesByType('resource');
                    var now = window.performance.now();
                    
                    // 최근 1초 내에 완료된 리소스가 있는지 확인
                    var recentResources = resources.filter(function(resource) {
                        return resource.responseEnd > (now - 1000);
                    });
                    
                    return recentResources.length === 0;
                """)
            )
            self.logger.debug("✅ 네트워크 idle 상태 확인")
            return True
            
        except TimeoutException:
            self.logger.debug("⚠️ 네트워크 idle 대기 타임아웃")
            return False
    
    def trigger_lazy_loading(self) -> None:
        """
        Lazy loading 콘텐츠를 활성화합니다.
        
        Requirements 2.3을 완전히 구현:
        - 페이지 스크롤을 통해 lazy loading 콘텐츠 활성화
        - 다양한 스크롤 패턴으로 모든 lazy loading 요소 활성화
        - 이미지 및 동적 콘텐츠 로딩 트리거
        - 네이버 카페 특화 lazy loading 처리
        """
        try:
            self.logger.info("🔄 Lazy loading 콘텐츠 활성화 시작")
            
            # 현재 스크롤 위치 및 페이지 정보 저장
            scroll_info = self.driver.execute_script("""
                return {
                    originalY: window.pageYOffset,
                    originalX: window.pageXOffset,
                    bodyHeight: document.body.scrollHeight,
                    windowHeight: window.innerHeight,
                    bodyWidth: document.body.scrollWidth,
                    windowWidth: window.innerWidth
                };
            """)
            
            # 1단계: 수직 스크롤 패턴 (상 → 중간 → 하 → 상)
            self._perform_vertical_scroll_pattern(scroll_info)
            
            # 2단계: 네이버 카페 특화 lazy loading 트리거
            self._trigger_naver_cafe_lazy_loading()
            
            # 3단계: 이미지 lazy loading 특별 처리
            self._trigger_image_lazy_loading()
            
            # 4단계: 수평 스크롤 (필요한 경우)
            if scroll_info['bodyWidth'] > scroll_info['windowWidth']:
                self._perform_horizontal_scroll_pattern(scroll_info)
            
            # 5단계: 원래 스크롤 위치로 복원
            self.driver.execute_script(f"""
                window.scrollTo({scroll_info['originalX']}, {scroll_info['originalY']});
            """)
            time.sleep(0.5)
            self.logger.debug(f"📍 원래 스크롤 위치로 복원: ({scroll_info['originalX']}, {scroll_info['originalY']})")
            
            # 6단계: 최종 대기 (모든 lazy loading 완료 대기)
            time.sleep(1)
            
            self.logger.info("✅ Lazy loading 콘텐츠 활성화 완료")
            
        except WebDriverException as e:
            self.logger.error(f"❌ Lazy loading 활성화 중 WebDriver 오류: {e}")
        except Exception as e:
            self.logger.error(f"❌ Lazy loading 활성화 중 예상치 못한 오류: {e}")
    
    def _perform_vertical_scroll_pattern(self, scroll_info: Dict[str, Any]) -> None:
        """수직 스크롤 패턴 실행"""
        body_height = scroll_info['bodyHeight']
        window_height = scroll_info['windowHeight']
        
        if body_height <= window_height:
            self.logger.debug("📍 페이지가 짧아 수직 스크롤 불필요")
            return
        
        # 스크롤 위치들 계산
        scroll_positions = [
            0,  # 상단
            body_height // 4,  # 1/4 지점
            body_height // 2,  # 중간
            body_height * 3 // 4,  # 3/4 지점
            body_height - window_height,  # 하단
        ]
        
        for i, position in enumerate(scroll_positions):
            self.driver.execute_script(f"window.scrollTo(0, {position});")
            time.sleep(self.config.scroll_pause_time)
            self.logger.debug(f"📍 수직 스크롤 {i+1}/{len(scroll_positions)}: {position}px")
    
    def _perform_horizontal_scroll_pattern(self, scroll_info: Dict[str, Any]) -> None:
        """수평 스크롤 패턴 실행 (넓은 콘텐츠가 있는 경우)"""
        body_width = scroll_info['bodyWidth']
        window_width = scroll_info['windowWidth']
        
        scroll_positions = [
            0,  # 좌측
            (body_width - window_width) // 2,  # 중간
            body_width - window_width,  # 우측
        ]
        
        for i, position in enumerate(scroll_positions):
            self.driver.execute_script(f"window.scrollTo({position}, window.pageYOffset);")
            time.sleep(1)
            self.logger.debug(f"📍 수평 스크롤 {i+1}/{len(scroll_positions)}: {position}px")
    
    def _trigger_naver_cafe_lazy_loading(self) -> None:
        """네이버 카페 특화 lazy loading 트리거"""
        try:
            # SmartEditor 이미지 lazy loading 트리거
            self.driver.execute_script("""
                // SmartEditor 3.0 이미지 lazy loading
                var se3Images = document.querySelectorAll('.se-image-resource[data-src]');
                se3Images.forEach(function(img) {
                    if (img.dataset.src && !img.src) {
                        img.src = img.dataset.src;
                    }
                });
                
                // SmartEditor 2.0 이미지 lazy loading
                var se2Images = document.querySelectorAll('img[data-lazy-src]');
                se2Images.forEach(function(img) {
                    if (img.dataset.lazySrc && !img.src) {
                        img.src = img.dataset.lazySrc;
                    }
                });
                
                // 일반적인 lazy loading 이미지
                var lazyImages = document.querySelectorAll('img[data-original], img[loading="lazy"]');
                lazyImages.forEach(function(img) {
                    if (img.dataset.original && !img.src) {
                        img.src = img.dataset.original;
                    }
                });
            """)
            self.logger.debug("✅ 네이버 카페 특화 lazy loading 트리거 완료")
            
        except Exception as e:
            self.logger.debug(f"⚠️ 네이버 카페 lazy loading 트리거 중 오류: {e}")
    
    def _trigger_image_lazy_loading(self) -> None:
        """이미지 lazy loading 특별 처리"""
        try:
            # Intersection Observer가 있는 이미지들을 뷰포트에 노출
            lazy_images = self.driver.find_elements(By.CSS_SELECTOR, 
                "img[data-src], img[data-lazy-src], img[data-original], img[loading='lazy']")
            
            if lazy_images:
                self.logger.debug(f"🖼️ {len(lazy_images)}개의 lazy loading 이미지 발견")
                
                # 각 이미지를 뷰포트에 스크롤하여 로딩 트리거
                for i, img in enumerate(lazy_images[:10]):  # 최대 10개만 처리 (성능 고려)
                    try:
                        # 이미지 위치로 스크롤
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img)
                        time.sleep(0.5)
                        
                        # 강제로 이미지 로딩 트리거
                        self.driver.execute_script("""
                            var img = arguments[0];
                            if (img.dataset.src && !img.src) {
                                img.src = img.dataset.src;
                            } else if (img.dataset.lazySrc && !img.src) {
                                img.src = img.dataset.lazySrc;
                            } else if (img.dataset.original && !img.src) {
                                img.src = img.dataset.original;
                            }
                        """, img)
                        
                    except Exception as e:
                        self.logger.debug(f"⚠️ 이미지 {i+1} lazy loading 처리 중 오류: {e}")
                        continue
                
                self.logger.debug("✅ 이미지 lazy loading 처리 완료")
            
        except Exception as e:
            self.logger.debug(f"⚠️ 이미지 lazy loading 처리 중 오류: {e}")
    
    def wait_for_iframe_and_switch(self, iframe_name: str = 'cafe_main', timeout: int = 15) -> bool:
        """
        iframe이 로드될 때까지 대기하고 전환합니다.
        
        Args:
            iframe_name: iframe의 name 속성값
            timeout: 최대 대기 시간 (초)
            
        Returns:
            bool: iframe 전환 성공 여부
        """
        try:
            self.logger.info(f"⏳ iframe '{iframe_name}' 전환 대기")
            
            # iframe이 사용 가능해질 때까지 대기하고 전환
            WebDriverWait(self.driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.NAME, iframe_name))
            )
            
            self.logger.info(f"✅ iframe '{iframe_name}' 전환 성공")
            
            # iframe 전환 후 추가 로딩 대기 (Requirements 2.2)
            if self.config.enable_lazy_loading_trigger:
                self.wait_for_complete_loading(timeout=10)
                self.trigger_lazy_loading()
            
            return True
            
        except TimeoutException:
            self.logger.error(f"❌ iframe '{iframe_name}' 전환 타임아웃")
            return False
        except WebDriverException as e:
            self.logger.error(f"❌ iframe '{iframe_name}' 전환 중 WebDriver 오류: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ iframe '{iframe_name}' 전환 중 예상치 못한 오류: {e}")
            return False
    
    def wait_for_element_visibility(self, selector: str, timeout: int = 10) -> bool:
        """
        특정 요소가 보일 때까지 대기합니다.
        
        Args:
            selector: CSS 선택자
            timeout: 최대 대기 시간 (초)
            
        Returns:
            bool: 요소 가시성 확인 여부
        """
        try:
            self.logger.debug(f"⏳ 요소 가시성 대기: {selector}")
            
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            self.logger.debug(f"✅ 요소 가시성 확인: {selector}")
            return True
            
        except TimeoutException:
            self.logger.debug(f"⚠️ 요소 가시성 대기 타임아웃: {selector}")
            return False
        except Exception as e:
            self.logger.debug(f"❌ 요소 가시성 대기 중 오류: {selector}, {e}")
            return False
    
    def check_dynamic_content_loaded(self) -> bool:
        """
        동적 콘텐츠가 로드되었는지 확인합니다.
        
        Returns:
            bool: 동적 콘텐츠 로드 완료 여부
        """
        try:
            # SmartEditor 관련 요소들이 로드되었는지 확인
            smart_editor_loaded = self.driver.execute_script("""
                // SmartEditor 3.0 확인
                var se3 = document.querySelector('.se-main-container');
                if (se3) {
                    var textElements = se3.querySelectorAll('.se-module-text, .se-text-paragraph');
                    return textElements.length > 0;
                }
                
                // SmartEditor 2.0 확인
                var se2 = document.querySelector('.ContentRenderer, #postViewArea');
                if (se2) {
                    return se2.innerHTML.length > 100;
                }
                
                // 일반 에디터 확인
                var general = document.querySelector('#content-area, #tbody');
                if (general) {
                    return general.innerHTML.length > 100;
                }
                
                return false;
            """)
            
            if smart_editor_loaded:
                self.logger.debug("✅ 동적 콘텐츠 로드 확인됨")
                return True
            else:
                self.logger.debug("⚠️ 동적 콘텐츠 로드 미확인")
                return False
                
        except Exception as e:
            self.logger.debug(f"❌ 동적 콘텐츠 로드 확인 중 오류: {e}")
            return False
    
    def enhanced_wait_for_content(self, max_attempts: int = 3) -> bool:
        """
        향상된 콘텐츠 로딩 대기 (여러 단계 검증)
        
        Args:
            max_attempts: 최대 시도 횟수
            
        Returns:
            bool: 콘텐츠 로딩 완료 여부
        """
        for attempt in range(max_attempts):
            self.logger.info(f"🔄 향상된 콘텐츠 로딩 대기 시도 {attempt + 1}/{max_attempts}")
            
            # 기본 로딩 대기
            if not self.wait_for_complete_loading():
                continue
            
            # Lazy loading 활성화
            if self.config.enable_lazy_loading_trigger:
                self.trigger_lazy_loading()
            
            # 동적 콘텐츠 로드 확인
            if self.check_dynamic_content_loaded():
                self.logger.info("✅ 향상된 콘텐츠 로딩 대기 성공")
                return True
            
            # 실패 시 추가 대기
            if attempt < max_attempts - 1:
                self.logger.info(f"⏳ 시도 {attempt + 1} 실패, 추가 대기 후 재시도")
                time.sleep(2)
        
        self.logger.warning("⚠️ 향상된 콘텐츠 로딩 대기 최종 실패")
        return False
    
    def wait_for_ajax_complete(self, timeout: int = 10) -> bool:
        """
        AJAX 요청 완료 대기
        
        Args:
            timeout: 최대 대기 시간 (초)
            
        Returns:
            bool: AJAX 완료 여부
        """
        try:
            self.logger.debug("⏳ AJAX 요청 완료 대기")
            
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("""
                    // jQuery AJAX 확인
                    if (typeof jQuery !== 'undefined' && jQuery.active !== undefined) {
                        if (jQuery.active > 0) return false;
                    }
                    
                    // XMLHttpRequest 확인 (간단한 방법)
                    if (typeof window.activeXHRs !== 'undefined') {
                        return window.activeXHRs === 0;
                    }
                    
                    // Fetch API 확인은 복잡하므로 기본적으로 통과
                    return true;
                """)
            )
            
            self.logger.debug("✅ AJAX 요청 완료 확인")
            return True
            
        except TimeoutException:
            self.logger.debug("⚠️ AJAX 완료 대기 타임아웃")
            return False
        except Exception as e:
            self.logger.debug(f"❌ AJAX 완료 대기 중 오류: {e}")
            return False
    
    def wait_for_specific_elements(self, selectors: List[str], timeout: int = 10) -> Dict[str, bool]:
        """
        특정 요소들의 로딩 완료 대기
        
        Args:
            selectors: 대기할 CSS 선택자 목록
            timeout: 각 선택자별 최대 대기 시간 (초)
            
        Returns:
            Dict[str, bool]: 각 선택자별 로딩 완료 여부
        """
        results = {}
        
        for selector in selectors:
            try:
                self.logger.debug(f"⏳ 요소 로딩 대기: {selector}")
                
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                results[selector] = True
                self.logger.debug(f"✅ 요소 로딩 완료: {selector}")
                
            except TimeoutException:
                results[selector] = False
                self.logger.debug(f"⚠️ 요소 로딩 타임아웃: {selector}")
            except Exception as e:
                results[selector] = False
                self.logger.debug(f"❌ 요소 로딩 대기 중 오류: {selector}, {e}")
        
        return results
    
    def get_loading_performance_metrics(self) -> Dict[str, Any]:
        """
        페이지 로딩 성능 메트릭 수집
        
        Returns:
            Dict[str, Any]: 성능 메트릭 정보
        """
        try:
            metrics = self.driver.execute_script("""
                if (typeof window.performance === 'undefined' || !window.performance.timing) {
                    return null;
                }
                
                var timing = window.performance.timing;
                var navigation = window.performance.navigation;
                
                return {
                    // 기본 타이밍 정보
                    navigationStart: timing.navigationStart,
                    domainLookupStart: timing.domainLookupStart,
                    domainLookupEnd: timing.domainLookupEnd,
                    connectStart: timing.connectStart,
                    connectEnd: timing.connectEnd,
                    requestStart: timing.requestStart,
                    responseStart: timing.responseStart,
                    responseEnd: timing.responseEnd,
                    domLoading: timing.domLoading,
                    domInteractive: timing.domInteractive,
                    domContentLoadedEventStart: timing.domContentLoadedEventStart,
                    domContentLoadedEventEnd: timing.domContentLoadedEventEnd,
                    domComplete: timing.domComplete,
                    loadEventStart: timing.loadEventStart,
                    loadEventEnd: timing.loadEventEnd,
                    
                    // 계산된 메트릭
                    totalLoadTime: timing.loadEventEnd - timing.navigationStart,
                    domReadyTime: timing.domContentLoadedEventEnd - timing.navigationStart,
                    firstByteTime: timing.responseStart - timing.requestStart,
                    
                    // 네비게이션 타입
                    navigationType: navigation.type,
                    redirectCount: navigation.redirectCount
                };
            """)
            
            if metrics:
                # 시간을 밀리초에서 초로 변환
                for key in ['totalLoadTime', 'domReadyTime', 'firstByteTime']:
                    if metrics.get(key):
                        metrics[f"{key}_seconds"] = metrics[key] / 1000
                
                self.logger.debug(f"📊 로딩 성능 메트릭 수집 완료: {metrics.get('totalLoadTime_seconds', 0):.2f}초")
            
            return metrics or {}
            
        except Exception as e:
            self.logger.debug(f"❌ 성능 메트릭 수집 중 오류: {e}")
            return {}
    
    def adaptive_wait_strategy(self, url: str = None) -> bool:
        """
        적응형 대기 전략 (URL이나 페이지 특성에 따라 대기 방식 조정)
        
        Args:
            url: 현재 페이지 URL (분석용)
            
        Returns:
            bool: 적응형 대기 성공 여부
        """
        try:
            current_url = url or self.driver.current_url
            self.logger.info(f"🧠 적응형 대기 전략 시작: {current_url}")
            
            # URL 패턴 분석
            is_cafe_article = 'cafe.naver.com' in current_url and ('articles' in current_url or 'ArticleRead' in current_url)
            is_mobile = 'm.cafe.naver.com' in current_url
            
            # 기본 대기 시간 조정
            base_timeout = self.config.timeout_seconds
            if is_mobile:
                base_timeout = int(base_timeout * 1.5)  # 모바일은 50% 더 대기
                self.logger.debug("📱 모바일 페이지 감지: 대기 시간 증가")
            
            # 1단계: 기본 로딩 대기
            if not self.wait_for_complete_loading(timeout=base_timeout):
                return False
            
            # 2단계: 카페 게시물 특화 처리
            if is_cafe_article:
                self.logger.debug("📄 카페 게시물 페이지 감지: 특화 처리 시작")
                
                # SmartEditor 요소 대기
                editor_selectors = [
                    '.se-main-container',
                    '.ContentRenderer',
                    '#postViewArea',
                    '#content-area',
                    '#tbody'
                ]
                
                editor_results = self.wait_for_specific_elements(editor_selectors, timeout=10)
                detected_editors = [sel for sel, found in editor_results.items() if found]
                
                if detected_editors:
                    self.logger.debug(f"✅ 에디터 감지: {detected_editors}")
                    
                    # 감지된 에디터에 따른 추가 대기
                    if '.se-main-container' in detected_editors:
                        time.sleep(2)  # SmartEditor 3.0 추가 대기
                    elif '.ContentRenderer' in detected_editors or '#postViewArea' in detected_editors:
                        time.sleep(1.5)  # SmartEditor 2.0 추가 대기
                
                # Lazy loading 활성화
                if self.config.enable_lazy_loading_trigger:
                    self.trigger_lazy_loading()
            
            # 3단계: AJAX 완료 대기
            self.wait_for_ajax_complete(timeout=5)
            
            # 4단계: 최종 검증
            content_loaded = self.check_dynamic_content_loaded()
            
            if content_loaded:
                self.logger.info("✅ 적응형 대기 전략 성공")
                return True
            else:
                self.logger.warning("⚠️ 적응형 대기 전략 완료되었으나 콘텐츠 로딩 미확인")
                return True  # 부분 성공으로 처리
            
        except Exception as e:
            self.logger.error(f"❌ 적응형 대기 전략 중 오류: {e}")
            return False