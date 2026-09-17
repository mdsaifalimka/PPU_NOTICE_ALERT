import os
import re
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_samarth_admission_notices(page):
    """ppupadm.samarth.edu.in admission portal"""
    notices = []
    try:
        page.goto(
            "https://ppupadm.samarth.edu.in/index.php/notifications/index",
            timeout=60000,
            wait_until="networkidle"
        )
        page.wait_for_timeout(3000)

        soup = BeautifulSoup(page.content(), "html.parser")
        
        # Samarth portal ke table rows
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                # Text aur link search karna
                a_tag = row.find("a", href=True)
                if a_tag:
                    title_text = row.get_text(" ", strip=True)
                    url = a_tag.get("href", "").strip()
                    if not url.startswith("http"):
                        url = "https://ppupadm.samarth.edu.in" + (url if url.startswith("/") else "/" + url)

                    # Date match karna
                    date_match = re.search(r"(\d{2}[-/.]\d{2}[-/.]\d{4})", title_text)
                    date_val = date_match.group(1) if date_match else "Admission Notice"

                    # Saaf title banana
                    clean_title = a_tag.get_text(" ", strip=True)
                    if not clean_title or len(clean_title) < 5:
                        clean_title = cols[-1].get_text(" ", strip=True)

                    notices.append({
                        "title": clean_title,
                        "date": date_val,
                        "url": url,
                        "source": "Samarth Admission Portal"
                    })
    except Exception as e:
        print(f"Error fetching Samarth: {e}")

    return notices


def fetch_main_ppu_notices(page):
    """ppup.ac.in/notice-board"""
    notices = []
    try:
        page.goto(
            "https://ppup.ac.in/notice-board",
            timeout=60000,
            wait_until="domcontentloaded"
        )
        page.wait_for_timeout(3000)

        soup = BeautifulSoup(page.content(), "html.parser")
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            if not any(term in href.lower() for term in ["/details/", ".pdf", "/upload/"]):
                continue

            title = link.get_text(" ", strip=True)
            if not title or len(title) < 5:
                continue

            url = href if href.startswith("http") else "https://ppup.ac.in" + (href if href.startswith("/") else "/" + href)
            parent = link.find_parent("li")
            text = parent.get_text(" ", strip=True) if parent else link.parent.get_text(" ", strip=True)
            date_match = re.search(r"(\d{2}[-./]\d{2}[-./]\d{4})", text)
            date = date_match.group(1) if date_match else "General Circular"

            notices.append({
                "title": title,
                "date": date,
                "url": url,
                "source": "PPU Notice Board"
            })
    except Exception as e:
        print(f"Error fetching Main PPU: {e}")

    return notices


def get_latest_notice():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        samarth_list = fetch_samarth_admission_notices(page)
        main_list = fetch_main_ppu_notices(page)

        browser.close()

    all_notices = samarth_list + main_list

    if not all_notices:
        raise Exception("No notices found on either portal")

    return all_notices[0]


def send_telegram(notice):
    message = (
        f"🔔 <b>NEW PPU ALERT</b> ({notice.get('source', 'PPU')})\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Date: {html.escape(notice['date'])}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">Open Notice / PDF</a>"
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
    notice = get_latest_notice()
    current_id = notice["url"]

    old_id = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_id = f.read().strip()

    print(f"Latest notice picked: {notice['title']} -> {current_id}")

    if current_id != old_id:
        send_telegram(notice)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(current_id)
        print("Sent to Telegram!")
    else:
        print("No new notice.")


if __name__ == "__main__":
    main()
