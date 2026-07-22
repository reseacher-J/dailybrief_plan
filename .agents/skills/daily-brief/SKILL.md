---
name: daily-brief
description: 매일 오전 10시 뉴스·보도자료 요약 및 Gmail 자동 발송 서비스 관리 및 테스트 실행 스킬
---

# 데일리브리프 (Daily Brief) 스킬

이 스킬은 매일 주요 이슈(기획예산처, 공공투자·지방재정, 부산 시정 현안, AI 기술 동향, 거시경제 및 건설경기)를 수집하고 요약하여 Gmail로 메일을 발송하는 자동화 서비스를 관리하고 실행하는 스킬입니다.

## 주요 기능

1. **테스트 실행**:
   - `python daily_brief.py --test` 명령으로 메일을 전송하지 않고 로컬에 미리보기 HTML 및 요약 결과를 생성합니다.
2. **즉시 실행 & 발송**:
   - `python daily_brief.py` 명령으로 뉴스를 즉시 수집하여 `goodman0410@gmail.com`으로 발송합니다.
3. **수집 규칙 변경**:
   - `brief-spec.md` 파일을 수정하여 수집 소스, 주제 키워드 및 요약 스타일을 변경할 수 있습니다.

## 실행 명령어

```bash
# 1. 의존성 패키지 설치
pip install -r requirements.txt

# 2. 로컬 프리뷰 테스트 (메일 발송 안 함)
python daily_brief.py --test

# 3. 브리프 수집 및 메일 직접 발송
python daily_brief.py
```
