
import os
import html
import requests

STATE_FILE = "last_notice.txt"
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "1472421595"


def fetch_notices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://ppupadm.samarth.edu.in/index.php/notifications/index"
    }

    # Samarth portal ka direct notification API URL
    api_url = "https://ppupadm.samarth.edu.in/index.php/notifications/get-all-notifications"
    
    session = requests.Session()
    try:
        # Session establish
        session.get("https://ppupadm.samarth.edu.in/index.php/notifications/index", headers=headers, timeout=25)
        res = session.get(api_url, headers=headers, timeout=25)
        
        if res.status_code == 200 and res.json():
            data = res.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if items and isinstance(items, list):
                top = items[0]
                return {
                    "title": top.get("title") or top.get("notification_title") or "PPU Admission Notice",
                    "url": top.get("document_url") or top.get("file") or "https://ppupadm.samarth.edu.in",
                    "date": top.get("published_on") or top.get("created_at") or "Latest"
                }
    except Exception as e:
        print(f"API attempt error: {e}")

    # Fallback via direct page extraction
    from bs4 import BeautifulSoup
    res = session.get("https://ppupadm.samarth.edu.in/index.php/notifications/index", headers=headers, timeout=25)
    soup = BeautifulSoup(res.text, "html.parser")
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "read" in a.text.lower() or "view" in a.text.lower() or ".pdf" in href.lower():
            full = href if href.startswith("http") else "https://ppupadm.samarth.edu.in" + (href if href.startswith("/") else "/" + href)
            return {
                "title": a.get_text(" ", strip=True) or "PPU Admission Notice",
                "url": full,
                "date": "Recent"
            }
    return None


def send_telegram(notice):
    msg = (
        "🔔 <b>NEW PPU NOTICE ALERT</b>\n\n"
        f"📢 <b>{html.escape(notice['title'])}</b>\n"
        f"📅 Date: {html.escape(str(notice.get('date', 'Latest')))}\n\n"
        f"🔗 <a href=\"{html.escape(notice['url'], quote=True)}\">View Notice Document</a>"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=20)
    res.raise_for_status()


def main():
    notice = fetch_notices()
    if not notice:
        print("No notices retrieved.")
        return

    unique_key = notice["url"]
    old_key = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_key = f.read().strip()

    print(f"Fetched notice: {notice['title']} -> {unique_key}")

    if unique_key != old_key:
        send_telegram(notice)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(unique_key)
        print("Alert successfully sent to Telegram!")
    else:
        print("Notice already recorded.")


if __name__ == "__main__":
    main()
