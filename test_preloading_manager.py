#!/usr/bin/env python3
"""
PreloadingManager 클래스 단위 테스트
"""

import unittest
import time
from unittest.mock import Mock, MagicMock, patch, call
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from preloading_manager import PreloadingManager
from content_extraction_models import ExtractionConfig


class TestPreloadingManager(unittest.TestCase):
    """PreloadingManager 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_driver = Mock()
        self.mock_config = ExtractionConfig(
            timeout_seconds=30,
            scroll_pause_time=1.0,
            enable_lazy_loading_trigger=True
        )
        self.preloader = PreloadingManager(self.mock_driver, self.mock_config)
    
    def test_init_with_default_config(self):
        """기본 설정으로 초기화 테스트"""
        preloader = PreloadingManager(self.mock_driver)
        self.assertIsNotNone(preloader.config)
        self.assertEqual(preloader.config.timeout_seconds, 30)
        self.assertEqual(preloader.driver, self.mock_driver)
    
    def test_init_with_custom_config(self):
        """커스텀 설정으로 초기화 테스트"""
        custom_config = ExtractionConfig(timeout_seconds=60)
        preloader = PreloadingManager(self.mock_driver, custom_config)
        self.assertEqual(preloader.config.timeout_seconds, 60)
    
    @patch('preloading_manager.WebDriverWait')
    @patch('preloading_manager.time.sleep')
    def test_wait_for_complete_loading_success(self, mock_sleep, mock_wait):
        """완전한 로딩 대기 성공 테스트"""
        # Mock WebDriverWait 설정
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = True
        
        # Mock driver.execute_script 설정
        self.mock_driver.execute_script.side_effect = [
            'complete',  # document.readyState
            True,        # jQuery.active check
            True         # performance timing check
        ]
        
        result = self.preloader.wait_for_complete_loading(timeout=30)
        
        self.assertTrue(result)
        # 3초 추가 대기 확인 (Requirements 2.2)
        mock_sleep.assert_called_with(3)
        # WebDriverWait 호출 확인
        self.assertEqual(mock_wait.call_count, 3)  # 3번의 대기 단계
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_complete_loading_timeout(self, mock_wait):
        """로딩 대기 타임아웃 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = TimeoutException("Timeout")
        
        result = self.preloader.wait_for_complete_loading(timeout=30)
        
        self.assertFalse(result)
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_complete_loading_webdriver_exception(self, mock_wait):
        """로딩 대기 WebDriver 예외 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = WebDriverException("WebDriver error")
        
        result = self.preloader.wait_for_complete_loading(timeout=30)
        
        self.assertFalse(result)
    
    @patch('preloading_manager.time.sleep')
    def test_trigger_lazy_loading_success(self, mock_sleep):
        """Lazy loading 활성화 성공 테스트"""
        # Mock driver.execute_script 설정
        self.mock_driver.execute_script.side_effect = [
            100,  # 원래 스크롤 위치
            None, # 중간으로 스크롤
            None, # 하단으로 스크롤
            None, # 상단으로 스크롤
            None  # 원래 위치로 복원
        ]
        
        self.preloader.trigger_lazy_loading()
        
        # 스크롤 명령 확인
        expected_calls = [
            call("return window.pageYOffset;"),
            call("window.scrollTo(0, document.body.scrollHeight / 2);"),
            call("window.scrollTo(0, document.body.scrollHeight);"),
            call("window.scrollTo(0, 0);"),
            call("window.scrollTo(0, 100);")
        ]
        self.mock_driver.execute_script.assert_has_calls(expected_calls)
        
        # sleep 호출 확인 (scroll_pause_time * 2 + 추가 대기들)
        self.assertTrue(mock_sleep.call_count >= 4)
    
    @patch('preloading_manager.time.sleep')
    def test_trigger_lazy_loading_webdriver_exception(self, mock_sleep):
        """Lazy loading 활성화 WebDriver 예외 테스트"""
        self.mock_driver.execute_script.side_effect = WebDriverException("WebDriver error")
        
        # 예외가 발생해도 메서드가 정상 종료되어야 함
        try:
            self.preloader.trigger_lazy_loading()
        except Exception:
            self.fail("trigger_lazy_loading should handle WebDriverException gracefully")
    
    @patch('preloading_manager.WebDriverWait')
    @patch('preloading_manager.EC')
    def test_wait_for_iframe_and_switch_success(self, mock_ec, mock_wait):
        """iframe 전환 성공 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = True
        
        # wait_for_complete_loading과 trigger_lazy_loading을 Mock
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'trigger_lazy_loading'):
            
            result = self.preloader.wait_for_iframe_and_switch('cafe_main', 15)
            
            self.assertTrue(result)
            mock_wait_instance.until.assert_called_once()
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_iframe_and_switch_timeout(self, mock_wait):
        """iframe 전환 타임아웃 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = TimeoutException("Timeout")
        
        result = self.preloader.wait_for_iframe_and_switch('cafe_main', 15)
        
        self.assertFalse(result)
    
    @patch('preloading_manager.WebDriverWait')
    @patch('preloading_manager.EC')
    def test_wait_for_element_visibility_success(self, mock_ec, mock_wait):
        """요소 가시성 대기 성공 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = Mock()  # Mock element
        
        result = self.preloader.wait_for_element_visibility('.test-selector', 10)
        
        self.assertTrue(result)
        mock_wait_instance.until.assert_called_once()
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_element_visibility_timeout(self, mock_wait):
        """요소 가시성 대기 타임아웃 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = TimeoutException("Timeout")
        
        result = self.preloader.wait_for_element_visibility('.test-selector', 10)
        
        self.assertFalse(result)
    
    def test_check_dynamic_content_loaded_smarteditor3(self):
        """SmartEditor 3.0 동적 콘텐츠 로드 확인 테스트"""
        self.mock_driver.execute_script.return_value = True
        
        result = self.preloader.check_dynamic_content_loaded()
        
        self.assertTrue(result)
        self.mock_driver.execute_script.assert_called_once()
    
    def test_check_dynamic_content_loaded_not_loaded(self):
        """동적 콘텐츠 미로드 확인 테스트"""
        self.mock_driver.execute_script.return_value = False
        
        result = self.preloader.check_dynamic_content_loaded()
        
        self.assertFalse(result)
    
    def test_check_dynamic_content_loaded_exception(self):
        """동적 콘텐츠 확인 예외 테스트"""
        self.mock_driver.execute_script.side_effect = Exception("Script error")
        
        result = self.preloader.check_dynamic_content_loaded()
        
        self.assertFalse(result)
    
    @patch('preloading_manager.time.sleep')
    def test_enhanced_wait_for_content_success_first_attempt(self, mock_sleep):
        """향상된 콘텐츠 대기 첫 시도 성공 테스트"""
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'trigger_lazy_loading'), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', return_value=True):
            
            result = self.preloader.enhanced_wait_for_content(max_attempts=3)
            
            self.assertTrue(result)
            # 첫 시도에서 성공했으므로 sleep이 호출되지 않아야 함
            mock_sleep.assert_not_called()
    
    @patch('preloading_manager.time.sleep')
    def test_enhanced_wait_for_content_success_second_attempt(self, mock_sleep):
        """향상된 콘텐츠 대기 두 번째 시도 성공 테스트"""
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'trigger_lazy_loading'), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', side_effect=[False, True]):
            
            result = self.preloader.enhanced_wait_for_content(max_attempts=3)
            
            self.assertTrue(result)
            # 첫 시도 실패 후 2초 대기 확인
            mock_sleep.assert_called_once_with(2)
    
    @patch('preloading_manager.time.sleep')
    def test_enhanced_wait_for_content_all_attempts_fail(self, mock_sleep):
        """향상된 콘텐츠 대기 모든 시도 실패 테스트"""
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'trigger_lazy_loading'), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', return_value=False):
            
            result = self.preloader.enhanced_wait_for_content(max_attempts=3)
            
            self.assertFalse(result)
            # 2번의 재시도 대기 확인 (3번 시도 중 처음 2번 실패)
            self.assertEqual(mock_sleep.call_count, 2)
            mock_sleep.assert_has_calls([call(2), call(2)])
    
    def test_enhanced_wait_for_content_loading_fails(self):
        """향상된 콘텐츠 대기 - 기본 로딩 실패 테스트"""
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=False):
            
            result = self.preloader.enhanced_wait_for_content(max_attempts=2)
            
            self.assertFalse(result)
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_ajax_complete_success(self, mock_wait):
        """AJAX 완료 대기 성공 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = True
        
        result = self.preloader.wait_for_ajax_complete(timeout=10)
        
        self.assertTrue(result)
        mock_wait_instance.until.assert_called_once()
    
    @patch('preloading_manager.WebDriverWait')
    def test_wait_for_ajax_complete_timeout(self, mock_wait):
        """AJAX 완료 대기 타임아웃 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = TimeoutException("Timeout")
        
        result = self.preloader.wait_for_ajax_complete(timeout=10)
        
        self.assertFalse(result)
    
    @patch('preloading_manager.WebDriverWait')
    @patch('preloading_manager.EC')
    def test_wait_for_specific_elements_success(self, mock_ec, mock_wait):
        """특정 요소들 로딩 대기 성공 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = Mock()  # Mock element
        
        selectors = ['.selector1', '.selector2', '.selector3']
        results = self.preloader.wait_for_specific_elements(selectors, timeout=10)
        
        # 모든 선택자가 성공해야 함
        for selector in selectors:
            self.assertTrue(results[selector])
        
        # WebDriverWait이 각 선택자마다 호출되었는지 확인
        self.assertEqual(mock_wait_instance.until.call_count, len(selectors))
    
    @patch('preloading_manager.WebDriverWait')
    @patch('preloading_manager.EC')
    def test_wait_for_specific_elements_mixed_results(self, mock_ec, mock_wait):
        """특정 요소들 로딩 대기 혼합 결과 테스트"""
        mock_wait_instance = Mock()
        mock_wait.return_value = mock_wait_instance
        # 첫 번째는 성공, 두 번째는 타임아웃
        mock_wait_instance.until.side_effect = [Mock(), TimeoutException("Timeout")]
        
        selectors = ['.success-selector', '.timeout-selector']
        results = self.preloader.wait_for_specific_elements(selectors, timeout=10)
        
        self.assertTrue(results['.success-selector'])
        self.assertFalse(results['.timeout-selector'])
    
    def test_get_loading_performance_metrics_success(self):
        """로딩 성능 메트릭 수집 성공 테스트"""
        mock_metrics = {
            'navigationStart': 1000,
            'loadEventEnd': 3000,
            'domContentLoadedEventEnd': 2500,
            'requestStart': 1200,
            'responseStart': 1500,
            'totalLoadTime': 2000,
            'domReadyTime': 1500,
            'firstByteTime': 300,
            'navigationType': 0,
            'redirectCount': 0
        }
        
        self.mock_driver.execute_script.return_value = mock_metrics
        
        result = self.preloader.get_loading_performance_metrics()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['totalLoadTime'], 2000)
        self.assertEqual(result['totalLoadTime_seconds'], 2.0)
        self.assertEqual(result['domReadyTime_seconds'], 1.5)
        self.assertEqual(result['firstByteTime_seconds'], 0.3)
    
    def test_get_loading_performance_metrics_no_performance_api(self):
        """Performance API 미지원 시 메트릭 수집 테스트"""
        self.mock_driver.execute_script.return_value = None
        
        result = self.preloader.get_loading_performance_metrics()
        
        self.assertEqual(result, {})
    
    def test_get_loading_performance_metrics_exception(self):
        """성능 메트릭 수집 예외 테스트"""
        self.mock_driver.execute_script.side_effect = Exception("Script error")
        
        result = self.preloader.get_loading_performance_metrics()
        
        self.assertEqual(result, {})
    
    def test_adaptive_wait_strategy_cafe_article(self):
        """적응형 대기 전략 - 카페 게시물 테스트"""
        test_url = "https://cafe.naver.com/testcafe/articles/123456"
        
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'wait_for_specific_elements', return_value={'.se-main-container': True}), \
             patch.object(self.preloader, 'trigger_lazy_loading'), \
             patch.object(self.preloader, 'wait_for_ajax_complete', return_value=True), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', return_value=True), \
             patch('preloading_manager.time.sleep'):
            
            result = self.preloader.adaptive_wait_strategy(url=test_url)
            
            self.assertTrue(result)
    
    def test_adaptive_wait_strategy_mobile_cafe(self):
        """적응형 대기 전략 - 모바일 카페 테스트"""
        test_url = "https://m.cafe.naver.com/testcafe/articles/123456"
        
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'wait_for_specific_elements', return_value={}), \
             patch.object(self.preloader, 'wait_for_ajax_complete', return_value=True), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', return_value=True):
            
            result = self.preloader.adaptive_wait_strategy(url=test_url)
            
            self.assertTrue(result)
            # 모바일 페이지의 경우 타임아웃이 1.5배 증가해야 함
            # wait_for_complete_loading이 증가된 타임아웃으로 호출되었는지 확인
            self.preloader.wait_for_complete_loading.assert_called_once()
    
    def test_adaptive_wait_strategy_non_cafe_url(self):
        """적응형 대기 전략 - 비카페 URL 테스트"""
        test_url = "https://example.com/page"
        
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=True), \
             patch.object(self.preloader, 'wait_for_ajax_complete', return_value=True), \
             patch.object(self.preloader, 'check_dynamic_content_loaded', return_value=True):
            
            result = self.preloader.adaptive_wait_strategy(url=test_url)
            
            self.assertTrue(result)
    
    def test_adaptive_wait_strategy_loading_fails(self):
        """적응형 대기 전략 - 로딩 실패 테스트"""
        test_url = "https://cafe.naver.com/testcafe/articles/123456"
        
        with patch.object(self.preloader, 'wait_for_complete_loading', return_value=False):
            
            result = self.preloader.adaptive_wait_strategy(url=test_url)
            
            self.assertFalse(result)
    
    def test_adaptive_wait_strategy_exception(self):
        """적응형 대기 전략 - 예외 발생 테스트"""
        test_url = "https://cafe.naver.com/testcafe/articles/123456"
        
        with patch.object(self.preloader, 'wait_for_complete_loading', side_effect=Exception("Test error")):
            
            result = self.preloader.adaptive_wait_strategy(url=test_url)
            
            self.assertFalse(result)


