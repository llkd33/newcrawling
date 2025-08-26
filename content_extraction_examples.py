#!/usr/bin/env python3
"""
콘텐츠 추출 데이터 모델 사용 예제
"""

from datetime import datetime
from content_extraction_models import (
    ContentResult, ValidationResult, SelectorAttempt, DebugInfo,
    ExtractionMethod, ExtractionConfig, CafeSpecificConfig
)


def example_successful_extraction():
    """성공적인 콘텐츠 추출 예제"""
    print("📝 성공적인 콘텐츠 추출 예제")
    
    # 디버깅 정보 생성
    debug_info = DebugInfo(
        url="https://cafe.naver.com/example/123",
        page_ready_state="complete",
        body_html_length=15000,
        editor_type_detected="SmartEditor3",
        selector_attempts=[],
        timestamp=datetime.now().isoformat()
    )
    
    # 선택자 시도 결과들 추가
    attempts = [
        SelectorAttempt(
            selector=".se-main-container",
            success=True,
            content_length=450,
            extraction_time_ms=120
        ),
        SelectorAttempt(
            selector=".ContentRenderer",
            success=False,
            content_length=0,
            error_message="Element not found"
        )
    ]
    
    for attempt in attempts:
        debug_info.add_selector_attempt(attempt)
    
    # 성공적인 추출 결과
    result = ContentResult(
        content="안녕하세요! 이것은 네이버 카페에서 추출된 게시물 내용입니다. 여러 줄에 걸쳐 작성된 내용이며, 의미 있는 정보를 담고 있습니다.",
        extraction_method=ExtractionMethod.SMART_EDITOR_3,
        quality_score=0.85,
        debug_info=debug_info.__dict__,
        success=True,
        extraction_time_ms=120
    )
    
    print(f"  ✅ 추출 성공: {len(result.content)}자")
    print(f"  📊 품질 점수: {result.quality_score}")
    print(f"  🔧 추출 방법: {result.extraction_method.value}")
    print(f"  ⏱️ 소요 시간: {result.extraction_time_ms}ms")
    print()


def example_content_validation():
    """콘텐츠 검증 예제"""
    print("🔍 콘텐츠 검증 예제")
    
    original_content = """
    로그인 메뉴 홈
    
    안녕하세요! 오늘 맛있는 음식을 만들어봤어요.
    재료는 다음과 같습니다:
    - 양파 1개
    - 당근 2개
    - 감자 3개
    
    조리 과정은...
    
    댓글 좋아요 스크랩
    """
    
    # 검증 결과 (불필요한 UI 텍스트 제거됨)
    cleaned_content = """안녕하세요! 오늘 맛있는 음식을 만들어봤어요.
재료는 다음과 같습니다:
- 양파 1개
- 당근 2개
- 감자 3개

조리 과정은..."""
    
    validation_result = ValidationResult(
        is_valid=True,
        quality_score=0.75,
        issues=["UI 텍스트 제거됨"],
        cleaned_content=cleaned_content,
        original_length=len(original_content),
        cleaned_length=len(cleaned_content)
    )
    
    print(f"  📏 원본 길이: {validation_result.original_length}자")
    print(f"  ✂️ 정제 후 길이: {validation_result.cleaned_length}자")
    print(f"  📊 품질 점수: {validation_result.quality_score}")
    print(f"  ⚠️ 발견된 문제: {', '.join(validation_result.issues)}")
    print(f"  ✅ 유효성: {'통과' if validation_result.is_valid else '실패'}")
    print()


