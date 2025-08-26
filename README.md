# 네이버 카페 크롤러 → 노션 자동 저장

F-E 카페의 게시물을 자동으로 크롤링하여 노션 데이터베이스에 저장하는 시스템입니다.

## 🚀 주요 기능

- **자동 스케줄링**: GitHub Actions를 통해 매일 오전 9시, 오후 5시 자동 실행
- **강화된 콘텐츠 추출**: 다양한 에디터 형식(SmartEditor 2.0/3.0, 일반 에디터) 지원
- **품질 검증**: 추출된 내용의 품질 검증 및 정제
- **중복 방지**: URL 기반 중복 게시물 자동 필터링
- **디버깅 지원**: 실패 시 상세한 로그 및 스크린샷 저장

## 📋 노션 데이터베이스 구조

다음 필드들이 필요합니다:

| 필드명 | 타입 | 설명 |
|--------|------|------|
| 이름 | Title | 게시물 제목 |
| 작성자 | Rich Text | 게시물 작성자 |
| 작성일 | Rich Text | 게시물 작성일 |
| URL | URL | 게시물 링크 |
| 내용 | Rich Text | 게시물 내용 |
| uploaded | Checkbox | 업로드 상태 (기본값: false) |

## ⚙️ 설정 방법

### 1. 환경변수 설정

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```bash
# 네이버 계정 정보
NAVER_ID=your_naver_id
NAVER_PW=your_naver_password

# 노션 API 설정
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxx

# 콘텐츠 추출 설정 (선택사항)
CONTENT_EXTRACTION_TIMEOUT=30
CONTENT_MIN_LENGTH=30
CONTENT_MAX_LENGTH=2000
DEBUG_SCREENSHOT_ENABLED=true
EXTRACTION_RETRY_COUNT=3
```

### 2. GitHub Secrets 설정

GitHub Actions 사용을 위해 다음 Secrets를 설정하세요:

- `NAVER_ID`: 네이버 아이디
- `NAVER_PW`: 네이버 비밀번호
- `NOTION_TOKEN`: 노션 API 토큰
- `NOTION_DATABASE_ID`: 노션 데이터베이스 ID

## 🎯 대상 카페

현재 **F-E 카페**를 대상으로 설정되어 있습니다:
- 카페 URL: https://cafe.naver.com/f-e
- 게시판: https://cafe.naver.com/f-e/cafes/18786605/menus/105?viewType=L

## 🔧 사용 방법

### 로컬 실행

1. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```

2. **노션 연결 테스트**:
   ```bash
   python test_full_crawling.py
   # 1번 선택: 노션 연결 테스트만
   ```

3. **전체 크롤링 테스트**:
   ```bash
   python test_full_crawling.py
   # 2번 선택: 전체 크롤링 테스트
   ```

4. **실제 크롤링 실행**:
   ```bash
   python main.py
   ```

### GitHub Actions 자동 실행

- **스케줄**: 매일 오전 9시, 오후 5시 (한국시간)
- **수동 실행**: GitHub Actions 탭에서 "Run workflow" 클릭

## 🏗️ 시스템 아키텍처

### 핵심 컴포넌트

1. **ContentExtractor**: 메인 콘텐츠 추출 클래스
2. **PreloadingManager**: 동적 콘텐츠 로딩 관리
3. **SelectorStrategy**: 에디터별 선택자 전략
4. **ContentValidator**: 내용 품질 검증
5. **DebugCollector**: 디버깅 정보 수집

### 추출 전략

1. **SmartEditor 3.0**: `.se-main-container` 등
2. **SmartEditor 2.0**: `.ContentRenderer`, `#postViewArea` 등
3. **일반 에디터**: `#content-area` 등
4. **레거시 에디터**: `#tbody` 등
5. **JavaScript 추출**: DOM 트리 순회
6. **최후 수단**: 페이지 새로고침 후 재시도

## 📊 성능 및 제한사항

- **처리량**: 게시물당 5개씩 크롤링
- **품질 검증**: 최소 30자 이상의 의미있는 콘텐츠만 저장
- **내용 길이**: 최대 2000자로 제한
- **실행 시간**: GitHub Actions 환경에서 약 5-10분 소요

## 🐛 문제 해결

### 일반적인 문제

1. **로그인 실패**:
   - 네이버 계정 정보 확인
   - 2단계 인증 비활성화 필요할 수 있음

2. **내용 추출 실패**:
   - 디버깅 스크린샷 확인 (`artifacts` 폴더)
   - 로그에서 에디터 타입 확인

3. **노션 저장 실패**:
   - 노션 API 토큰 및 데이터베이스 ID 확인
   - 데이터베이스 필드 구조 확인

### 로그 확인

- **로컬**: `crawler.log` 파일
- **GitHub Actions**: Actions 탭의 로그 및 artifacts

## 🔄 업데이트 내역

### v2.0 (최신)
- 모듈화된 아키텍처로 완전 리팩토링
- 다층적 콘텐츠 추출 전략 도입
- 품질 검증 시스템 추가
- GitHub Actions 환경 최적화
- F-E 카페 전용 URL 구조 지원

### v1.0
- 기본 크롤링 기능
- 노션 저장 기능

## 📝 라이선스

MIT License

## 🤝 기여

이슈나 개선사항이 있으시면 GitHub Issues를 통해 알려주세요.

---

**주의**: 이 도구는 개인적인 용도로만 사용하시고, 네이버 카페의 이용약관을 준수해주세요.