import os
import sys
import datetime
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드 (.env 지원)
load_dotenv()

# Windows 콘솔 유니코드 출력 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 기본 설정값
GMAIL_USER = os.getenv("GMAIL_USER", "goodman0410@gmail.com").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "goodman0410@gmail.com").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

ARCHIVE_DIR = Path(__file__).parent / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

# 5대 수집 주제 및 검색 키워드
TOPICS = [
    {
        "id": 1,
        "title": "기획예산처 및 재정 관련 보도자료",
        "keywords": ["기획예산처", "재정경제부 예산", "기획재정부 예산"],
    },
    {
        "id": 2,
        "title": "공공투자·지방재정",
        "keywords": ["지방재정 투자심사", "예비타당성조사", "민간투자사업 BTO BTL"],
    },
    {
        "id": 3,
        "title": "부산 지역 현안",
        "keywords": ["부산시 예산", "부산 개발계획", "부산연구원"],
    },
    {
        "id": 4,
        "title": "AI·기술 동향",
        "keywords": ["공공부문 AI 도입", "AI 모델 출시"],
    },
    {
        "id": 5,
        "title": "거시경제·건설경기",
        "keywords": ["한국은행 기준금리", "SOC 예산", "건설수주 건설자재비"],
    },
]


def get_recent_archive_links():
    """최근 3일치 archive MD 파일에서 이미 다룬 기사 URL 목록을 읽어옵니다."""
    existing_links = set()
    today = datetime.date.today()
    for i in range(1, 4):
        past_date = today - datetime.timedelta(days=i)
        archive_file = ARCHIVE_DIR / f"{past_date.strftime('%Y-%m-%d')}.md"
        if archive_file.exists():
            content = archive_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "http" in line:
                    # 마크다운 링크 또는 일반 URL 추출
                    import re
                    urls = re.findall(r'https?://[^\s\)\]"]+', line)
                    existing_links.update(urls)
    return existing_links


def fetch_google_news_rss(query):
    """Google 뉴스 RSS에서 최신 뉴스 항목을 가져옵니다."""
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(rss_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall("./channel/item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source = item.findtext("source", "").strip()

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "source": source or "뉴스"
                })
        return items[:6]  # 주제당 여유있게 6개까지 수집
    except Exception as e:
        print(f"[-] RSS 수집 중 오류 ({query}): {e}")
        return []


def collect_all_news():
    """5개 주제별로 뉴스를 수집하고 중복을 제거합니다."""
    existing_links = get_recent_archive_links()
    collected_data = {}

    for topic in TOPICS:
        topic_title = topic["title"]
        collected_data[topic_title] = []
        seen_links = set()

        for kw in topic["keywords"]:
            items = fetch_google_news_rss(kw)
            for item in items:
                link = item["link"]
                if link in existing_links or link in seen_links:
                    continue
                seen_links.add(link)
                collected_data[topic_title].append(item)
                if len(collected_data[topic_title]) >= 5:
                    break
            if len(collected_data[topic_title]) >= 5:
                break

    return collected_data


def summarize_with_gemini(collected_data):
    """Gemini API를 호출하거나 로컬 처리로 핵심 요약 및 개조식 브리프를 생성합니다."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][datetime.date.today().weekday()]
    date_header = f"{today_str} ({weekday_str})"

    prompt = f"""당신은 공공기관 정책 및 뉴스 요약 전문 분석가입니다.
아래의 {date_header} 뉴스 데이터를 바탕으로 데일리브리프를 작성해주세요.

[규칙 및 문체]
- 제목 형식: [데일리브리프] {date_header}
- 1. **오늘의 3줄 요약**: 전체 뉴스 중 가장 중요한 이슈 3가지를 각각 1줄씩 개조식으로 요약
- 2. 주제별 섹션: 5개 주제별로 원문 기사의 핵심을 2문장 내외의 개조식 문체(`□` / `ㅇ` / `-` 서식)로 작성
- 원문 기사의 제목, 출처, 원문 링크(URL)는 그대로 유지해야 합니다.

