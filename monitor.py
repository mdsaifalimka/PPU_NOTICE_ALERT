import os
import re
import html
import requests
from bs4 import BeautifulSoup

PPU_URL = "https://ppup.ac.in/notice-board"
STATE_FILE = "last_notice.txt"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def get_latest_notice():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://ppup.ac.in/",
        "Connection": "keep-alive"
    }

    session = requests.Session()
    response = session.get(
        PPU_URL,
        timeout=30,
        headers=headers
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    notices = []

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()

        if "/details/" not in href:
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        if href.startswith("http"):
            url = href
        else:
            url = "https://ppup.ac.in" + href

        parent = link.find_parent("li")

        if parent:
            text = parent.get_text(" ", strip=True)
        else:
            text = link.parent.get_text(" ", strip=True)

        date_match = re.search(
            r"Updated\s*On\s*:?\s*(\d{2}-\d{2}-\d{4})",
            text,
            re.IGNORECASE
        )

        date = date_match.group(1) if date_match else "Date not available"

        notices.append({
            "title": title,
            "date": date,
            "url": url
        })

    if not notices:
        raise Exception("No PPU notices found")

    return notices[0]


def send_telegram(notice):
    message = (
        "🔔 <b>PPU NEW NOTICE</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Updated: {notice['date']}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">"
        "Open Notice</a>"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


def main():
    notice = get_latest_notice()
    current_id = notice["url"]

    old_id = ""

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_id = f.read().strip()

    if current_id != old_id:
        send_telegram(notice)

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(current_id)

        print("New notice sent:", notice["title"])
    else:
        print("No new notice.")


if __name__ == "__main__":
    main()
    
