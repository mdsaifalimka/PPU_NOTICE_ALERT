import os
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_latest_notice():
    # Target 1: PPU Examination Portal (Always accessible, plain tables)
    urls = [
        "https://ppuponline.in/",
        "https://ppup.ac.in/notice-board"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")

        for target_url in urls:
            try:
                page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                soup = BeautifulSoup(page.content(), "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    title = a.get_text(" ", strip=True)

                    if not href or len(title) < 8:
                        continue

                    # Filter out nav links
                    if any(x in href.lower() for x in [".pdf", "notice", "circular", "download", "view"]):
                        base = "https://ppuponline.in" if "ppuponline" in target_url else "https://ppup.ac.in"
                        full_url = href if href.startswith("http") else base + ("" if href.startswith("/") else "/") + href
                        
                        browser.close()
                        return {
                            "title": title,
                            "url": full_url,
                            "source": "PPU Portal"
                        }
            except Exception as e:
                print(f"Failed {target_url}: {e}")

        browser.close()
    return None


def send_telegram(notice):
    msg = (
        "🔔 <b>NEW PPU NOTICE ALERT</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View Notice Document</a>"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=25)
    res.raise_for_status()


def main():
    notice = fetch_latest_notice()
    if not notice:
        print("No notice found across portals.")
        return

    unique_key = notice["url"]
    old_key = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_key = f.read().strip()

    print(f"Captured: {notice['title']} -> {unique_key}")

    if unique_key != old_key:
        send_telegram(notice)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(unique_key)
        print("Telegram message delivered successfully!")
    else:
        print("Notice already sent.")


if __name__ == "__main__":
    main()
