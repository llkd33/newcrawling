# Task 11: 통합 테스트 및 실제 데이터 검증

이 문서는 네이버 카페 콘텐츠 추출 시스템의 통합 테스트에 대한 종합적인 가이드입니다.

## 📋 Requirements 충족 현황

### ✅ Requirement 1.1, 1.2, 1.3 - 다양한 에디터 형식 테스트
- **SmartEditor 3.0**: `.se-main-container` 선택자 기반 추출
- **SmartEditor 2.0**: `.ContentRenderer`, `#postViewArea` 선택자 기반 추출  
- **일반 에디터**: `#content-area`, `.content-body` 선택자 기반 추출
- **레거시 에디터**: `#tbody`, `table.board-content` 선택자 기반 추출

### ✅ Requirement 2.1, 2.2, 2.3 - 동적 콘텐츠 로딩 테스트
- **페이지 로딩 대기**: `document.readyState` 확인 및 완료 대기
- **iframe 전환 후 대기**: 최소 3초간 추가 대기로 동적 콘텐츠 로딩 허용
- **Lazy Loading 활성화**: 페이지 스크롤을 통한 지연 로딩 콘텐츠 활성화

## 🧪 테스트 파일 구조

```
├── test_integration_real_data.py     # 실제 데이터 통합 테스트 (메인)
├── test_editor_formats.py            # 에디터 형식별 특화 테스트
├── test_performance_load.py          # 성능 및 부하 테스트
├── run_integration_tests.py          # 통합 테스트 실행기
├── test_quick_validation.py          # 빠른 검증 테스트
└── INTEGRATION_TESTS_README.md       # 이 문서
```

## 🚀 테스트 실행 방법

### 1. 환경 설정

```bash
# 필수 환경변수 설정 (.env 파일)
NAVER_ID=your_naver_id
NAVER_PW=your_naver_password

# 선택적 환경변수
CONTENT_EXTRACTION_TIMEOUT=30
CONTENT_MIN_LENGTH=30
CONTENT_MAX_LENGTH=2000
DEBUG_SCREENSHOT_ENABLED=true
```

### 2. 의존성 설치

```bash
pip install selenium pytest psutil python-dotenv
```

### 3. 테스트 실행

#### 빠른 검증 테스트
```bash
python test_quick_validation.py
```

#### 전체 통합 테스트
```bash
python run_integration_tests.py
```

#### 개별 테스트 실행
```bash
# 실제 데이터 테스트
python test_integration_real_data.py

# 에디터 형식 테스트 (pytest)
python -m pytest test_editor_formats.py -v

# 성능 테스트
python test_performance_load.py
```

## 📊 테스트 상세 내용

### 1. 실제 데이터 통합 테스트 (`test_integration_real_data.py`)

#### 🎯 에디터 형식 감지 테스트
- **F-E 카페 SmartEditor 3.0**: 실제 게시물에서 `.se-main-container` 감지 및 추출
- **일반 카페 SmartEditor 2.0**: `.ContentRenderer` 기반 추출 테스트
- **레거시 에디터**: 구형 에디터 형식 처리 테스트

#### 🔄 동적 콘텐츠 로딩 테스트
- **기본 로딩 대기**: 15초 타임아웃으로 기본 동작 테스트
- **긴 로딩 대기**: 45초 타임아웃과 lazy loading 트리거 활성화
- **짧은 로딩 대기**: 5초 타임아웃으로 타임아웃 처리 테스트

#### 🌐 네트워크 지연 시나리오
- **정상 네트워크**: 지연 없음, 10MB/s 처리량
- **느린 네트워크**: 2초 지연, 500KB/s 처리량  
- **매우 느린 네트워크**: 5초 지연, 100KB/s 처리량

#### ⚠️ 에러 시나리오 테스트
- **존재하지 않는 게시물**: 404 오류 처리 테스트
- **접근 권한 없는 게시물**: 권한 오류 처리 테스트
- **매우 짧은 타임아웃**: 타임아웃 예외 처리 테스트

