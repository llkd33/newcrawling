#!/usr/bin/env python3
"""
네이버 카페 콘텐츠 추출을 위한 핵심 데이터 모델 및 인터페이스
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from enum import Enum


class ExtractionMethod(Enum):
    """콘텐츠 추출 방법 열거형"""
    SMART_EDITOR_3 = "smart_editor_3"
    SMART_EDITOR_2 = "smart_editor_2"
    GENERAL_EDITOR = "general_editor"
    LEGACY_EDITOR = "legacy_editor"
    JAVASCRIPT_EXTRACTION = "javascript_extraction"
    DOM_TRAVERSAL = "dom_traversal"
    FALLBACK = "fallback"


@dataclass
class ContentResult:
    """콘텐츠 추출 결과를 담는 데이터 클래스"""
    content: str
    extraction_method: ExtractionMethod
    quality_score: float  # 내용 품질 점수 (0.0-1.0)
    debug_info: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    extraction_time_ms: Optional[int] = None  # 추출 소요 시간 (밀리초)
    
    def __post_init__(self):
        """데이터 검증"""
        if not isinstance(self.quality_score, (int, float)) or not (0.0 <= self.quality_score <= 1.0):
            raise ValueError("quality_score는 0.0과 1.0 사이의 값이어야 합니다")
        
        if self.success and not self.content:
            raise ValueError("성공한 추출 결과는 content가 비어있을 수 없습니다")


@dataclass
class ValidationResult:
    """콘텐츠 검증 결과를 담는 데이터 클래스"""
    is_valid: bool
    quality_score: float  # 품질 점수 (0.0-1.0)
    issues: List[str]  # 발견된 문제점들
    cleaned_content: str  # 정제된 내용
    original_length: int  # 원본 길이
    cleaned_length: int  # 정제 후 길이
    
    def __post_init__(self):
        """데이터 검증"""
        if not isinstance(self.quality_score, (int, float)) or not (0.0 <= self.quality_score <= 1.0):
            raise ValueError("quality_score는 0.0과 1.0 사이의 값이어야 합니다")
        
        if self.original_length < 0 or self.cleaned_length < 0:
            raise ValueError("길이 값은 음수일 수 없습니다")


@dataclass
class SelectorAttempt:
    """선택자 시도 결과를 담는 데이터 클래스"""
    selector: str
    success: bool
    content_length: int
    error_message: Optional[str] = None
    extraction_time_ms: Optional[int] = None


@dataclass
class DebugInfo:
    """디버깅 정보를 담는 데이터 클래스"""
    url: str
    page_ready_state: str
    body_html_length: int
    editor_type_detected: Optional[str]
    selector_attempts: List[SelectorAttempt]
    screenshot_path: Optional[str] = None
    timestamp: Optional[str] = None
    
    def add_selector_attempt(self, attempt: SelectorAttempt):
        """선택자 시도 결과 추가"""
        self.selector_attempts.append(attempt)


# 추상 인터페이스 정의

class ContentExtractorInterface(ABC):
    """콘텐츠 추출기 인터페이스"""
    
    @abstractmethod
    def extract_content(self, url: str) -> ContentResult:
        """
        주어진 URL에서 콘텐츠를 추출합니다.
        
        Args:
            url: 추출할 게시물의 URL
            
        Returns:
            ContentResult: 추출 결과
        """
        pass


class PreloadingManagerInterface(ABC):
    """동적 콘텐츠 로딩 관리 인터페이스"""
    
    @abstractmethod
    def wait_for_complete_loading(self, timeout: int = 30) -> bool:
        """
        페이지의 완전한 로딩을 대기합니다.
        
        Args:
            timeout: 최대 대기 시간 (초)
            
        Returns:
            bool: 로딩 완료 여부
        """
        pass
    
    @abstractmethod
    def trigger_lazy_loading(self) -> None:
        """
        Lazy loading 콘텐츠를 활성화합니다.
        """
        pass


class SelectorStrategyInterface(ABC):
    """선택자 전략 인터페이스"""
    
    @abstractmethod
    def get_selectors(self) -> List[str]:
        """
        해당 전략의 선택자 목록을 반환합니다.
        
        Returns:
            List[str]: 선택자 목록 (우선순위 순)
        """
        pass
    
    @abstractmethod
    def extract_with_selectors(self, driver) -> Optional[str]:
        """
        선택자를 사용하여 콘텐츠를 추출합니다.
        
        Args:
            driver: Selenium WebDriver 인스턴스
            
        Returns:
            Optional[str]: 추출된 콘텐츠 (실패 시 None)
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        전략 이름을 반환합니다.
        
        Returns:
            str: 전략 이름
        """
        pass


class ContentValidatorInterface(ABC):
    """콘텐츠 검증기 인터페이스"""
    
    @abstractmethod
    def validate_content(self, content: str) -> ValidationResult:
        """
        추출된 콘텐츠의 품질을 검증합니다.
        
        Args:
            content: 검증할 콘텐츠
            
        Returns:
            ValidationResult: 검증 결과
        """
        pass
    
    @abstractmethod
    def clean_content(self, content: str) -> str:
        """
        콘텐츠를 정제합니다.
        
        Args:
            content: 정제할 콘텐츠
            
        Returns:
            str: 정제된 콘텐츠
        """
        pass


class DebugCollectorInterface(ABC):
    """디버깅 정보 수집기 인터페이스"""
    
    @abstractmethod
    def collect_page_info(self, url: str) -> DebugInfo:
        """
        페이지 상태 정보를 수집합니다.
        
        Args:
            url: 현재 페이지 URL
            
        Returns:
            DebugInfo: 수집된 디버깅 정보
        """
        pass
    
    @abstractmethod
    def save_debug_screenshot(self, url: str, filename_prefix: str = "debug") -> Optional[str]:
        """
        디버깅용 스크린샷을 저장합니다.
        
        Args:
            url: 현재 페이지 URL
            filename_prefix: 파일명 접두사
            
        Returns:
            Optional[str]: 저장된 파일 경로 (실패 시 None)
        """
        pass


class FallbackExtractorInterface(ABC):
    """최후 수단 추출기 인터페이스"""
    
    @abstractmethod
    def extract_with_dom_traversal(self) -> Optional[str]:
        """
        DOM 트리 순회를 통해 텍스트를 추출합니다.
        
        Returns:
            Optional[str]: 추출된 텍스트 (실패 시 None)
        """
        pass
    
    @abstractmethod
    def extract_with_refresh_retry(self, url: str) -> Optional[str]:
        """
        페이지 새로고침 후 재시도하여 콘텐츠를 추출합니다.
        
        Args:
            url: 재시도할 페이지 URL
            
        Returns:
            Optional[str]: 추출된 콘텐츠 (실패 시 None)
        """
        pass


# 타입 힌트 정의
from typing import TypeVar, Generic, Callable, Union

T = TypeVar('T')
ExtractorResult = Union[ContentResult, None]
ValidatorResult = Union[ValidationResult, None]
DebugResult = Union[DebugInfo, None]

# 콜백 함수 타입 정의
ProgressCallback = Callable[[str, float], None]  # (message, progress_percentage)
ErrorCallback = Callable[[Exception, str], None]  # (error, context)
SuccessCallback = Callable[[ContentResult], None]  # (result)


# 설정 관련 데이터 클래스
@dataclass
class ExtractionConfig:
    """콘텐츠 추출 설정"""
    timeout_seconds: int = 30
    min_content_length: int = 30
    max_content_length: int = 2000
    retry_count: int = 3
    enable_debug_screenshot: bool = True
    enable_lazy_loading_trigger: bool = True
    scroll_pause_time: float = 2.0
    
    def __post_init__(self):
        """설정 값 검증"""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds는 양수여야 합니다")
        if self.min_content_length < 0:
            raise ValueError("min_content_length는 음수일 수 없습니다")
        if self.max_content_length <= self.min_content_length:
            raise ValueError("max_content_length는 min_content_length보다 커야 합니다")
        if self.retry_count < 0:
            raise ValueError("retry_count는 음수일 수 없습니다")


@dataclass
class CafeSpecificConfig:
    """카페별 특화 설정"""
    cafe_name: str
    custom_selectors: List[str]
    custom_wait_time: Optional[int] = None
    custom_user_agent: Optional[str] = None
    
    def __post_init__(self):
        """설정 값 검증"""
        if not self.cafe_name.strip():
            raise ValueError("cafe_name은 비어있을 수 없습니다")
        if not self.custom_selectors:
            raise ValueError("custom_selectors는 비어있을 수 없습니다")