import os
import re
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_main_ppu_notices(context):
    """ppup.ac.in/notice-board se notices nikalne ke liye"""
    notices = []
    try:
        page = context.new_page()
        page.goto("https://ppup.ac.in/notice-board", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()

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
            date = date_match.group(1) if date_match else "Official Circular"

            notices.append({
                "title": title,
                "date": date,
                "url": url,
                "source": "PPU Notice Board"
            })
    except Exception as e:
        print(f"Error fetching main notice board: {e}")

    return notices


def fetch_samarth_admission_notices(context):
    """ppupadm.samarth.edu.in admission portal se notices nikalne ke liye"""
    notices = []
    try:
        page = context.new_page()
        page.goto("https://ppupadm.samarth.edu.in/index.php/notifications/index", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()

        # Samarth portal ke table rows
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                date_text = cols[0].get_text(" ", strip=True)
                link_tag = cols[1].find("a", href=True)
                title_text = cols[2].get_text(" ", strip=True)

                if link_tag and title_text:
                    href = link_tag.get("href", "").strip()
                    url = href if href.startswith("http") else "https://ppupadm.samarth.edu.in" + (href if href.startswith("/") else "/" + href)
                    
                    notices.append({
                        "title": title_text,
                        "date": date_text,
                        "url": url,
                        "source": "PPU Admission Portal"
                    })
    except Exception as e:
        print(f"Error fetching samarth portal: {e}")

    return notices


def get_latest_notice():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        all_notices = []
        # Pehle admission notices check karega
        all_notices.extend(fetch_samarth_admission_notices(context))
        # Fir main website ke notices check karega
        all_notices.extend(fetch_main_ppu_notices(context))

        browser.close()

    if not all_notices:
        raise Exception("No notices found from any PPU portal")

    return all_notices[0]


def send_telegram(notice):
    message = (
        f"🔔 <b>NEW PPU ALERT ({notice.get('source', 'PPU')})</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Date: {notice['date']}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">Open Notice / PDF</a>"
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
