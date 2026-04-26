import asyncio
import json
import os
import html
from datetime import datetime, timezone
from email.utils import format_datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list?ima=0000"
DATA_FILE = "data.json"
FEED_FILE = "feed.xml"
MEMBER_DIR = "members"

os.makedirs(MEMBER_DIR, exist_ok=True)

# ----------------------
# XMLエスケープ（最重要）
# ----------------------
def esc(text):
    return html.escape(text or "", quote=True)

# ----------------------
# データ読み込み
# ----------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# ----------------------
# データ保存
# ----------------------
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------------
# 日付パース
# ----------------------
def parse_date(text):
    if not text:
        return datetime.now().isoformat()

    text = text.strip()

    for fmt in [
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d"
    ]:
        try:
            return datetime.strptime(text, fmt).isoformat()
        except:
            continue

    return datetime.now().isoformat()

# ----------------------
# 記事ページから日付取得
# ----------------------
async def fetch_date(context, url):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # 優先：timeタグ
        el = page.locator("time")
        if await el.count():
            text = await el.first.text_content()
            return parse_date(text)

        # fallback
        el = page.locator("p")
        if await el.count():
            text = await el.first.text_content()
            return parse_date(text)

    except:
        pass
    finally:
        await page.close()

    return datetime.now().isoformat()

# ----------------------
# スクレイピング
# ----------------------
async def scrape():
    print("アクセス中...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
        )

        page = await context.new_page()

        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        entries = page.locator('a[href*="/diary/detail/"]')
        count = await entries.count()

        print("検出リンク数:", count)

        items = []

        for i in range(count):
            try:
                link = entries.nth(i)

                href = await link.get_attribute("href")
                title = await link.text_content()

                if not href:
                    continue

                parent = link.locator("xpath=ancestor::li[1]")

                name = "unknown"
                try:
                    name_el = parent.locator("p")
                    if await name_el.count():
                        name = (await name_el.first.text_content()).strip()
                except:
                    pass

                url_full = "https://www.nogizaka46.com" + href

                # 日付取得
                date = await fetch_date(context, url_full)

                items.append({
                    "title": (title or "").strip(),
                    "link": url_full,
                    "member": name,
                    "date": date
                })

            except Exception as e:
                print("取得エラー:", e)

        await browser.close()

    print(f"取得数: {len(items)}")
    return items

# ----------------------
# RSS生成（Feedly完全対応）
# ----------------------
def generate_rss(items):
    rss = '<?xml version="1.0" encoding="UTF-8"?>\n'
    rss += '<rss version="2.0">\n<channel>\n'
    rss += '<title>Nogizaka Blog</title>\n'
    rss += '<link>https://www.nogizaka46.com/</link>\n'
    rss += '<description>Nogizaka Member Blog</description>\n'

    for item in items:
        dt = datetime.fromisoformat(item["date"]).astimezone(timezone.utc)
        pubdate = format_datetime(dt)

        rss += "<item>\n"
        rss += f"<title>{esc(item['title'])}</title>\n"
        rss += f"<link>{esc(item['link'])}</link>\n"
        rss += f"<guid>{esc(item['link'])}</guid>\n"
        rss += f"<pubDate>{pubdate}</pubDate>\n"
        rss += f"<description>{esc(item['member'])}</description>\n"
        rss += "</item>\n"

    rss += "</channel>\n</rss>"

    with open(FEED_FILE, "w") as f:
        f.write(rss)

# ----------------------
# メンバー別RSS
# ----------------------
def generate_member_rss(items):
    members = {}

    for item in items:
        members.setdefault(item["member"], []).append(item)

    for member, posts in members.items():
        safe_name = member.replace(" ", "_").replace("/", "_")
        path = f"{MEMBER_DIR}/{safe_name}.xml"

        rss = '<?xml version="1.0" encoding="UTF-8"?>\n'
        rss += '<rss version="2.0">\n<channel>\n'
        rss += f'<title>{esc(member)} Blog</title>\n'

        for item in posts:
            rss += "<item>\n"
            rss += f"<title>{esc(item['title'])}</title>\n"
            rss += f"<link>{esc(item['link'])}</link>\n"
            rss += "</item>\n"

        rss += "</channel>\n</rss>"

        with open(path, "w") as f:
            f.write(rss)

# ----------------------
# メイン
# ----------------------
async def main():
    new_items = await scrape()
    old_items = load_data()

    links = {item["link"] for item in old_items}
    merged = old_items.copy()

    for item in new_items:
        if item["link"] not in links:
            merged.insert(0, item)

    merged = merged[:50]

    save_data(merged)
    generate_rss(merged)
    generate_member_rss(merged)

    print("RSS作成完了")

# ----------------------
if __name__ == "__main__":
    asyncio.run(main())
