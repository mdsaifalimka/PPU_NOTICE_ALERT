
import os
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_samarth_notices(page):
    notices = []
    try:
        # Samarth portal open karna
        page.goto("https://ppupadm.samarth.edu.in/index.php/notifications/index", timeout=60000, wait_until="networkidle")
        page.wait_for_selector("table", timeout=15000)
        page.wait_for_timeout(2000)

        soup = BeautifulSoup(page.content(), "html.parser")
        table = soup.find("table")

        if table:
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    # Column 1: Date
                    date_val = tds[0].get_text(" ", strip=True)
                    
                    # Column 2: Document Link (Read Notice / View Notice)
                    a_tag = tds[1].find("a", href=True)
                    
                    # Column 3: Title
                    title_val = tds[2].get_text(" ", strip=True)

                    if a_tag and title_val:
                        link_href = a_tag.get("href", "").strip()
                        if not link_href.startswith("http"):
                            full_url = "https://ppupadm.samarth.edu.in" + (link_href if link_href.startswith("/") else "/" + link_href)
                        else:
                            full_url = link_href

                        notices.append({
                            "title": title_val,
                            "date": date_val,
                            "url": full_url,
                            "source": "Samarth Admission Portal"
                        })
    except Exception as e:
        print(f"Samarth fetch error: {e}")

    return notices


def send_telegram(notice):
    message = (
        f"🔔 <b>NEW PPU NOTICE ALERT</b>\n"
        f"📌 <i>Source: {notice['source']}</i>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Date: {html.escape(notice['date'])}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View / Download Notice</a>"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        },
        timeout=25
    )
    res.raise_for_status()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        notices = fetch_samarth_notices(page)
        browser.close()

    if not notices:
        print("No notices found from Samarth portal.")
        return

    latest = notices[0]
    unique_key = latest["url"]

    old_key = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_key = f.read().strip()

    print(f"Latest notice picked: {latest['title']} ({unique_key})")

    if unique_key != old_key:
        send_telegram(latest)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(unique_key)
        print("Alert sent to Telegram successfully!")
    else:
        print("Notice already sent, no new update.")


if __name__ == "__main__":
    main()
