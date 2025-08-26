# Requirements Document

## Introduction

네이버 카페 크롤러에서 게시물 제목은 성공적으로 크롤링하지만 게시물 내용을 제대로 추출하지 못하는 문제를 해결해야 합니다. 현재 시스템은 9시, 12시, 5시에 5개씩 게시물을 크롤링하여 Notion에 저장하는데, 내용 추출 실패로 인해 "내용을 불러올 수 없습니다"라는 메시지만 저장되고 있습니다.

## Requirements

### Requirement 1

**User Story:** 크롤러 운영자로서, 네이버 카페의 다양한 에디터 형식(SmartEditor 2.0, 3.0, 일반 에디터)에서 게시물 내용을 안정적으로 추출하고 싶습니다. 그래야 완전한 게시물 정보를 Notion에 저장할 수 있습니다.

#### Acceptance Criteria

1. WHEN 크롤러가 SmartEditor 3.0으로 작성된 게시물에 접근할 때 THEN 시스템은 `.se-main-container` 및 관련 선택자를 통해 내용을 추출해야 합니다
2. WHEN 크롤러가 SmartEditor 2.0으로 작성된 게시물에 접근할 때 THEN 시스템은 `.ContentRenderer`, `#postViewArea` 선택자를 통해 내용을 추출해야 합니다
3. WHEN 크롤러가 일반 에디터로 작성된 게시물에 접근할 때 THEN 시스템은 `#tbody`, `#content-area` 선택자를 통해 내용을 추출해야 합니다
4. WHEN 기본 선택자로 내용 추출이 실패할 때 THEN 시스템은 JavaScript를 사용한 대체 추출 방법을 시도해야 합니다

### Requirement 2

**User Story:** 크롤러 운영자로서, 동적으로 로딩되는 콘텐츠를 안정적으로 기다리고 추출하고 싶습니다. 그래야 JavaScript로 렌더링되는 내용도 놓치지 않을 수 있습니다.

#### Acceptance Criteria

1. WHEN 크롤러가 게시물 페이지에 접근할 때 THEN 시스템은 `document.readyState`가 'complete'가 될 때까지 대기해야 합니다
2. WHEN iframe 전환 후 THEN 시스템은 최소 3초간 추가 대기하여 동적 콘텐츠 로딩을 허용해야 합니다
3. WHEN 콘텐츠 추출 전 THEN 시스템은 페이지 스크롤을 통해 lazy loading 콘텐츠를 활성화해야 합니다
4. WHEN 첫 번째 추출 시도가 실패할 때 THEN 시스템은 페이지를 새로고침하고 재시도해야 합니다

### Requirement 3

**User Story:** 크롤러 운영자로서, 내용 추출 실패 시 상세한 디버깅 정보를 얻고 싶습니다. 그래야 문제를 분석하고 해결할 수 있습니다.

#### Acceptance Criteria

1. WHEN 내용 추출이 실패할 때 THEN 시스템은 페이지의 에디터 타입, 선택자 존재 여부, HTML 길이 등의 디버깅 정보를 로그에 기록해야 합니다
2. WHEN 내용 추출이 실패할 때 THEN 시스템은 해당 페이지의 스크린샷을 저장해야 합니다
3. WHEN 각 선택자 시도 시 THEN 시스템은 선택자별 성공/실패 상태를 로그에 기록해야 합니다
4. WHEN JavaScript 추출 방법을 사용할 때 THEN 시스템은 추출된 텍스트의 길이와 품질을 검증하고 로그에 기록해야 합니다

### Requirement 4

**User Story:** 크롤러 운영자로서, 추출된 내용의 품질을 검증하고 정제하고 싶습니다. 그래야 의미 있는 콘텐츠만 Notion에 저장할 수 있습니다.

#### Acceptance Criteria

1. WHEN 내용이 추출될 때 THEN 시스템은 최소 30자 이상의 유효한 텍스트인지 검증해야 합니다
2. WHEN 추출된 내용에 불필요한 텍스트가 포함될 때 THEN 시스템은 '로그인', '메뉴', '댓글' 등의 UI 요소 텍스트를 제거해야 합니다
3. WHEN 내용 추출이 완전히 실패할 때 THEN 시스템은 제목과 URL만으로도 게시물을 저장하고 실패 사유를 명시해야 합니다
4. WHEN 추출된 내용이 2000자를 초과할 때 THEN 시스템은 내용을 적절히 잘라서 저장해야 합니다

### Requirement 5

**User Story:** 크롤러 운영자로서, 다양한 네이버 카페의 레이아웃 변화에 대응할 수 있는 유연한 추출 시스템을 원합니다. 그래야 카페별 특성에 관계없이 안정적으로 크롤링할 수 있습니다.

#### Acceptance Criteria

1. WHEN 새로운 에디터 형식을 만날 때 THEN 시스템은 우선순위가 있는 선택자 목록을 순차적으로 시도해야 합니다
2. WHEN 모든 기본 선택자가 실패할 때 THEN 시스템은 DOM 트리를 순회하여 텍스트 노드를 직접 수집해야 합니다
3. WHEN 특정 카페에서 지속적으로 추출이 실패할 때 THEN 시스템은 해당 카페에 특화된 선택자를 추가할 수 있는 구조를 제공해야 합니다
4. WHEN 네이버의 보안 정책 변화로 접근이 제한될 때 THEN 시스템은 User-Agent 변경, 대기 시간 조정 등의 우회 방법을 시도해야 합니다