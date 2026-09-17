import os
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_samarth(page):
    notices = []
    try:
        page.goto("https://ppupadm.samarth.edu.in/", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # 1. Marquee / Flash Alerts
        marquee_items = page.locator("marquee a, .marquee a, marquee, .flash-news a").all()
        for item in marquee_items:
            text = item.inner_text().strip()
            if text and len(text) > 8 and any(k in text.lower() for k in ["merit", "pg", "admission", "notice", "list", "cutoff"]):
                href = item.get_attribute("href") or ""
                url = href if href.startswith("http") else ("https://ppupadm.samarth.edu.in" + href if href else "https://ppupadm.samarth.edu.in/")
                notices.append({"title": " ".join(text.split()), "url": url, "source": "Samarth Admission Portal"})

        # 2. General Links with Merit / PG keywords
        all_links = page.locator("a").all()
        for link in all_links:
            text = link.inner_text().strip()
            href = link.get_attribute("href") or ""
            if text and any(k in text.lower() for k in ["merit", "pg admission", "selection list", "pg merit"]):
                url = href if href.startswith("http") else ("https://ppupadm.samarth.edu.in" + href if href else "https://ppupadm.samarth.edu.in/")
                notices.append({"title": " ".join(text.split()), "url": url, "source": "Samarth Admission Portal"})
    except Exception as e:
        print(f"Samarth scrape error: {e}")

    return notices


def fetch_ppu_board(page):
    notices = []
    try:
        page.goto("https://ppup.ac.in/notice-board", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(" ", strip=True)
            if title and len(title) > 8 and ("/details/" in href or "notice" in href.lower() or href.endswith(".pdf")):
                full = href if href.startswith("http") else "https://ppup.ac.in" + (href if href.startswith("/") else "/" + href)
                notices.append({"title": title, "url": full, "source": "PPU Main Board"})
    except Exception as e:
        print(f"PPU board scrape error: {e}")

    return notices


def send_telegram(notice):
    msg = (
        f"🔔 <b>NEW PPU ALERT</b>\n"
        f"📌 <i>Source: {notice['source']}</i>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View Notice / List</a>"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": False}, timeout=25)
    res.raise_for_status()


def main():
    collected = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        collected.extend(fetch_samarth(page))
        collected.extend(fetch_ppu_board(page))
        browser.close()

    if not collected:
        print("No notices found.")
        return

    # Store sent URLs to avoid duplicates
    seen = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            seen = set(line.strip() for line in f if line.strip())

    sent_any = False
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        for item in collected:
            key = item["url"]
            if key not in seen:
                send_telegram(item)
                seen.add(key)
                f.write(key + "\n")
                sent_any = True
                print(f"Sent: {item['title']}")

    if not sent_any:
        print("No new notices found, all previous items already alerted.")


if __name__ == "__main__":
    main()
