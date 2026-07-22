# 데일리브리프 (Daily Brief)

매일 오전 10시(KST)에 관심 뉴스 및 보도자료를 자동 수집·요약하여 **Gmail 이메일로 직접 발송**해 주는 서버리스 자동화 서비스입니다.
**내 컴퓨터가 꺼져 있어도 클라우드(GitHub Actions)에서 자동으로 실행되어 메일이 도착합니다.**

---

## 🌟 주요 기능

1. **자동 뉴스 수집 & 개조식 요약**:
   - 5대 관심 주제(기획예산처/재정, 공공투자·지방재정, 부산 지역 현안, AI 기술 동향, 거시경제/건설경기) 수집
   - 원문 링크(URL) 필수 수록 및 핵심 내용 2~3줄 개조식 요약
   - 최근 3일치 수집 내역 비교를 통한 중복 뉴스 완전 방지
2. **Gmail 직접 이메일 발송**:
   - 깔끔한 HTML 이메일 양식으로 `goodman0410@gmail.com`에 직접 도착
   - `.docx` 생성 없이 깔끔한 이메일 본문만 제공
3. **컴퓨터 켜둘 필요 없음 (GitHub Actions 연동)**:
   - 매일 오전 10시(KST) 클라우드에서 자동 발송
   - 언제든 GitHub 웹 페이지에서 'Run workflow' 버튼으로 즉시 수동 실행 가능

---

## 🛠️ 구조 및 주요 파일

- `daily_brief.py` — 뉴스 수집, LLM 요약, HTML 생성 및 Gmail SMTP 발송 메인 파이프라인
- `brief-spec.md` — 주제, 키워드, 필터링 및 작성 서식 규칙 (단일 진실 출처)
- `.github/workflows/daily_brief.yml` — 매일 오전 10시 클라우드 자동 발송 워크플로우
- `.agents/skills/daily-brief/SKILL.md` — 안티그래비티 대화창 관리를 위한 커스텀 스킬
- `archive/` — 날짜별 수집 마크다운(`YYYY-MM-DD.md`) 보관함

---

## 🔑 클라우드 자동 발송 설정법 (GitHub Secrets)

이 저장소를 GitHub에 올린 후, **GitHub 저장소 비밀키(Secrets)**에 아래 3가지를 등록하면 내 컴퓨터가 꺼져 있어도 매일 10시에 메일이 발송됩니다:

1. **GitHub 저장소 접속** → `Settings` → `Secrets and variables` → `Actions` → `New repository secret` 클릭
2. 아래 정보 추가:

| Secret 이름 | 설명 | 예시 |
|---|---|---|
| `GMAIL_USER` | 수신/발송용 Gmail 주소 | `goodman0410@gmail.com` |
| `GMAIL_APP_PASSWORD` | Google 계정 보안에서 발급받은 16자리 앱 비밀번호 | `abcd efgh ijkl mnop` |
| `GEMINI_API_KEY` | (선택) Gemini API 키 ([Google AI Studio](https://aistudio.google.com/)에서 무료 발급) | `AIzaSy...` |
| `RECEIVER_EMAIL` | (선택) 수신 이메일 주소 (기본값: `goodman0410@gmail.com`) | `goodman0410@gmail.com` |

---

## 💻 로컬에서 직접 테스트하는 방법

내 컴퓨터에서 바로 뉴스 수집과 메일 발송을 테스트하고 싶다면:

```bash
# 1. 의존성 패키지 설치
pip install -r requirements.txt

# 2. 로컬 테스트 (메일 발송 안 함, preview_email.html 로컬 프리뷰 생성)
python daily_brief.py --test

# 3. 로컬에서 메일 직접 즉시 발송
python daily_brief.py
```

---

## 💡 자주 하는 질문

* **Q. 수집 주제나 검색 키워드를 바꾸고 싶어요.**
  * [`brief-spec.md`](brief-spec.md) 파일이나 `daily_brief.py` 내의 `TOPICS` 배열을 수정하시면 됩니다. 안티그래비티에게 "데일리브리프에 OO 주제 추가해줘"라고 요청하셔도 됩니다.
* **Q. 주말(토/일)에는 메일을 안 받고 싶어요.**
  * `.github/workflows/daily_brief.yml` 파일의 `cron: '0 1 * * *'`를 평일 전용 `cron: '0 1 * * 1-5'`로 변경하시면 됩니다.
