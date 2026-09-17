import os
import html
import requests
from bs4 import BeautifulSoup

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_samarth_admission_notices():
    """Samarth Admission Portal (ppupadm.samarth.edu.in) se notices nikalna"""
    notices = []
    url = "https://ppupadm.samarth.edu.in/index.php/notifications/index"
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table")
            if table:
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 3:
                        # Column 0: Published On
                        date = tds[0].get_text(" ", strip=True)
                        # Column 1: Document (Read Notice a tag)
                        link_tag = tds[1].find("a", href=True)
                        # Column 2: Title
                        title = tds[2].get_text(" ", strip=True)

                        if link_tag and title:
                            doc_href = link_tag.get("href", "").strip()
                            if not doc_href.startswith("http"):
                                doc_url = "https://ppupadm.samarth.edu.in" + (doc_href if doc_href.startswith("/") else "/" + doc_href)
                            else:
                                doc_url = doc_href

                            notices.append({
                                "title": title,
                                "date": date,
                                "url": doc_url,
                                "source": "PPU Admission Portal"
                            })
    except Exception as e:
        print(f"Error fetching Samarth notices: {e}")

    return notices


def fetch_main_ppu_notices():
    """Main Website (ppup.ac.in/notice-board) se notices nikalna"""
    notices = []
    url = "https://ppup.ac.in/notice-board"
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a.get("href", "").strip()
                if "/details/" in href:
                    title = a.get_text(" ", strip=True)
                    if title:
                        link_url = href if href.startswith("http") else "https://ppup.ac.in" + href
                        notices.append({
                            "title": title,
                            "date": "General Notice",
                            "url": link_url,
                            "source": "PPU Main Board"
                        })
    except Exception as e:
        print(f"Error fetching Main board: {e}")

    return notices


def get_latest_notice():
    # Pehle Samarth Admission notices check honge (jahan PG 2nd merit list aayi hai)
    samarth_list = fetch_samarth_admission_notices()
    if samarth_list:
        return samarth_list[0]

    # Fallback to main website
    main_list = fetch_main_ppu_notices()
    if main_list:
        return main_list[0]

    raise Exception("No notices found on either portal")


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
    notice = get_latest_notice()
    current_id = notice["url"]

    old_id = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_id = f.read().strip()

    print(f"Fetched latest: {notice['title']} ({current_id})")

    if current_id != old_id:
        send_telegram(notice)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(current_id)
        print("Telegram alert sent successfully!")
    else:
        print("Notice already sent, no duplicate.")


if __name__ == "__main__":
    main()
