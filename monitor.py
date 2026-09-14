
import os
import re
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

PPU_URL = "https://ppup.ac.in/notice-board"
STATE_FILE = "last_notice.txt"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def get_latest_notice():
    # Real headless browser chalakar page load karenge
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(PPU_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
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