### 2. 에디터 형식 테스트 (`test_editor_formats.py`)

#### pytest 기반 단위 테스트
- **SmartEditor 3.0 감지**: `.se-main-container` 선택자 테스트
- **SmartEditor 2.0 감지**: `.ContentRenderer` 선택자 테스트
- **일반 에디터 감지**: `#content-area` 선택자 테스트
- **레거시 에디터 감지**: `#tbody` 선택자 테스트
- **추출 방법 우선순위**: 여러 에디터 요소 동시 존재 시 우선순위 테스트
- **콘텐츠 품질 검증**: 최소 길이, 품질 점수 검증
- **이미지 추출**: 이미지 URL 추출 기능 테스트

### 3. 성능 및 부하 테스트 (`test_performance_load.py`)

#### 📈 성능 메트릭 측정
- **추출 속도**: 평균, 중앙값, 최소/최대 추출 시간
- **메모리 사용량**: 추출 과정에서의 메모리 증가량 측정
- **성공률**: 반복 테스트를 통한 안정성 측정

#### ⏱️ 타임아웃 시나리오
- **매우 짧은 타임아웃** (5초): 실패 예상 시나리오
- **짧은 타임아웃** (15초): 기본 성능 테스트
- **일반 타임아웃** (30초): 표준 운영 환경
- **긴 타임아웃** (60초): 안정성 우선 환경

#### 🔄 동시 추출 테스트
- **멀티 워커**: 동시에 여러 추출 작업 실행
- **리소스 경합**: 메모리, CPU 사용량 모니터링
- **안정성 검증**: 동시 실행 시 오류 발생률 측정

#### 🧠 메모리 누수 감지
- **반복 실행**: 20회 반복으로 메모리 증가 패턴 분석
- **가비지 컬렉션**: 강제 GC 후 메모리 상태 확인
- **누수 판정**: 100MB 이상 증가 시 누수로 판정

## 📊 테스트 결과 해석

### 성공 기준

#### 🎯 전체 통합 테스트
- **성공률**: 70% 이상
- **에디터 형식 감지**: 최소 1개 이상 성공
- **동적 로딩**: 페이지 로딩 완료 확인
- **오류 처리**: Graceful failure 구현

#### ⚡ 성능 테스트
- **평균 추출 시간**: 30초 이내
- **메모리 사용량**: 100MB 이내 증가
- **동시 처리**: 3개 워커 동시 실행 성공
- **메모리 누수**: 없음

### 보고서 형식

테스트 실행 후 다음 파일들이 생성됩니다:

```
integration_test_report_YYYYMMDD_HHMMSS.txt    # 텍스트 보고서
integration_test_results_YYYYMMDD_HHMMSS.json  # JSON 상세 결과
performance_test_report_YYYYMMDD_HHMMSS.txt    # 성능 테스트 보고서
```

## 🔧 GitHub Actions 환경

### 환경 변수 설정
```yaml
env:
  NAVER_ID: ${{ secrets.NAVER_ID }}
  NAVER_PW: ${{ secrets.NAVER_PW }}
  GITHUB_ACTIONS: true
  HEADLESS_MODE: true
```

### 아티팩트 업로드
```yaml
- name: Upload test artifacts
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: integration-test-results
    path: |
      artifacts/
      *_report_*.txt
      *_results_*.json
```

## 🐛 문제 해결

### 일반적인 문제들

#### 1. 로그인 실패
```bash
❌ 네이버 로그인 실패
```
**해결방법**: 
- NAVER_ID, NAVER_PW 환경변수 확인
- 계정 보안 설정 확인 (2단계 인증 등)

#### 2. Chrome 드라이버 오류
```bash
❌ Chrome 드라이버 오류
```
**해결방법**:
- Chrome 브라우저 최신 버전 설치
- ChromeDriver 버전 호환성 확인
- PATH 환경변수에 ChromeDriver 경로 추가

