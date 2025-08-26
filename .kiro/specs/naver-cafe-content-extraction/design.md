# Design Document

## Overview

네이버 카페 크롤러의 게시물 내용 추출 문제를 해결하기 위한 강화된 콘텐츠 추출 시스템을 설계합니다. 현재 시스템은 다양한 에디터 형식과 동적 로딩 콘텐츠를 처리하는데 한계가 있어, 다층적 추출 전략과 강화된 대기 메커니즘을 도입합니다.

## Architecture

### 현재 시스템 분석

현재 `get_article_content` 메서드는 다음과 같은 구조로 되어 있습니다:

1. **새 탭에서 게시물 열기**
2. **iframe 전환 (`cafe_main`)**
3. **다중 선택자 시도**
4. **JavaScript 강제 추출**
5. **재시도 메커니즘**

### 문제점 분석

1. **동적 콘텐츠 로딩 대기 부족**: 3초 대기로는 SmartEditor의 복잡한 렌더링을 완전히 기다리지 못함
2. **선택자 우선순위 최적화 필요**: 현재 선택자 순서가 실제 사용 빈도와 맞지 않음
3. **에러 핸들링 개선 필요**: 실패 시 디버깅 정보가 부족함
4. **콘텐츠 품질 검증 부족**: 추출된 내용의 유효성 검사가 미흡함

### 새로운 아키텍처

```
ContentExtractor
├── PreloadingManager (동적 콘텐츠 로딩 관리)
├── SelectorStrategy (선택자 전략 패턴)
├── ContentValidator (내용 검증)
├── DebugCollector (디버깅 정보 수집)
└── FallbackExtractor (최후 수단 추출)
```

## Components and Interfaces

### 1. ContentExtractor (메인 클래스)

```python
class ContentExtractor:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
        self.preloader = PreloadingManager(driver)
        self.selector_strategy = SelectorStrategy()
        self.validator = ContentValidator()
        self.debug_collector = DebugCollector(driver)
        self.fallback = FallbackExtractor(driver)
    
    def extract_content(self, url: str) -> ContentResult:
        """메인 추출 메서드"""
        pass
```

### 2. PreloadingManager (동적 로딩 관리)

```python
class PreloadingManager:
    def wait_for_complete_loading(self):
        """완전한 페이지 로딩 대기"""
        # document.readyState 확인
        # JavaScript 실행 완료 대기
        # 동적 콘텐츠 로딩 트리거 (스크롤)
        pass
    
    def trigger_lazy_loading(self):
        """Lazy loading 콘텐츠 활성화"""
        pass
```

### 3. SelectorStrategy (선택자 전략)

```python
class SelectorStrategy:
    def __init__(self):
        self.strategies = [
            SmartEditor3Strategy(),
            SmartEditor2Strategy(), 
            GeneralEditorStrategy(),
            LegacyEditorStrategy()
        ]
    
    def extract_with_selectors(self, driver) -> str:
        """우선순위별 선택자 시도"""
        pass
```

### 4. ContentValidator (내용 검증)

```python
class ContentValidator:
    def validate_content(self, content: str) -> ValidationResult:
        """추출된 내용의 품질 검증"""
        # 최소 길이 확인
        # 불필요한 UI 텍스트 제거
        # 의미 있는 콘텐츠 여부 판단
        pass
    
    def clean_content(self, content: str) -> str:
        """내용 정제"""
        pass
```

### 5. DebugCollector (디버깅 정보 수집)

```python
class DebugCollector:
    def __init__(self, driver, is_github_actions=False):
        self.driver = driver
        self.is_github_actions = is_github_actions
    
    def collect_page_info(self) -> Dict:
        """페이지 상태 정보 수집"""
        pass
    
    def save_debug_screenshot(self, url: str):
        """디버깅용 스크린샷 저장 (GitHub Actions에서는 artifacts 디렉토리에)"""
        pass
    
    def log_selector_attempts(self, attempts: List):
        """선택자 시도 결과 로깅"""
        pass
    
    def prepare_artifacts_for_upload(self):
        """GitHub Actions artifacts 업로드 준비"""
        pass
```

### 6. FallbackExtractor (최후 수단)

```python
class FallbackExtractor:
    def extract_with_dom_traversal(self) -> str:
        """DOM 트리 순회를 통한 텍스트 추출"""
        pass
    
    def extract_with_refresh_retry(self, url: str) -> str:
        """새로고침 후 재시도"""
        pass
```

## Data Models

### ContentResult

