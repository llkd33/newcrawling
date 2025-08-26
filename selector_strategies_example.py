#!/usr/bin/env python3
"""
SelectorStrategy 패턴 사용 예시
"""

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from selector_strategies import (
    SelectorStrategyManager,
    SmartEditor3Strategy,
    CustomCafeStrategy
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_usage():
    """SelectorStrategy 패턴 사용 예시"""
    
    # 1. 기본 사용법 - SelectorStrategyManager 사용
    print("=== SelectorStrategyManager 기본 사용법 ===")
    
    # Chrome 드라이버 설정 (실제 사용 시)
    options = Options()
    options.add_argument('--headless')  # 헤드리스 모드
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 실제 드라이버 대신 예시를 위한 Mock 사용
    # driver = webdriver.Chrome(options=options)
    
    # 매니저 초기화
    manager = SelectorStrategyManager()
    
    # 사용 가능한 전략들 확인
    print("사용 가능한 전략들:")
    for strategy_name in manager.get_all_strategy_names():
        print(f"  - {strategy_name}")
    
    # 실제 추출 시 사용법 (드라이버가 있을 때)
    # result = manager.extract_with_strategies(driver)
    # if result['content']:
    #     print(f"추출 성공! 전략: {result['strategy']}")
    #     print(f"내용: {result['content'][:100]}...")
    # else:
    #     print("모든 전략 실패")
    #     for attempt in result['attempts']:
    #         print(f"  - {attempt.selector}: {'성공' if attempt.success else '실패'}")
    
    print("\n=== 개별 전략 사용법 ===")
    
    # 2. 개별 전략 직접 사용
    se3_strategy = SmartEditor3Strategy()
    print(f"전략 이름: {se3_strategy.get_strategy_name()}")
    print(f"추출 방법: {se3_strategy.get_extraction_method()}")
    print("선택자 목록:")
    for selector in se3_strategy.get_selectors():
        print(f"  - {selector}")
    
    print("\n=== 커스텀 전략 추가 ===")
    
    # 3. 커스텀 전략 추가
    custom_selectors = [
        '.my-custom-content',
        '.special-cafe-selector',
        '#unique-content-area'
    ]
    custom_strategy = CustomCafeStrategy("특별한카페", custom_selectors)
    
    # 매니저에 커스텀 전략 추가 (최우선으로 추가됨)
    manager.add_custom_strategy(custom_strategy)
    
    print("커스텀 전략 추가 후 전략 목록:")
    for strategy_name in manager.get_all_strategy_names():
        print(f"  - {strategy_name}")
    
    print("\n=== 특정 전략 가져오기 ===")
    
    # 4. 특정 전략 가져오기
    se2_strategy = manager.get_strategy_by_name("SmartEditor 2.0")
    if se2_strategy:
        print(f"SmartEditor 2.0 전략 선택자들:")
        for selector in se2_strategy.get_selectors():
            print(f"  - {selector}")
    
    print("\n=== 실제 사용 시나리오 예시 ===")
    print("""
    # 실제 크롤러에서 사용할 때:
    
    def get_article_content_with_strategies(self, url: str) -> str:
        try:
            # 페이지 로딩 및 iframe 전환 등 기본 설정
            self.driver.get(url)
            # ... 기본 설정 코드 ...
            
            # SelectorStrategy 패턴으로 콘텐츠 추출
            manager = SelectorStrategyManager()
            result = manager.extract_with_strategies(self.driver)
            
            if result['content']:
                logging.info(f"✅ {result['strategy']} 전략으로 추출 성공")
                return result['content']
            else:
                logging.warning("⚠️ 모든 전략 실패")
                # 시도한 전략들의 상세 정보 로깅
                for attempt in result['attempts']:
                    logging.debug(f"  - {attempt.selector}: {'성공' if attempt.success else '실패'} "
                                f"({attempt.extraction_time_ms}ms)")
                
                # 폴백 처리
                return self.fallback_extraction()
                
        except Exception as e:
            logging.error(f"추출 중 오류: {e}")
            return f"내용을 불러올 수 없습니다.\\n원본 링크: {url}"
    """)


def demonstrate_strategy_pattern_benefits():
    """SelectorStrategy 패턴의 장점 설명"""
    print("\n" + "="*60)
    print("SelectorStrategy 패턴의 장점")
    print("="*60)
    
    benefits = [
        "1. 확장성: 새로운 에디터 형식에 대응하는 전략을 쉽게 추가 가능",
        "2. 유지보수성: 각 에디터별 로직이 분리되어 수정이 용이",
        "3. 테스트 용이성: 각 전략을 독립적으로 테스트 가능",
        "4. 우선순위 관리: 성공률이 높은 전략을 우선적으로 시도",
        "5. 디버깅 개선: 각 전략의 시도 결과를 상세히 추적 가능",
        "6. 카페별 커스터마이징: 특정 카페에 특화된 전략 추가 가능"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print("\n기존 방식과의 비교:")
    print("  기존: 하나의 긴 메서드에서 모든 선택자를 순차 시도")
    print("  개선: 각 에디터별로 최적화된 전략 클래스로 분리")
    print("  결과: 코드 가독성 향상, 유지보수 용이성 증대, 확장성 확보")


if __name__ == "__main__":
    example_usage()
    demonstrate_strategy_pattern_benefits()