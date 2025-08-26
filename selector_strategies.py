#!/usr/bin/env python3
"""
네이버 카페 콘텐츠 추출을 위한 SelectorStrategy 패턴 구현
다양한 에디터 형식에 대응하는 선택자 전략들을 정의합니다.
"""

import time
import logging
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from content_extraction_models import (
    SelectorStrategyInterface, 
    SelectorAttempt, 
    ExtractionMethod
)


class SelectorStrategy(SelectorStrategyInterface):
    """기본 SelectorStrategy 클래스 - 추상 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_selectors(self) -> List[str]:
        """해당 전략의 선택자 목록을 반환합니다."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """전략 이름을 반환합니다."""
        pass
    
    @abstractmethod
    def get_extraction_method(self) -> ExtractionMethod:
        """해당 전략의 추출 방법을 반환합니다."""
        pass
    
    def extract_with_selectors(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        선택자를 사용하여 콘텐츠를 추출합니다.
        
        Args:
            driver: Selenium WebDriver 인스턴스
            
        Returns:
            Optional[str]: 추출된 콘텐츠 (실패 시 None)
        """
        selectors = self.get_selectors()
        strategy_name = self.get_strategy_name()
        
        self.logger.info(f"🔍 {strategy_name} 전략으로 콘텐츠 추출 시도")
        
        for selector in selectors:
            try:
                start_time = time.time()
                
                # 요소 존재 확인
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if not elements:
                    self.logger.debug(f"  - 선택자 '{selector}': 요소 없음")
                    continue
                
                element = elements[0]
                
                # 요소가 보일 때까지 대기 (최대 5초)
                try:
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of(element)
                    )
                except TimeoutException:
                    self.logger.debug(f"  - 선택자 '{selector}': 요소가 보이지 않음")
                    # 보이지 않아도 텍스트 추출 시도
                    pass
                
                # 다양한 방법으로 텍스트 추출 시도
                content = self._extract_text_from_element(element, driver)
                
                extraction_time = int((time.time() - start_time) * 1000)
                
                if content and len(content.strip()) > 20:
                    # 유효한 콘텐츠 발견
                    cleaned_content = self._basic_content_cleaning(content)
                    
                    if self._is_valid_content(cleaned_content):
                        self.logger.info(f"  ✅ 선택자 '{selector}'로 콘텐츠 추출 성공: {len(cleaned_content)}자 ({extraction_time}ms)")
                        return cleaned_content
                    else:
                        self.logger.debug(f"  - 선택자 '{selector}': 콘텐츠 품질 부족")
                else:
                    self.logger.debug(f"  - 선택자 '{selector}': 콘텐츠 길이 부족 ({len(content) if content else 0}자)")
                
            except StaleElementReferenceException:
                self.logger.debug(f"  - 선택자 '{selector}': 요소 참조 오류 (페이지 변경됨)")
                continue
            except NoSuchElementException:
                self.logger.debug(f"  - 선택자 '{selector}': 요소 없음")
                continue
            except Exception as e:
                self.logger.debug(f"  - 선택자 '{selector}': 예외 발생 - {e}")
                continue
        
        self.logger.warning(f"⚠️ {strategy_name} 전략으로 콘텐츠 추출 실패")
        return None
    
    def _extract_text_from_element(self, element, driver: webdriver.Chrome) -> str:
        """요소에서 텍스트를 추출하는 다양한 방법을 시도합니다."""
        methods = [
            lambda: element.text.strip(),
            lambda: element.get_attribute('innerText') or '',
            lambda: element.get_attribute('textContent') or '',
            lambda: driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", element)
        ]
        
        for method in methods:
            try:
                text = method()
                if text and text.strip():
                    return text.strip()
            except Exception:
                continue
        
        return ""
    
    def _basic_content_cleaning(self, content: str) -> str:
        """기본적인 콘텐츠 정제를 수행합니다."""
        if not content:
            return ""
        
        # 불필요한 텍스트 패턴 제거
        remove_patterns = [
            '로그인', '메뉴', '목록', '이전글', '다음글', '카페앱으로 보기',
            'JavaScript', '댓글', '스크랩', '신고', '좋아요', '답글',
            "doesn't work properly", "내용을 불러올 수 없습니다"
        ]
        
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # 너무 짧은 라인 제거
                # 불필요한 패턴이 포함되지 않은 라인만 유지
                if not any(pattern in line for pattern in remove_patterns):
                    filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _is_valid_content(self, content: str) -> bool:
        """콘텐츠가 유효한지 검증합니다."""
        if not content or len(content.strip()) < 30:
            return False
        
        # 의미 없는 콘텐츠 패턴 체크
        invalid_patterns = [
            "내용을 불러올 수 없습니다",
            "JavaScript를 활성화",
            "로그인이 필요합니다",
            "접근 권한이 없습니다"
        ]
        
        for pattern in invalid_patterns:
            if pattern in content:
                return False
        
        return True


