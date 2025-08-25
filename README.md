# 네이버 카페 → 노션 자동 크롤러

네이버 카페 게시물을 자동으로 크롤링하여 노션 데이터베이스에 저장하는 GitHub Actions 기반 자동화 시스템입니다.

## 🚀 주요 기능

- **자동 크롤링**: 매일 9시, 12시, 17시에 자동 실행
- **중복 방지**: 해시값을 이용한 중복 게시물 필터링
- **2개 카페 지원**: 동시에 2개 카페 크롤링 가능
- **노션 자동 저장**: 크롤링한 데이터를 노션 데이터베이스에 자동 저장
- **GitHub Actions**: 서버 없이 무료로 자동화 실행

## 📋 저장되는 데이터

- 제목
- 작성자
- 작성일
- 조회수
- 본문 내용 (최대 2000자)
- 원본 URL
- 게시물 ID
- 카페명
- 크롤링 일시
- 해시값 (중복 체크용)

## 🔧 설정 방법

### 1. 리포지토리 Fork 또는 복사

```bash
git clone https://github.com/yourusername/naver-cafe-notion-crawler.git
cd naver-cafe-notion-crawler
```

### 2. 노션 설정

1. [Notion Integration](https://www.notion.so/my-integrations) 생성
2. Integration Token 복사
3. 노션 데이터베이스 생성 및 Integration 연결
4. 데이터베이스 ID 복사 (URL에서 추출)

### 3. 네이버 카페 정보 수집

각 카페에서 필요한 정보:
- **Club ID**: 카페 URL에서 추출 (예: `https://cafe.naver.com/ArticleList.nhn?search.clubid=12345678`)
- **Board ID**: 게시판 메뉴 ID (URL의 `search.menuid` 값)

### 4. GitHub Secrets 설정

리포지토리 Settings → Secrets and variables → Actions에서 다음 시크릿 추가:

#### 필수 시크릿
```
# 네이버 계정
NAVER_ID: 네이버 아이디
NAVER_PW: 네이버 비밀번호

# 노션 설정
NOTION_TOKEN: secret_로 시작하는 Integration 토큰
NOTION_DATABASE_ID: 데이터베이스 ID

# 카페 1
CAFE1_NAME: 첫 번째 카페 이름
CAFE1_URL: https://cafe.naver.com/cafename1
CAFE1_CLUB_ID: 12345678
CAFE1_BOARD_ID: 1
CAFE1_BOARD_NAME: 자유게시판

# 카페 2
CAFE2_NAME: 두 번째 카페 이름
CAFE2_URL: https://cafe.naver.com/cafename2
CAFE2_CLUB_ID: 87654321
CAFE2_BOARD_ID: 2
CAFE2_BOARD_NAME: 정보게시판
```

### 5. 실행 확인

1. Actions 탭에서 "Naver Cafe Crawler" 워크플로우 확인
2. "Run workflow" 버튼으로 수동 실행 테스트
3. 실행 로그 확인

## 📅 실행 스케줄

- **09:00 KST** (00:00 UTC)
- **12:00 KST** (03:00 UTC)
- **17:00 KST** (08:00 UTC)

수동 실행도 가능합니다 (Actions → Run workflow).

## 🔍 트러블슈팅

### 로그인 실패
- 네이버 2단계 인증 해제 필요
- 보안 문자 발생 시 수동 로그인 후 재시도

### 크롤링 실패
- Club ID, Board ID 재확인
- 카페 회원 가입 여부 확인
- 게시판 접근 권한 확인

### 노션 저장 실패
- Integration 권한 확인
- 데이터베이스 ID 정확성 확인
- 데이터베이스 필드 구조 확인

## 📊 노션 데이터베이스 필수 필드

다음 필드들이 노션 데이터베이스에 있어야 합니다:

| 필드명 | 타입 | 설명 |
|--------|------|------|
| 제목 | Title | 게시물 제목 |
| URL | URL | 원본 링크 |
| 작성자 | Text | 작성자 이름 |
| 작성일 | Date | 작성 날짜 |
| 카페명 | Select | 카페 이름 |
| 내용 | Text | 본문 내용 |
| 크롤링 일시 | Date | 크롤링 시간 |
| 조회수 | Number | 조회수 |
| 게시물 ID | Text | 고유 ID |
| 해시 | Text | 중복 체크용 |
| uploaded | Checkbox | 업로드 상태 |

## 📝 라이센스

MIT License

## 🤝 기여

Issue와 Pull Request는 언제나 환영합니다!

## ⚠️ 주의사항

- 네이버 카페 이용약관을 준수하세요
- 과도한 크롤링은 계정 제재 위험이 있습니다
- 개인정보가 포함된 게시물 처리에 주의하세요
- GitHub Actions 무료 사용량 제한 확인 (매월 2,000분)