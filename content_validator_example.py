#!/usr/bin/env python3
"""
ContentValidator 사용 예제
"""

from content_validator import ContentValidator
from content_extraction_models import ExtractionConfig


def main():
    """ContentValidator 사용 예제를 실행합니다"""
    
    # 기본 설정으로 ContentValidator 생성
    validator = ContentValidator()
    
    print("=== ContentValidator 사용 예제 ===\n")
    
    # 예제 1: 유효한 콘텐츠
    print("1. 유효한 콘텐츠 검증:")
    valid_content = """
    이것은 네이버 카페에서 추출된 게시물 내용입니다.
    여러 문장으로 구성되어 있고, 충분한 길이를 가지고 있습니다.
    사용자가 작성한 의미있는 내용을 담고 있어서 품질이 좋습니다.
    """
    
    result = validator.validate_content(valid_content)
    print(f"  - 유효성: {result.is_valid}")
    print(f"  - 품질 점수: {result.quality_score:.2f}")
    print(f"  - 원본 길이: {result.original_length}자")
    print(f"  - 정제 후 길이: {result.cleaned_length}자")
    print(f"  - 문제점: {result.issues}")
    print(f"  - 정제된 내용: {result.cleaned_content[:100]}...")
    print()
    
    # 예제 2: UI 텍스트가 포함된 콘텐츠
    print("2. UI 텍스트 제거:")
    ui_content = """
    실제 게시물 내용입니다.
    로그인하세요
    댓글 5개
    공유하기
    좋아요 10
    이것은 더 많은 실제 내용입니다.
    """
    
    cleaned = validator.clean_content(ui_content)
    print(f"  - 원본: {ui_content.strip()}")
    print(f"  - 정제 후: {cleaned}")
    print()
    
    # 예제 3: HTML 태그가 포함된 콘텐츠
    print("3. HTML 태그 제거:")
    html_content = '<p>이것은 <strong>HTML</strong> 태그가 포함된 <em>콘텐츠</em>입니다.</p>'
    
    cleaned_html = validator.clean_content(html_content)
    print(f"  - 원본: {html_content}")
    print(f"  - 정제 후: {cleaned_html}")
    print()
    
    # 예제 4: 너무 짧은 콘텐츠
    print("4. 너무 짧은 콘텐츠:")
    short_content = "짧은 글"
    
    result_short = validator.validate_content(short_content)
    print(f"  - 유효성: {result_short.is_valid}")
    print(f"  - 품질 점수: {result_short.quality_score:.2f}")
    print(f"  - 문제점: {result_short.issues}")
    print()
    
    # 예제 5: 너무 긴 콘텐츠 (잘리는 경우)
    print("5. 너무 긴 콘텐츠 (자동 잘림):")
    long_content = "이것은 매우 긴 콘텐츠입니다. " * 100  # 2000자 초과
    
    result_long = validator.validate_content(long_content)
    print(f"  - 원본 길이: {len(long_content)}자")
    print(f"  - 정제 후 길이: {result_long.cleaned_length}자")
    print(f"  - 최대 허용 길이: {validator.config.max_content_length}자")
    print(f"  - 문제점: {result_long.issues}")
    print(f"  - 잘린 내용 끝부분: ...{result_long.cleaned_content[-50:]}")
    print()
    
    # 예제 6: 커스텀 설정 사용
    print("6. 커스텀 설정 사용:")
    custom_config = ExtractionConfig(
        min_content_length=50,  # 최소 50자
        max_content_length=500,  # 최대 500자
    )
    custom_validator = ContentValidator(custom_config)
    
    test_content = "이것은 커스텀 설정으로 테스트하는 콘텐츠입니다. 기본 설정과 다른 결과를 보여줄 것입니다."
    
    result_custom = custom_validator.validate_content(test_content)
    print(f"  - 커스텀 최소 길이: {custom_config.min_content_length}자")
    print(f"  - 커스텀 최대 길이: {custom_config.max_content_length}자")
    print(f"  - 콘텐츠 길이: {result_custom.cleaned_length}자")
    print(f"  - 유효성: {result_custom.is_valid}")
    print(f"  - 품질 점수: {result_custom.quality_score:.2f}")
    print()
    
    # 예제 7: 콘텐츠 요약 생성
    print("7. 콘텐츠 요약 생성:")
    summary_content = """
    이것은 긴 게시물 내용입니다. 첫 번째 문장은 중요한 정보를 담고 있습니다.
    두 번째 문장은 부가적인 설명을 제공합니다. 세 번째 문장은 더 자세한 내용을 다룹니다.
    네 번째 문장부터는 추가적인 정보들이 계속 이어집니다.
    """
    
    summary = validator.get_content_summary(summary_content, 80)
    print(f"  - 원본 길이: {len(summary_content.strip())}자")
    print(f"  - 요약 길이: {len(summary)}자")
    print(f"  - 요약: {summary}")
    print()


if __name__ == "__main__":
    main()