class SmartEditor3Strategy(SelectorStrategy):
    """SmartEditor 3.0 전용 선택자 전략"""
    
    def get_selectors(self) -> List[str]:
        """SmartEditor 3.0 관련 선택자들을 우선순위 순으로 반환"""
        return [
            '.se-main-container',
            '.se-component-content',
            'div.se-module-text',
            '.se-text-paragraph',
            '.se-section-text',
            '.se-viewer',
            '.se-content'
        ]
    
    def get_strategy_name(self) -> str:
        return "SmartEditor 3.0"
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.SMART_EDITOR_3
    
    def extract_with_selectors(self, driver: webdriver.Chrome) -> Optional[str]:
        """SmartEditor 3.0 특화 추출 로직"""
        # 기본 추출 시도
        content = super().extract_with_selectors(driver)
        if content:
            return content
        
        # SmartEditor 3.0 특화 JavaScript 추출
        try:
            self.logger.info("🔧 SmartEditor 3.0 JavaScript 특화 추출 시도")
            
            js_content = driver.execute_script("""
                // SmartEditor 3.0 전용 추출 로직
                var se3Container = document.querySelector('.se-main-container');
                if (se3Container) {
                    var texts = [];
                    
                    // 모든 텍스트 관련 요소 수집
                    var textElements = se3Container.querySelectorAll(
                        '.se-module-text, .se-text-paragraph, .se-section-text, p, span, div'
                    );
                    
                    textElements.forEach(function(el) {
                        var style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            var text = (el.innerText || el.textContent || '').trim();
                            if (text && text.length > 10) {
                                texts.push(text);
                            }
                        }
                    });
                    
                    if (texts.length > 0) {
                        return texts.join('\\n');
                    }
                }
                
                return '';
            """)
            
            if js_content and len(js_content.strip()) > 30:
                cleaned_content = self._basic_content_cleaning(js_content)
                if self._is_valid_content(cleaned_content):
                    self.logger.info(f"  ✅ SmartEditor 3.0 JavaScript 추출 성공: {len(cleaned_content)}자")
                    return cleaned_content
            
        except Exception as e:
            self.logger.debug(f"SmartEditor 3.0 JavaScript 추출 실패: {e}")
        
        return None


class SmartEditor2Strategy(SelectorStrategy):
    """SmartEditor 2.0 전용 선택자 전략"""
    
    def get_selectors(self) -> List[str]:
        """SmartEditor 2.0 관련 선택자들을 우선순위 순으로 반환"""
        return [
            '.ContentRenderer',
            '#postViewArea',
            '.NHN_Writeform_Main',
            '.post-view',
            '.post_ct',
            '.view-content',
            '.article-content'
        ]
    
    def get_strategy_name(self) -> str:
        return "SmartEditor 2.0"
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.SMART_EDITOR_2
    
    def extract_with_selectors(self, driver: webdriver.Chrome) -> Optional[str]:
        """SmartEditor 2.0 특화 추출 로직"""
        # 기본 추출 시도
        content = super().extract_with_selectors(driver)
        if content:
            return content
        
        # SmartEditor 2.0 특화 JavaScript 추출
        try:
            self.logger.info("🔧 SmartEditor 2.0 JavaScript 특화 추출 시도")
            
            js_content = driver.execute_script("""
                // SmartEditor 2.0 전용 추출 로직
                var selectors = ['.ContentRenderer', '#postViewArea', '.NHN_Writeform_Main'];
                
                for (var i = 0; i < selectors.length; i++) {
                    var container = document.querySelector(selectors[i]);
                    if (container) {
                        var style = window.getComputedStyle(container);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            var text = (container.innerText || container.textContent || '').trim();
                            if (text && text.length > 20) {
                                return text;
                            }
                        }
                    }
                }
                
                return '';
            """)
            
            if js_content and len(js_content.strip()) > 30:
                cleaned_content = self._basic_content_cleaning(js_content)
                if self._is_valid_content(cleaned_content):
                    self.logger.info(f"  ✅ SmartEditor 2.0 JavaScript 추출 성공: {len(cleaned_content)}자")
                    return cleaned_content
            
        except Exception as e:
            self.logger.debug(f"SmartEditor 2.0 JavaScript 추출 실패: {e}")
        
        return None


