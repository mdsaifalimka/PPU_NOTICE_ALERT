import os
import re
import html
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_samarth_admission_notices(context):
    """ppupadm.samarth.edu.in portal se notices nikalne ke liye"""
    notices = []
    try:
        page = context.new_page()
        page.goto("https://ppupadm.samarth.edu.in/index.php/notifications/index", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()

        # Samarth table ke sabhi rows
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                date_text = cols[0].get_text(" ", strip=True)
                
                # Document link dhundhna
                link_tag = cols[1].find("a", href=True)
                title_tag = cols[2]
                title_text = title_tag.get_text(" ", strip=True)

                if link_tag and title_text:
                    url = link_tag.get("href", "").strip()
                    if not url.startswith("http"):
                        url = "https://ppupadm.samarth.edu.in" + (url if url.startswith("/") else "/" + url)
                    
                    notices.append({
                        "title": title_text,
                        "date": date_text,
                        "url": url,
                        "source": "Samarth Admission Portal"
                    })
    except Exception as e:
        print(f"Error fetching Samarth portal: {e}")

    return notices


def fetch_main_ppu_notices(context):
    """ppup.ac.in/notice-board se notices nikalne ke liye"""
    notices = []
    try:
        page = context.new_page()
        page.goto("https://ppup.ac.in/notice-board", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
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
        print(f"Error fetching main PPU board: {e}")

    return notices


def get_latest_notice():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        # Samarth admission portal ke notices
        samarth_notices = fetch_samarth_admission_notices(context)
        # Main website ke notices
        main_notices = fetch_main_ppu_notices(context)

        browser.close()

    # Pehle Samarth ke notices check honge kyunki admission/merit wahi aate hain
    if samarth_notices:
        return samarth_notices[0]
    elif main_notices:
        return main_notices[0]
    else:
        raise Exception("No notices found from any PPU portal")


def send_telegram(notice):
    message = (
        f"🔔 <b>NEW PPU ALERT</b> ({notice.get('source', 'PPU')})\n\n"
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
