#!/usr/bin/env python3
"""
네이버 카페 콘텐츠 추출을 위한 메인 ContentExtractor 클래스
모든 컴포넌트를 통합하여 강화된 콘텐츠 추출 기능을 제공합니다.
"""

import time
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from content_extraction_models import (
    ContentResult, 
    ExtractionMethod, 
    ExtractionConfig,
    ContentExtractorInterface,
    DebugInfo
)
from preloading_manager import PreloadingManager
from selector_strategies import SelectorStrategyManager
from content_validator import ContentValidator


class DebugCollector:
    """디버깅 정보 수집 클래스 (GitHub Actions 환경 고려)"""
    
    def __init__(self, driver: webdriver.Chrome, is_github_actions: bool = False):
        self.driver = driver
        self.is_github_actions = is_github_actions
        self.logger = logging.getLogger(__name__)
        
        # GitHub Actions 환경에서는 artifacts 디렉토리 사용
        self.screenshot_dir = "artifacts" if is_github_actions else "debug_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def collect_page_info(self, url: str) -> DebugInfo:
        """페이지 상태 정보를 수집합니다."""
        try:
            debug_info = DebugInfo(
                url=url,
                page_ready_state="unknown",
                body_html_length=0,
                editor_type_detected=None,
                selector_attempts=[],
                timestamp=datetime.now().isoformat()
            )
            
            # 페이지 상태 정보 수집
            page_info = self.driver.execute_script("""
                return {
                    'readyState': document.readyState,
                    'bodyLength': document.body ? document.body.innerHTML.length : 0,
                    'hasSmartEditor3': !!document.querySelector('.se-main-container'),
                    'hasSmartEditor2': !!document.querySelector('.ContentRenderer, #postViewArea'),
                    'hasGeneralEditor': !!document.querySelector('#content-area'),
                    'hasLegacyEditor': !!document.querySelector('#tbody'),
                    'url': window.location.href
                };
            """)
            
            debug_info.page_ready_state = page_info.get('readyState', 'unknown')
            debug_info.body_html_length = page_info.get('bodyLength', 0)
            
            # 에디터 타입 감지
            if page_info.get('hasSmartEditor3'):
                debug_info.editor_type_detected = "SmartEditor 3.0"
            elif page_info.get('hasSmartEditor2'):
                debug_info.editor_type_detected = "SmartEditor 2.0"
            elif page_info.get('hasGeneralEditor'):
                debug_info.editor_type_detected = "일반 에디터"
            elif page_info.get('hasLegacyEditor'):
                debug_info.editor_type_detected = "레거시 에디터"
            
            return debug_info
            
        except Exception as e:
            self.logger.error(f"❌ 페이지 정보 수집 실패: {e}")
            return DebugInfo(
                url=url,
                page_ready_state="error",
                body_html_length=0,
                editor_type_detected=None,
                selector_attempts=[],
                timestamp=datetime.now().isoformat()
            )
    
    def save_debug_screenshot(self, url: str, filename_prefix: str = "debug") -> Optional[str]:
        """디버깅용 스크린샷을 저장합니다."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            self.driver.save_screenshot(filepath)
            self.logger.info(f"📷 디버깅 스크린샷 저장: {filepath}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ 스크린샷 저장 실패: {e}")
            return None


class FallbackExtractor:
    """최후 수단 추출기"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = logging.getLogger(__name__)
    
    def extract_with_dom_traversal(self) -> Optional[str]:
        """DOM 트리 순회를 통해 텍스트를 추출합니다."""
        try:
            self.logger.info("🔧 DOM 트리 순회를 통한 최후 수단 추출 시도")
            
            content = self.driver.execute_script("""
                var allText = [];
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    function(node) {
                        // 스크립트, 스타일 태그 내용 제외
                        var parent = node.parentElement;
                        if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE')) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        
                        // 숨겨진 요소 제외
                        if (parent) {
                            var style = window.getComputedStyle(parent);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                return NodeFilter.FILTER_REJECT;
                            }
                        }
                        
                        return NodeFilter.FILTER_ACCEPT;
                    },
                    false
                );
                
                var node;
                while (node = walker.nextNode()) {
                    var text = node.nodeValue.trim();
                    if (text && text.length > 10) {
                        allText.push(text);
                    }
                }
                
                return allText.join(' ');
            """)
            
            if content and len(content.strip()) > 50:
                self.logger.info(f"✅ DOM 트리 순회 추출 성공: {len(content)}자")
                return content.strip()
            
        except Exception as e:
            self.logger.error(f"❌ DOM 트리 순회 추출 실패: {e}")
        
        return None
    
    def extract_with_refresh_retry(self, url: str) -> Optional[str]:
        """페이지 새로고침 후 재시도하여 콘텐츠를 추출합니다."""
        try:
            self.logger.info("🔄 페이지 새로고침 후 재시도")
            
            # 페이지 새로고침
            self.driver.refresh()
            time.sleep(5)
            
            # iframe 재진입 시도
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.NAME, 'cafe_main'))
                )
                time.sleep(3)
            except:
                self.logger.warning("iframe 재진입 실패")
            
            # DOM 트리 순회로 재시도
            return self.extract_with_dom_traversal()
            
        except Exception as e:
            self.logger.error(f"❌ 새로고침 후 재시도 실패: {e}")
            return None