class GeneralEditorStrategy(SelectorStrategy):
    """일반 에디터 전용 선택자 전략"""
    
    def get_selectors(self) -> List[str]:
        """일반 에디터 관련 선택자들을 우선순위 순으로 반환"""
        return [
            '#content-area',
            'div[id="content-area"]',
            '.content_view',
            '.board-content',
            '.content-body',
            '.post-content',
            '.article-body',
            '.view-content',
            '.main-content'
        ]
    
    def get_strategy_name(self) -> str:
        return "일반 에디터"
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.GENERAL_EDITOR


class LegacyEditorStrategy(SelectorStrategy):
    """구형/레거시 에디터 전용 선택자 전략"""
    
    def get_selectors(self) -> List[str]:
        """구형 에디터 관련 선택자들을 우선순위 순으로 반환"""
        return [
            '#tbody',
            'td[id="tbody"]',
            '.post_content',
            '.view_content',
            '.article_viewer',
            '.board-view-content',
            'div.content_box',
            'table.board_view td',
            '.old-editor-content'
        ]
    
    def get_strategy_name(self) -> str:
        return "레거시 에디터"
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.LEGACY_EDITOR


class SelectorStrategyManager:
    """선택자 전략들을 관리하는 매니저 클래스"""
    
    def __init__(self):
        self.strategies = [
            SmartEditor3Strategy(),
            SmartEditor2Strategy(),
            GeneralEditorStrategy(),
            LegacyEditorStrategy()
        ]
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def extract_with_strategies(self, driver: webdriver.Chrome) -> Optional[Dict[str, Any]]:
        """
        모든 전략을 순차적으로 시도하여 콘텐츠를 추출합니다.
        
        Args:
            driver: Selenium WebDriver 인스턴스
            
        Returns:
            Optional[Dict]: 추출 결과 정보 (성공 시)
                - content: 추출된 콘텐츠
                - strategy: 성공한 전략 이름
                - extraction_method: 추출 방법
                - attempts: 시도한 전략들의 정보
        """
        attempts = []
        
        self.logger.info("🎯 SelectorStrategy 패턴으로 콘텐츠 추출 시작")
        
        for strategy in self.strategies:
            strategy_name = strategy.get_strategy_name()
            start_time = time.time()
            
            try:
                content = strategy.extract_with_selectors(driver)
                extraction_time = int((time.time() - start_time) * 1000)
                
                attempt = SelectorAttempt(
                    selector=strategy_name,
                    success=content is not None,
                    content_length=len(content) if content else 0,
                    extraction_time_ms=extraction_time
                )
                attempts.append(attempt)
                
                if content:
                    self.logger.info(f"🎉 '{strategy_name}' 전략으로 콘텐츠 추출 성공!")
                    return {
                        'content': content,
                        'strategy': strategy_name,
                        'extraction_method': strategy.get_extraction_method(),
                        'attempts': attempts
                    }
                
            except Exception as e:
                extraction_time = int((time.time() - start_time) * 1000)
                attempt = SelectorAttempt(
                    selector=strategy_name,
                    success=False,
                    content_length=0,
                    error_message=str(e),
                    extraction_time_ms=extraction_time
                )
                attempts.append(attempt)
                self.logger.warning(f"❌ '{strategy_name}' 전략 실패: {e}")
        
        self.logger.warning("⚠️ 모든 SelectorStrategy 전략 실패")
        return {
            'content': None,
            'strategy': None,
            'extraction_method': None,
            'attempts': attempts
        }
    
    def get_strategy_by_name(self, strategy_name: str) -> Optional[SelectorStrategy]:
        """이름으로 특정 전략을 가져옵니다."""
        for strategy in self.strategies:
            if strategy.get_strategy_name() == strategy_name:
                return strategy
        return None
    
    def add_custom_strategy(self, strategy: SelectorStrategy):
        """커스텀 전략을 추가합니다."""
        self.strategies.insert(0, strategy)  # 최우선으로 추가
        self.logger.info(f"➕ 커스텀 전략 추가: {strategy.get_strategy_name()}")
    
    def get_all_strategy_names(self) -> List[str]:
        """모든 전략 이름을 반환합니다."""
        return [strategy.get_strategy_name() for strategy in self.strategies]


# 카페별 특화 전략 예시
class CustomCafeStrategy(SelectorStrategy):
    """특정 카페에 특화된 커스텀 전략"""
    
    def __init__(self, cafe_name: str, custom_selectors: List[str]):
        super().__init__()
        self.cafe_name = cafe_name
        self.custom_selectors = custom_selectors
    
    def get_selectors(self) -> List[str]:
        return self.custom_selectors
    
    def get_strategy_name(self) -> str:
        return f"{self.cafe_name} 커스텀"
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.FALLBACK