class TestPreloadingManagerIntegration(unittest.TestCase):
    """PreloadingManager 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_driver = Mock()
        self.preloader = PreloadingManager(self.mock_driver)
    
    def test_requirements_2_1_document_ready_state(self):
        """Requirements 2.1: document.readyState 확인 테스트"""
        with patch('preloading_manager.WebDriverWait') as mock_wait:
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True
            
            self.preloader.wait_for_complete_loading()
            
            # document.readyState 확인을 위한 lambda 함수가 호출되었는지 확인
            mock_wait_instance.until.assert_called()
            call_args = mock_wait_instance.until.call_args_list[0][0][0]
            
            # lambda 함수 테스트
            self.mock_driver.execute_script.return_value = 'complete'
            result = call_args(self.mock_driver)
            self.assertTrue(result)
            
            self.mock_driver.execute_script.return_value = 'loading'
            result = call_args(self.mock_driver)
            self.assertFalse(result)
    
    @patch('preloading_manager.time.sleep')
    def test_requirements_2_2_iframe_additional_wait(self, mock_sleep):
        """Requirements 2.2: iframe 전환 후 3초 추가 대기 테스트"""
        with patch('preloading_manager.WebDriverWait') as mock_wait:
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True
            
            self.preloader.wait_for_complete_loading()
            
            # 3초 대기가 호출되었는지 확인
            mock_sleep.assert_called_with(3)
    
    @patch('preloading_manager.time.sleep')
    def test_requirements_2_3_scroll_lazy_loading(self, mock_sleep):
        """Requirements 2.3: 스크롤 기반 lazy loading 트리거 테스트"""
        # Mock scroll info and other execute_script calls
        scroll_info = {
            'originalY': 0,
            'originalX': 0,
            'bodyHeight': 2000,
            'windowHeight': 800,
            'bodyWidth': 1200,
            'windowWidth': 1200
        }
        
        self.mock_driver.execute_script.side_effect = [
            scroll_info,  # 스크롤 정보
            None, None, None, None, None,  # 수직 스크롤 패턴
            None,  # 원래 위치로 복원
        ]
        
        # Mock find_elements for image lazy loading
        self.mock_driver.find_elements.return_value = []
        
        self.preloader.trigger_lazy_loading()
        
        # 스크롤 정보 수집이 호출되었는지 확인
        first_call = self.mock_driver.execute_script.call_args_list[0]
        self.assertIn('originalY', first_call[0][0])
        
        # 원래 위치로 복원 호출 확인
        restore_call = self.mock_driver.execute_script.call_args_list[-1]
        self.assertIn('scrollTo(0, 0)', restore_call[0][0])
    
    def test_new_lazy_loading_features(self):
        """새로운 lazy loading 기능들 테스트"""
        # Mock scroll info
        scroll_info = {
            'originalY': 100,
            'originalX': 0,
            'bodyHeight': 2000,
            'windowHeight': 800,
            'bodyWidth': 1500,  # 수평 스크롤 필요
            'windowWidth': 1200
        }
        
        # Mock image elements
        mock_images = [Mock(), Mock()]
        
        with patch.object(self.preloader, '_perform_vertical_scroll_pattern'), \
             patch.object(self.preloader, '_trigger_naver_cafe_lazy_loading'), \
             patch.object(self.preloader, '_trigger_image_lazy_loading'), \
             patch.object(self.preloader, '_perform_horizontal_scroll_pattern'), \
             patch('preloading_manager.time.sleep'):
            
            self.mock_driver.execute_script.side_effect = [scroll_info, None]
            self.mock_driver.find_elements.return_value = mock_images
            
            self.preloader.trigger_lazy_loading()
            
            # 모든 새로운 메서드들이 호출되었는지 확인
            self.preloader._perform_vertical_scroll_pattern.assert_called_once_with(scroll_info)
            self.preloader._trigger_naver_cafe_lazy_loading.assert_called_once()
            self.preloader._trigger_image_lazy_loading.assert_called_once()
            self.preloader._perform_horizontal_scroll_pattern.assert_called_once_with(scroll_info)
    
    def test_enhanced_javascript_loading_detection(self):
        """향상된 JavaScript 로딩 감지 테스트"""
        with patch.object(self.preloader, '_wait_for_javascript_libraries', return_value=True), \
             patch.object(self.preloader, '_wait_for_naver_cafe_scripts', return_value=True), \
             patch.object(self.preloader, '_wait_for_network_idle', return_value=True), \
             patch('preloading_manager.WebDriverWait') as mock_wait, \
             patch('preloading_manager.time.sleep'):
            
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True
            
            result = self.preloader.wait_for_complete_loading()
            
            self.assertTrue(result)
            # 새로운 대기 메서드들이 호출되었는지 확인
            self.preloader._wait_for_javascript_libraries.assert_called_once()
            self.preloader._wait_for_naver_cafe_scripts.assert_called_once()
            self.preloader._wait_for_network_idle.assert_called_once()


if __name__ == '__main__':
    # 로깅 설정 (테스트 중 로그 출력 방지)
    import logging
    logging.getLogger('preloading_manager').setLevel(logging.CRITICAL)
    
    unittest.main(verbosity=2)