```python
@dataclass
class ContentResult:
    content: str
    extraction_method: str  # 성공한 추출 방법
    quality_score: float   # 내용 품질 점수 (0-1)
    debug_info: Dict      # 디버깅 정보
    success: bool         # 추출 성공 여부
    error_message: str    # 실패 시 오류 메시지
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool
    quality_score: float
    issues: List[str]     # 발견된 문제점들
    cleaned_content: str  # 정제된 내용
```

## Error Handling

### 1. 계층적 오류 처리

```
Level 1: 선택자별 개별 오류 처리
Level 2: 전략별 오류 처리  
Level 3: 전체 추출 프로세스 오류 처리
Level 4: 최후 수단 (제목+URL만 저장)
```

### 2. 오류 유형별 대응

- **TimeoutException**: 대기 시간 증가 후 재시도
- **NoSuchElementException**: 다음 선택자로 이동
- **StaleElementReferenceException**: 페이지 새로고침 후 재시도
- **WebDriverException**: 드라이버 재시작

### 3. 복구 전략

```python
class RecoveryStrategy:
    def handle_timeout(self):
        """타임아웃 시 복구"""
        # 대기 시간 증가
        # 페이지 새로고침
        pass
    
    def handle_stale_element(self):
        """요소 참조 오류 시 복구"""
        # iframe 재진입
        # 요소 재탐색
        pass
```

## Testing Strategy

### 1. 단위 테스트

- **SelectorStrategy**: 각 선택자별 추출 테스트
- **ContentValidator**: 다양한 콘텐츠 품질 검증 테스트
- **PreloadingManager**: 로딩 대기 메커니즘 테스트

### 2. 통합 테스트

- **실제 카페 게시물**: 다양한 에디터 형식의 실제 게시물로 테스트
- **네트워크 지연 시뮬레이션**: 느린 네트워크 환경에서의 동작 테스트
- **에러 시나리오**: 의도적 오류 발생 시 복구 테스트

### 3. 성능 테스트

- **추출 시간 측정**: 각 전략별 평균 추출 시간
- **메모리 사용량**: 장시간 실행 시 메모리 누수 확인
- **성공률 측정**: 다양한 게시물에 대한 추출 성공률

## Implementation Plan

### Phase 1: 핵심 구조 개선

1. **ContentExtractor 클래스 리팩토링**
   - 현재 `get_article_content` 메서드를 모듈화
   - 각 책임별로 클래스 분리

2. **PreloadingManager 구현**
   - 동적 로딩 대기 메커니즘 강화
   - 스크롤 기반 lazy loading 트리거

### Phase 2: 선택자 전략 최적화

1. **SelectorStrategy 패턴 적용**
   - 에디터별 전략 클래스 구현
   - 우선순위 기반 선택자 시도

2. **실제 카페 데이터 기반 최적화**
   - 다양한 카페의 에디터 형식 조사
   - 성공률 기반 선택자 순서 조정

### Phase 3: 품질 검증 및 디버깅

1. **ContentValidator 구현**
   - 내용 품질 검증 로직
   - 불필요한 텍스트 제거 알고리즘

2. **DebugCollector 구현**
   - 상세한 디버깅 정보 수집
   - 실패 케이스 분석을 위한 로깅

### Phase 4: 최적화 및 안정화

1. **FallbackExtractor 구현**
   - DOM 트리 순회 기반 추출
   - 최후 수단 메커니즘

2. **성능 최적화**
   - 불필요한 대기 시간 제거
   - 메모리 사용량 최적화

## Configuration

### GitHub Actions 환경 고려사항

현재 시스템은 GitHub Actions에서 실행되므로 다음 제약사항을 고려해야 합니다:

- **헤드리스 모드**: `--headless=new` 옵션으로 실행
- **파일 시스템**: 스크린샷 등 디버깅 파일은 artifacts로 업로드
- **실행 시간 제한**: GitHub Actions의 실행 시간 제한 고려
- **메모리 제한**: Ubuntu runner의 메모리 제한 고려

### 환경 변수 추가

```bash
# 콘텐츠 추출 설정
CONTENT_EXTRACTION_TIMEOUT=30
CONTENT_MIN_LENGTH=30
CONTENT_MAX_LENGTH=2000
DEBUG_SCREENSHOT_ENABLED=true
EXTRACTION_RETRY_COUNT=3

# GitHub Actions 전용 설정
GITHUB_ACTIONS=true  # 이미 설정됨
HEADLESS_MODE=true
ARTIFACT_UPLOAD_ENABLED=true
```

### 카페별 커스텀 설정

```python
CAFE_SPECIFIC_SELECTORS = {
    'cafe1': ['.custom-selector-1', '.custom-selector-2'],
    'cafe2': ['.another-selector']
}
```

이 설계는 현재 시스템의 문제점을 체계적으로 해결하면서도 기존 코드와의 호환성을 유지하는 방향으로 구성했습니다.