#### 3. 타임아웃 오류
```bash
⚠️ 페이지 로딩 대기 타임아웃
```
**해결방법**:
- CONTENT_EXTRACTION_TIMEOUT 값 증가
- 네트워크 연결 상태 확인
- 헤드리스 모드에서 --no-sandbox 옵션 추가

#### 4. 메모리 부족
```bash
❌ 메모리 사용량 초과
```
**해결방법**:
- 테스트 반복 횟수 감소
- 가비지 컬렉션 강제 실행
- Chrome 옵션에 메모리 제한 추가

### 디버깅 옵션

#### 상세 로깅 활성화
```bash
export PYTHONPATH=.
python -m logging.config.dictConfig '{"version": 1, "disable_existing_loggers": false, "formatters": {"default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}}, "handlers": {"default": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "default"}}, "root": {"level": "DEBUG", "handlers": ["default"]}}'
```

#### 스크린샷 활성화
```bash
export DEBUG_SCREENSHOT_ENABLED=true
```

#### 헤드리스 모드 비활성화 (로컬 테스트)
```python
# test_integration_real_data.py에서
test_suite.run_all_tests(headless=False)
```

## 📈 성능 최적화 팁

### 1. 테스트 실행 시간 단축
- 병렬 실행: pytest-xdist 사용
- 선택적 테스트: 특정 에디터만 테스트
- 캐시 활용: 로그인 세션 재사용

### 2. 안정성 향상
- 재시도 메커니즘: 네트워크 오류 시 자동 재시도
- 대기 시간 조정: 동적 콘텐츠 로딩 시간 고려
- 오류 복구: Graceful degradation 구현

### 3. 리소스 사용량 최적화
- 메모리 관리: 명시적 가비지 컬렉션
- 프로세스 관리: 드라이버 인스턴스 적절한 종료
- 네트워크 최적화: 불필요한 리소스 로딩 방지

## 🎯 Task 11 완료 체크리스트

- [x] **실제 네이버 카페 게시물 대상 통합 테스트 작성**
  - [x] F-E 카페 실제 게시물 테스트
  - [x] 다양한 카페 형식 지원
  - [x] 실제 로그인 및 크롤링 프로세스

- [x] **다양한 에디터 형식 테스트**
  - [x] SmartEditor 3.0 (.se-main-container)
  - [x] SmartEditor 2.0 (.ContentRenderer, #postViewArea)  
  - [x] 일반 에디터 (#content-area)
  - [x] 레거시 에디터 (#tbody)

- [x] **네트워크 지연 및 에러 시나리오 테스트**
  - [x] 다양한 네트워크 속도 시뮬레이션
  - [x] 타임아웃 처리 테스트
  - [x] 404, 권한 오류 등 예외 상황 테스트
  - [x] Graceful failure 검증

- [x] **성능 및 안정성 테스트**
  - [x] 추출 속도 측정
  - [x] 메모리 사용량 모니터링
  - [x] 동시 처리 능력 테스트
  - [x] 메모리 누수 감지

- [x] **자동화된 테스트 실행 환경**
  - [x] GitHub Actions 호환
  - [x] 헤드리스 모드 지원
  - [x] 아티팩트 업로드
  - [x] 종합 보고서 생성

## 📞 지원 및 문의

테스트 관련 문제나 개선 사항이 있으시면 다음을 참고하세요:

1. **로그 확인**: 상세 로그를 통한 문제 진단
2. **환경 검증**: 필수 조건 및 의존성 확인  
3. **단계별 실행**: 빠른 검증 → 개별 테스트 → 전체 통합 테스트
4. **보고서 분석**: 생성된 보고서를 통한 상세 분석

---

**Task 11 완료**: 이 통합 테스트 스위트는 네이버 카페 콘텐츠 추출 시스템의 모든 핵심 기능을 실제 데이터로 검증하며, 다양한 에디터 형식과 네트워크 조건에서의 안정성을 보장합니다.