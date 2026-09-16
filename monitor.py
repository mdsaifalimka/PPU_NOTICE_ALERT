import os
import re
import html
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as c_requests

PPU_URLS = [
    "https://ppup.ac.in/notice-board",
    "https://ppup.ac.in"
]
STATE_FILE = "last_notice.txt"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def get_latest_notice():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://ppup.ac.in/"
    }

    notices = []

    for url in PPU_URLS:
        try:
            response = c_requests.get(
                url,
                impersonate="chrome124",
                timeout=30,
                headers=headers
            )
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "").strip()

                # Details page, direct PDF, ya upload path teeno ko accept karega
                is_valid = any(sub in href.lower() for sub in ["/details/", ".pdf", "/upload/"])
                if not is_valid:
                    continue

                title = link.get_text(" ", strip=True)
                if not title or len(title) < 5:
                    continue

                full_url = href if href.startswith("http") else "https://ppup.ac.in" + (href if href.startswith("/") else "/" + href)

                parent = link.find_parent("li")
                text = parent.get_text(" ", strip=True) if parent else link.parent.get_text(" ", strip=True)

                date_match = re.search(
                    r"(\d{2}[-./]\d{2}[-./]\d{4})",
                    text
                )
                date = date_match.group(1) if date_match else "Official Circular"

                notices.append({
                    "title": title,
                    "date": date,
                    "url": full_url
                })
        except Exception as e:
            print(f"Error checking {url}: {e}")

    if not notices:
        raise Exception("No PPU notices found")

    return notices[0]


def send_telegram(notice):
    message = (
        "🔔 <b>PPU NEW NOTICE</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Date/Tag: {notice['date']}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">Open Notice</a>"
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
