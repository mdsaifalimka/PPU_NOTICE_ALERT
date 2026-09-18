import os
import re
import html
import hashlib
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def get_hash(text):
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()


def fetch_latest_notices():
    notices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        # 1. Samarth Portal Check
        try:
            page.goto("https://ppupadm.samarth.edu.in/", timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            items = page.locator("marquee a, .marquee a, marquee").all()
            for item in items:
                text = item.inner_text().strip()
                if text and len(text) > 10:
                    href = item.get_attribute("href") or ""
                    url = href if href.startswith("http") else ("https://ppupadm.samarth.edu.in" + href if href else "https://ppupadm.samarth.edu.in/")
                    clean_text = " ".join(text.split())
                    notices.append({
                        "title": clean_text,
                        "date": "Samarth Alert",
                        "url": url,
                        "source": "Samarth Portal",
                        "uid": get_hash(clean_text)
                    })
                    break
        except Exception as e:
            print("Samarth fetch error:", e)

        # 2. Main PPU Notice Board Check
        try:
            page.goto("https://ppup.ac.in/notice-board", timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Ignore list: Header/Nav links jo galti se match ho jate hain
            bad_keywords = ["admission-notice", "javascript:", "#", "tel:", "mailto:"]

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                title = a.get_text(" ", strip=True)

                if any(bad in href.lower() for bad in bad_keywords):
                    continue

                # Notice list items me aksar /details/ ya .pdf hota hai, ya parent container me 'Updated On' hota hai
                parent = a.find_parent("li") or a.find_parent("tr") or a.parent
                p_text = parent.get_text(" ", strip=True) if parent else ""

                has_date = bool(re.search(r"Updated\s*On", p_text, re.IGNORECASE))
                is_notice_link = "/details/" in href or href.lower().endswith(".pdf") or "download" in href.lower()

                if (is_notice_link or has_date) and len(title) > 5:
                    date_match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})", p_text)
                    date_val = date_match.group(1) if date_match else "Latest"

                    if href.startswith("http"):
                        full_url = href
                    else:
                        full_url = "https://ppup.ac.in" + (href if href.startswith("/") else "/" + href)

                    clean_title = " ".join(title.split())
                    uid_str = f"{clean_title}_{date_val}_{full_url}"

                    notices.append({
                        "title": clean_title,
                        "date": date_val,
                        "url": full_url,
                        "source": "PPU Notice Board",
                        "uid": get_hash(uid_str)
                    })
                    break
        except Exception as e:
            print("PPU board fetch error:", e)

        browser.close()

    return notices


def send_telegram(notice):
    message = (
        f"🔔 <b>NEW PPU ALERT</b>\n"
        f"📌 <i>Source: {notice['source']}</i>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Updated: {notice['date']}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View Notice / Download</a>"
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
    notices = fetch_latest_notices()
    if not notices:
        print("No notices found.")
        return

    last_id = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            last_id = f.read().strip()

    latest = notices[0]
    print(f"Checking notice: {latest['title']} ({latest['date']}) -> {latest['url']}")

    if latest["uid"] != last_id:
        send_telegram(latest)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(latest["uid"])
        print("New notice sent to Telegram!")
    else:
        print("No new notice. Already updated.")


if __name__ == "__main__":
    main()
