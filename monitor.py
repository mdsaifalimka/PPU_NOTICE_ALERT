import os
import html
import requests
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_samarth_notices(page):
    notices = []
    try:
        # Samarth portal open karein
        page.goto("https://ppupadm.samarth.edu.in/index.php/notifications/index", timeout=60000, wait_until="networkidle")
        
        # 'Read Notice' ya 'View Notice' button aane ka intezar karein
        locator = page.locator("text=/Read Notice|View Notice/i").first
        locator.wait_for(timeout=20000)

        # Saare buttons/links collect karein
        buttons = page.locator("a:has-text('Read Notice'), a:has-text('View Notice')").all()

        for btn in buttons:
            href = btn.get_attribute("href")
            if not href:
                continue

            full_url = href if href.startswith("http") else "https://ppupadm.samarth.edu.in" + (href if href.startswith("/") else "/" + href)

            # Us row ka title nikalna
            row = btn.locator("xpath=./ancestor::tr")
            if row.count() > 0:
                row_text = row.inner_text().strip()
            else:
                row_text = btn.locator("xpath=./ancestor::div[contains(@class,'card') or contains(@class,'row') or contains(@class,'item')]").inner_text().strip()

            clean_title = row_text.replace("Read Notice", "").replace("View Notice", "").strip()
            # Faltu newlines hatana
            clean_title = " ".join(clean_title.split())

            notices.append({
                "title": clean_title if clean_title else "PPU Admission Merit / Notice",
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
        f"📢 <b>{html.escape(notice['title'])}</b>\n\n"
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

    print(f"Notice found: {latest['title']} -> {unique_key}")

    if unique_key != old_key:
        send_telegram(latest)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(unique_key)
        print("Telegram alert delivered successfully!")
    else:
        print("Already sent, skipping duplicate.")


if __name__ == "__main__":
    main()