[수집된 뉴스 데이터]
"""
    has_items = False
    for topic_title, items in collected_data.items():
        prompt += f"\n### 주제: {topic_title}\n"
        if items:
            has_items = True
            for idx, item in enumerate(items, 1):
                prompt += f"{idx}. 제목: {item['title']}\n   출처: {item['source']}\n   링크: {item['link']}\n"
        else:
            prompt += "수집된 신규 뉴스 항목 없음\n"

    if not has_items:
        summary_text = f"# [데일리브리프] {date_header}\n\n## 오늘의 3줄 요약\n- 오늘은 조건에 맞는 신규 뉴스 소식이 없습니다.\n"
        return summary_text

    # Gemini API 호출 시도
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                summary_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return summary_text
            else:
                print(f"[-] Gemini API 오류 ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[-] Gemini API 호출 중 예외: {e}")

    # Fallback (API 키가 없거나 실패 시 수동 개조식 구성)
    summary_text = f"# [데일리브리프] {date_header}\n\n"
    summary_text += "## 📌 오늘의 3줄 요약\n"
    summary_text += f"- {date_header} 주요 뉴스 브리핑입니다.\n"
    summary_text += "- 주요 정책, 공공투자, 부산시 현안 및 AI·거시경제 동향 수집 완료.\n"
    summary_text += "- 각 항목별 링크를 통해 상세 원문을 확인할 수 있습니다.\n\n"

    for topic_title, items in collected_data.items():
        summary_text += f"### □ {topic_title}\n"
        if items:
            for item in items:
                summary_text += f"ㅇ **[{item['title']}]({item['link']})**\n"
                summary_text += f"   - 출처: {item['source']} | [원문보기]({item['link']})\n"
        else:
            summary_text += "   - 신규 보도자료 및 기사가 없습니다.\n"
        summary_text += "\n"

    return summary_text


def convert_markdown_to_html(md_text, date_str):
    """마크다운 요약 텍스트를 보기 좋은 이메일용 HTML 스타일로 변환합니다."""
    import re

    # 간단한 마크다운 HTML 파싱
    lines = md_text.splitlines()
    body_html = ""

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        if line_str.startswith("# "):
            body_html += f"<h1 style='color: #1a365d; font-size: 22px; border-bottom: 2px solid #3182ce; padding-bottom: 8px; margin-top: 20px;'>{line_str[2:]}</h1>"
        elif line_str.startswith("## "):
            body_html += f"<h2 style='color: #2b6cb0; font-size: 17px; margin-top: 18px; background: #ebf8ff; padding: 6px 12px; border-radius: 4px;'>{line_str[3:]}</h2>"
        elif line_str.startswith("### "):
            body_html += f"<h3 style='color: #2d3748; font-size: 15px; margin-top: 14px;'>{line_str[4:]}</h3>"
        elif line_str.startswith("- ") or line_str.startswith("ㅇ ") or line_str.startswith("□ "):
            # 마크다운 링크 [텍스트](URL) -> <a href='URL'>텍스트</a>
            formatted = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #3182ce; text-decoration: none; font-weight: bold;" target="_blank">\1 🔗</a>', line_str)
            formatted = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted)
            body_html += f"<div style='margin-left: 10px; margin-bottom: 6px; font-size: 14px; line-height: 1.6;'>{formatted}</div>"
        else:
            formatted = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #3182ce; text-decoration: none;" target="_blank">\1</a>', line_str)
            formatted = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted)
            body_html += f"<p style='font-size: 14px; line-height: 1.5; color: #4a5568;'>{formatted}</p>"

    full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #f7fafc; padding: 20px; color: #2d3748;">
  <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <div style="text-align: center; padding-bottom: 15px; border-bottom: 1px solid #edf2f7; margin-bottom: 20px;">
      <span style="background: #3182ce; color: white; padding: 4px 10px; font-size: 12px; border-radius: 12px; font-weight: bold;">매일 뉴스 브리프</span>
      <h2 style="margin: 10px 0 0 0; color: #1a202c; font-size: 20px;">데일리브리프 ({date_str})</h2>
    </div>
    
    {body_html}

    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #edf2f7; font-size: 12px; color: #a0aec0; text-align: center;">
      본 이메일은 안티그래비티 데일리브리프 자동화 서비스에 의해 매일 10:00 AM에 발송됩니다.<br>
      수신자: {RECEIVER_EMAIL}
    </div>
  </div>
</body>
</html>
"""
    return full_html


def send_gmail(subject, html_content):
    """Gmail SMTP를 사용하여 메일을 직접 전송합니다."""
    if not GMAIL_APP_PASSWORD:
        print("[!] GMAIL_APP_PASSWORD가 설정되지 않아 메일을 전송하지 않고 건너뜁니다.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = RECEIVER_EMAIL

        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_html)

        print(f"[+] Gmail SMTP 연결 시도 ({GMAIL_USER} -> {RECEIVER_EMAIL})...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, RECEIVER_EMAIL, msg.as_string())
        print("[+] 이메일 발송 완료!")
        return True
    except Exception as e:
        print(f"[-] 이메일 발송 중 오류 발생: {e}")
        sys.exit(1)


def main():
    test_mode = "--test" in sys.argv
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][datetime.date.today().weekday()]

    print(f"[*] [{today_str} ({weekday_str})] 데일리브리프 뉴스 수집 및 발송 프로세스 시작...")

    # 1. 뉴스 수집
    collected_data = collect_all_news()

    # 2. AI 요약 생성
    summary_md = summarize_with_gemini(collected_data)

    # 3. 마크다운 아카이브 보관 (중복 검사용)
    archive_file = ARCHIVE_DIR / f"{today_str}.md"
    archive_file.write_text(summary_md, encoding="utf-8")
    print(f"[+] 마크다운 보관 완료: {archive_file}")

    # 4. HTML 변환
    html_content = convert_markdown_to_html(summary_md, f"{today_str} {weekday_str}")

    subject = f"[데일리브리프] {today_str} ({weekday_str}) 주요 정책·뉴스 브리핑"

    # 5. 테스트 모드인 경우 프리뷰 HTML 파일 작성 및 종료
    if test_mode:
        test_html_file = Path(__file__).parent / "preview_email.html"
        test_html_file.write_text(html_content, encoding="utf-8")
        print(f"[+] 테스트 모드: 이메일을 전송하지 않고 프리뷰 파일 생성됨 -> {test_html_file}")
        print("\n--- [요약 마크다운 내용] ---")
        print(summary_md)
        return

    # 6. 실제 Gmail 발송
    send_gmail(subject, html_content)


if __name__ == "__main__":
    main()