def example_extraction_config():
    """추출 설정 예제"""
    print("⚙️ 추출 설정 예제")
    
    # 기본 설정
    default_config = ExtractionConfig()
    print(f"  기본 설정:")
    print(f"    - 타임아웃: {default_config.timeout_seconds}초")
    print(f"    - 최소 길이: {default_config.min_content_length}자")
    print(f"    - 최대 길이: {default_config.max_content_length}자")
    print(f"    - 재시도 횟수: {default_config.retry_count}회")
    
    # GitHub Actions 환경용 설정
    github_config = ExtractionConfig(
        timeout_seconds=45,  # 더 긴 타임아웃
        min_content_length=20,  # 더 관대한 최소 길이
        max_content_length=3000,  # 더 긴 최대 길이
        retry_count=5,  # 더 많은 재시도
        enable_debug_screenshot=True,  # 디버깅 스크린샷 활성화
        scroll_pause_time=3.0  # 더 긴 스크롤 대기 시간
    )
    
    print(f"  GitHub Actions 설정:")
    print(f"    - 타임아웃: {github_config.timeout_seconds}초")
    print(f"    - 재시도 횟수: {github_config.retry_count}회")
    print(f"    - 스크린샷: {'활성화' if github_config.enable_debug_screenshot else '비활성화'}")
    print()


def example_cafe_specific_config():
    """카페별 특화 설정 예제"""
    print("🏪 카페별 특화 설정 예제")
    
    # 특정 카페를 위한 커스텀 설정
    cafe_config = CafeSpecificConfig(
        cafe_name="맛집탐방카페",
        custom_selectors=[
            ".custom-food-content",
            ".recipe-container",
            ".food-review-text"
        ],
        custom_wait_time=15,
        custom_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Custom/1.0"
    )
    
    print(f"  카페명: {cafe_config.cafe_name}")
    print(f"  커스텀 선택자: {', '.join(cafe_config.custom_selectors)}")
    print(f"  커스텀 대기시간: {cafe_config.custom_wait_time}초")
    print(f"  커스텀 User-Agent: {cafe_config.custom_user_agent[:50]}...")
    print()


def example_failed_extraction():
    """실패한 추출 예제"""
    print("❌ 실패한 콘텐츠 추출 예제")
    
    # 모든 선택자가 실패한 경우의 디버깅 정보
    debug_info = DebugInfo(
        url="https://cafe.naver.com/difficult/456",
        page_ready_state="complete",
        body_html_length=8000,
        editor_type_detected=None,
        selector_attempts=[],
        screenshot_path="/tmp/debug_screenshot_20240826_143022.png",
        timestamp=datetime.now().isoformat()
    )
    
    # 실패한 선택자 시도들
    failed_attempts = [
        SelectorAttempt(
            selector=".se-main-container",
            success=False,
            content_length=0,
            error_message="NoSuchElementException: Unable to locate element"
        ),
        SelectorAttempt(
            selector=".ContentRenderer",
            success=False,
            content_length=0,
            error_message="Element found but empty"
        ),
        SelectorAttempt(
            selector="#content-area",
            success=False,
            content_length=0,
            error_message="TimeoutException: Element not visible"
        )
    ]
    
    for attempt in failed_attempts:
        debug_info.add_selector_attempt(attempt)
    
    # 실패 결과
    failed_result = ContentResult(
        content="",
        extraction_method=ExtractionMethod.FALLBACK,
        quality_score=0.0,
        debug_info=debug_info.__dict__,
        success=False,
        error_message="모든 추출 방법이 실패했습니다. 페이지 구조가 예상과 다를 수 있습니다."
    )
    
    print(f"  ❌ 추출 실패")
    print(f"  📊 품질 점수: {failed_result.quality_score}")
    print(f"  🔧 최종 시도 방법: {failed_result.extraction_method.value}")
    print(f"  💬 오류 메시지: {failed_result.error_message}")
    print(f"  📷 스크린샷: {debug_info.screenshot_path}")
    print(f"  🔍 시도한 선택자 수: {len(debug_info.selector_attempts)}")
    print()


def main():
    """예제 실행"""
    print("=" * 60)
    print("🚀 네이버 카페 콘텐츠 추출 데이터 모델 예제")
    print("=" * 60)
    print()
    
    example_successful_extraction()
    example_content_validation()
    example_extraction_config()
    example_cafe_specific_config()
    example_failed_extraction()
    
    print("=" * 60)
    print("✨ 모든 예제 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()