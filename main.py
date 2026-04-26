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
# エスケープ
# ----------------------
def esc(text):
    return html.escape(str(text or ""), quote=True)

def cdata(text):
    t = str(text or "")
    t = t.replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{t}]]>"

# ----------------------
# データ
# ----------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------------
# 日付
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

async def fetch_date(context, url):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1200)

        el = page.locator("time")
        if await el.count():
            return parse_date(await el.first.text_content())

        el = page.locator("p")
        if await el.count():
            return parse_date(await el.first.text_content())

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
            user_agent="Mozilla/5.0"
        )

        page = await context.new_page()

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

                # 🔥 タイトル修正（ここ重要）
                title_raw = await link.text_content()
                title_lines = (title_raw or "").strip().split("\n")
                title = title_lines[0].strip() if title_lines else ""

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

                date = await fetch_date(context, url_full)

                items.append({
                    "title": title,
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
# RSS生成
# ----------------------
def generate_rss(items):
    rss = '<?xml version="1.0" encoding="UTF-8"?>\n'
    rss += '<rss version="2.0">\n<channel>\n'
    rss += f'<title>{cdata("Nogizaka Blog")}</title>\n'
    rss += f'<link>{esc("https://www.nogizaka46.com/")}</link>\n'
    rss += f'<description>{cdata("Nogizaka Member Blog")}</description>\n'

    for item in items:
        dt = datetime.fromisoformat(item["date"]).astimezone(timezone.utc)
        pubdate = format_datetime(dt)

        rss += "<item>\n"
        rss += f"<title>{cdata(item['title'])}</title>\n"
        rss += f"<link>{esc(item['link'])}</link>\n"
        rss += f"<guid>{esc(item['link'])}</guid>\n"
        rss += f"<pubDate>{esc(pubdate)}</pubDate>\n"
        rss += f"<description>{cdata(item['member'])}</description>\n"
        rss += "</item>\n"

    rss += "</channel>\n</rss>"

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        f.write(rss)

# ----------------------
# メンバーRSS
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
        rss += f'<title>{cdata(member + " Blog")}</title>\n'

        for item in posts:
            rss += "<item>\n"
            rss += f"<title>{cdata(item['title'])}</title>\n"
            rss += f"<link>{esc(item['link'])}</link>\n"
            rss += "</item>\n"

        rss += "</channel>\n</rss>"

        with open(path, "w", encoding="utf-8") as f:
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
