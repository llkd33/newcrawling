# Implementation Plan

- [ ] 1. 핵심 데이터 모델 및 인터페이스 구현
  - ContentResult와 ValidationResult 데이터 클래스 생성
  - 기본 인터페이스와 타입 힌트 정의
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. PreloadingManager 클래스 구현
  - 동적 콘텐츠 로딩 대기 메커니즘 구현
  - document.readyState 확인 및 JavaScript 실행 완료 대기 로직
  - 스크롤 기반 lazy loading 트리거 메서드 구현
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. SelectorStrategy 패턴 구현
  - 기본 SelectorStrategy 클래스와 추상 메서드 정의
  - SmartEditor3Strategy 클래스 구현 (.se-main-container 등)
  - SmartEditor2Strategy 클래스 구현 (.ContentRenderer 등)
  - GeneralEditorStrategy 클래스 구현 (#content-area 등)
  - LegacyEditorStrategy 클래스 구현 (#tbody 등)
  - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.2_

- [x] 4. ContentValidator 클래스 구현
  - 내용 품질 검증 로직 구현 (최소 길이, 유효성 확인)
  - 불필요한 UI 텍스트 제거 메서드 구현
  - 내용 정제 및 길이 제한 처리 로직
  - _Requirements: 4.1, 4.2, 4.4_

- [ ] 5. DebugCollector 클래스 구현
  - 페이지 상태 정보 수집 메서드 구현
  - GitHub Actions 환경을 고려한 디버깅용 스크린샷 저장 기능
  - 선택자 시도 결과 로깅 시스템
  - GitHub Actions artifacts 업로드를 위한 파일 준비 기능
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 6. FallbackExtractor 클래스 구현
  - DOM 트리 순회를 통한 텍스트 추출 메서드
  - 페이지 새로고침 후 재시도 메커니즘
  - 최후 수단 추출 로직 구현
  - _Requirements: 2.4, 5.2, 5.4_

- [x] 7. ContentExtractor 메인 클래스 구현
  - 기존 get_article_content 메서드를 새로운 아키텍처로 리팩토링
  - 각 컴포넌트를 조합한 메인 추출 로직 구현
  - 오류 처리 및 복구 전략 통합
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

- [x] 8. 기존 NaverCafeCrawler 클래스 통합
  - 새로운 ContentExtractor를 기존 크롤러에 통합
  - 기존 get_article_content 메서드를 새로운 구현으로 교체
  - GitHub Actions 환경 감지 및 헤드리스 모드 최적화
  - 환경 변수 및 설정 추가 (타임아웃, 최소/최대 길이 등)
  - _Requirements: 4.3, 5.3_

- [ ] 9. 오류 처리 및 복구 메커니즘 구현
  - RecoveryStrategy 클래스 구현
  - 계층적 오류 처리 로직 (TimeoutException, NoSuchElementException 등)
  - 각 오류 유형별 복구 전략 구현
  - _Requirements: 2.4, 3.1, 3.2, 5.4_

- [ ] 10. 단위 테스트 작성
  - SelectorStrategy 각 전략별 테스트 케이스 작성
  - ContentValidator 검증 로직 테스트
  - PreloadingManager 대기 메커니즘 테스트
  - _Requirements: 3.3, 3.4_

- [x] 11. 통합 테스트 및 실제 데이터 검증
  - 실제 네이버 카페 게시물을 대상으로 한 통합 테스트 작성
  - 다양한 에디터 형식 (SmartEditor 2.0, 3.0, 일반) 테스트
  - 네트워크 지연 및 에러 시나리오 테스트
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

- [ ] 12. 성능 최적화 및 로깅 개선
  - 추출 시간 측정 및 최적화
  - 메모리 사용량 모니터링 및 개선
  - 상세한 로깅 시스템 구현 (성공률, 실패 원인 등)
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 13. 환경 설정 및 배포 준비
  - 새로운 환경 변수 추가 (.env.example 업데이트)
  - GitHub Actions 워크플로우 파일 업데이트 (새로운 환경변수 추가)
  - 카페별 커스텀 선택자 설정 시스템 구현
  - README 문서 업데이트 (새로운 기능 및 설정 방법)
  - _Requirements: 5.3_

- [x] 14. 최종 통합 및 검증
  - 전체 크롤링 프로세스 통합 테스트
  - GitHub Actions 환경에서의 실제 동작 검증
  - 헤드리스 모드에서의 성능 및 안정성 테스트
  - 성공률 측정 및 개선점 도출
  - _Requirements: 4.3, 5.1, 5.2_