class ContentExtractor(ContentExtractorInterface):
    """
    네이버 카페 콘텐츠 추출을 위한 메인 클래스
    모든 컴포넌트를 통합하여 강화된 추출 기능을 제공합니다.
    """
    
    def __init__(self, driver: webdriver.Chrome, wait: WebDriverWait, 
                 config: Optional[ExtractionConfig] = None):
        """
        ContentExtractor 초기화
        
        Args:
            driver: Selenium WebDriver 인스턴스
            wait: WebDriverWait 인스턴스
            config: 추출 설정
        """
        self.driver = driver
        self.wait = wait
        self.config = config or ExtractionConfig()
        self.logger = logging.getLogger(__name__)
        
        # GitHub Actions 환경 감지
        self.is_github_actions = os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
        
        # 컴포넌트 초기화
        self.preloader = PreloadingManager(driver, config)
        self.selector_strategy = SelectorStrategyManager()
        self.validator = ContentValidator(config)
        self.debug_collector = DebugCollector(driver, self.is_github_actions)
        self.fallback = FallbackExtractor(driver)
        
        self.logger.info(f"🚀 ContentExtractor 초기화 완료 (GitHub Actions: {self.is_github_actions})")
    
    def extract_content(self, url: str) -> ContentResult:
        """
        주어진 URL에서 콘텐츠를 추출합니다.
        
        Args:
            url: 추출할 게시물의 URL
            
        Returns:
            ContentResult: 추출 결과
        """
        start_time = time.time()
        original_window = self.driver.current_window_handle
        
        try:
            self.logger.info(f"📖 콘텐츠 추출 시작: {url}")
            
            # 디버깅 정보 수집 시작
            debug_info = self.debug_collector.collect_page_info(url)
            
            # 새 탭에서 열기
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 1단계: 페이지 로딩 대기
            if not self.preloader.wait_for_complete_loading(self.config.timeout_seconds):
                self.logger.warning("⚠️ 페이지 로딩 대기 타임아웃")
            
            # 2단계: iframe 전환 및 추가 로딩 대기
            if not self.preloader.wait_for_iframe_and_switch():
                self.logger.warning("⚠️ iframe 전환 실패")
                # iframe 전환 실패해도 계속 진행
            
            # 3단계: 선택자 전략으로 콘텐츠 추출
            strategy_result = self.selector_strategy.extract_with_strategies(self.driver)
            
            if strategy_result and strategy_result['content']:
                content = strategy_result['content']
                extraction_method = strategy_result['extraction_method']
                
                # 디버깅 정보에 시도 결과 추가
                debug_info.selector_attempts = strategy_result['attempts']
                
                # 4단계: 콘텐츠 검증 및 정제
                validation_result = self.validator.validate_content(content)
                
                if validation_result.is_valid:
                    extraction_time = int((time.time() - start_time) * 1000)
                    
                    self.logger.info(f"✅ 콘텐츠 추출 성공: {len(validation_result.cleaned_content)}자 ({extraction_time}ms)")
                    
                    return ContentResult(
                        content=validation_result.cleaned_content,
                        extraction_method=extraction_method,
                        quality_score=validation_result.quality_score,
                        debug_info=debug_info.__dict__,
                        success=True,
                        extraction_time_ms=extraction_time
                    )
                else:
                    self.logger.warning(f"⚠️ 콘텐츠 검증 실패: {validation_result.issues}")
            
            # 5단계: 최후 수단 추출 시도
            self.logger.info("🔧 최후 수단 추출 시도")
            
            fallback_content = self.fallback.extract_with_dom_traversal()
            if not fallback_content:
                fallback_content = self.fallback.extract_with_refresh_retry(url)
            
            if fallback_content:
                validation_result = self.validator.validate_content(fallback_content)
                
                if validation_result.is_valid:
                    extraction_time = int((time.time() - start_time) * 1000)
                    
                    self.logger.info(f"✅ 최후 수단 추출 성공: {len(validation_result.cleaned_content)}자")
                    
                    return ContentResult(
                        content=validation_result.cleaned_content,
                        extraction_method=ExtractionMethod.FALLBACK,
                        quality_score=validation_result.quality_score,
                        debug_info=debug_info.__dict__,
                        success=True,
                        extraction_time_ms=extraction_time
                    )
            
            # 6단계: 완전 실패 시 디버깅 정보 저장
            if self.config.enable_debug_screenshot:
                screenshot_path = self.debug_collector.save_debug_screenshot(url, "extraction_failed")
                debug_info.screenshot_path = screenshot_path
            
            extraction_time = int((time.time() - start_time) * 1000)
            
            self.logger.error("❌ 모든 추출 방법 실패")
            
            return ContentResult(
                content=f"내용을 불러올 수 없습니다.\n원본 링크: {url}",
                extraction_method=ExtractionMethod.FALLBACK,
                quality_score=0.0,
                debug_info=debug_info.__dict__,
                success=False,
                error_message="모든 추출 방법 실패",
                extraction_time_ms=extraction_time
            )
            
        except Exception as e:
            extraction_time = int((time.time() - start_time) * 1000)
            
            self.logger.error(f"❌ 콘텐츠 추출 중 심각한 오류: {e}")
            
            # 오류 시에도 디버깅 스크린샷 저장
            if self.config.enable_debug_screenshot:
                try:
                    screenshot_path = self.debug_collector.save_debug_screenshot(url, "extraction_error")
                    debug_info.screenshot_path = screenshot_path
                except:
                    pass
            
            return ContentResult(
                content=f"내용을 불러올 수 없습니다.\n원본 링크: {url}",
                extraction_method=ExtractionMethod.FALLBACK,
                quality_score=0.0,
                debug_info=debug_info.__dict__ if 'debug_info' in locals() else {},
                success=False,
                error_message=str(e),
                extraction_time_ms=extraction_time
            )
            
        finally:
            # 탭 닫고 원래 창으로 복귀
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except:
                pass
    
    def extract_content_simple(self, url: str) -> str:
        """
        간단한 인터페이스로 콘텐츠를 추출합니다 (기존 코드와의 호환성을 위해)
        
        Args:
            url: 추출할 게시물의 URL
            
        Returns:
            str: 추출된 콘텐츠
        """
        result = self.extract_content(url)
        return result.content
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        추출 통계 정보를 반환합니다.
        
        Returns:
            Dict: 통계 정보
        """
        return {
            'config': self.config.__dict__,
            'is_github_actions': self.is_github_actions,
            'available_strategies': self.selector_strategy.get_all_strategy_names()
        }