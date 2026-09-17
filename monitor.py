import os
import html
import json
import requests
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_notices():
    notices = []

    def handle_response(response):
        try:
            if "notifications" in response.url or "notice" in response.url or "json" in response.headers.get("content-type", ""):
                text = response.text()
                data = json.loads(text)
                items = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            title = item.get("title") or item.get("notification_title") or item.get("name")
                            url = item.get("document_url") or item.get("file") or item.get("url")
                            if title and url:
                                full_url = url if url.startswith("http") else "https://ppupadm.samarth.edu.in" + (url if url.startswith("/") else "/" + url)
                                notices.append({"title": title, "url": full_url})
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", handle_response)
        
        try:
            page.goto("https://ppupadm.samarth.edu.in/index.php/notifications/index", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print("Page load warning:", e)
        
        browser.close()

    return notices


def send_telegram(notice):
    msg = (
        "🔔 <b>NEW PPU NOTICE ALERT</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View / Download Notice</a>"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=25)
    res.raise_for_status()


def main():
    notices = fetch_notices()
    
    if not notices:
        print("Still no data via network listener.")
        return

    latest = notices[0]
    unique_key = latest["url"]

    old_key = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_key = f.read().strip()

    print(f"Captured Notice: {latest['title']} -> {unique_key}")

    if unique_key != old_key:
        send_telegram(latest)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(unique_key)
        print("Telegram alert delivered successfully!")
    else:
        print("Duplicate notice skipped.")


if __name__ == "__main__":
    main()
