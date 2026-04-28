import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"

DATA_FILE = "data.json"
MEMBER_DIR = "members"

FETCH_LIMIT = 50
MAX_ITEMS = 30

# --------------------------
# 初期化
# --------------------------
os.makedirs(MEMBER_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


# --------------------------
# データ
# --------------------------
def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------
# URL正規化
# --------------------------
def normalize_url(url):
    return url.split("?")[0]


# --------------------------
# 名前取得（安定版）
# --------------------------
async def get_member_name(page):
    try:
        await page.wait_for_selector("text=公式ブログ", timeout=10000)
        text = await page.locator("text=公式ブログ").inner_text()

        m = re.search(r"(.+?)\s*公式ブログ", text)
        if m:
            return m.group(1).strip()

        return "unknown"
    except:
        return "unknown"


# --------------------------
# スクレイプ（完全版）
# --------------------------
async def scrape(page, context):

    items = []

    await page.goto(BASE_URL, timeout=60000)
    await page.wait_for_selector("a[href*='/diary/detail/']")

    links = await page.locator("a[href*='/diary/detail/']").all()

    urls = []
    for a in links[:FETCH_LIMIT]:
        href = await a.get_attribute("href")
        if href:
            urls.append("https://www.nogizaka46.com" + href)

    for url in urls:
        detail = await context.new_page()
        await detail.goto(url, timeout=60000)

        html = await detail.content()
        body_text = await detail.inner_text("body")

        # タイトル
        title = "no title"
        t = re.search(r"<title>(.*?)</title>", html, re.S)
        if t:
            title = t.group(1).strip()

        # 日付
        date = "unknown"
        m = re.search(r"\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", body_text)
        if m:
            date = m.group(0)

        # 名前
        name = await get_member_name(detail)

        print(f"URL: {url}")
        print(f"取得: {title} / {name} / {date}")

        items.append({
            "title": title,
            "url": url,
            "date": date,
            "member": name
        })

        await detail.close()

    return items


# --------------------------
# 差分
# --------------------------
def diff(new, old):
    old_urls = set(normalize_url(x["url"]) for x in old)
    return [x for x in new if normalize_url(x["url"]) not in old_urls]


# --------------------------
# メンバー別保存
# --------------------------
def save_by_member(items):
    for item in items:
        name = item["member"] or "unknown"
        safe = name.replace(" ", "").replace("/", "_")

        path = os.path.join(MEMBER_DIR, f"{safe}.json")

        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
        else:
            data = []

        urls = set(normalize_url(x["url"]) for x in data)

        if normalize_url(item["url"]) in urls:
            continue

        data.insert(0, item)
        data = data[:MAX_ITEMS]

        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------
# RSS生成
# --------------------------
def generate_rss(items):
    rss_items = ""

    for item in items:
        rss_items += f"""
        <item>
            <title>{item['title']}</title>
            <link>{item['url']}</link>
            <pubDate>{item['date']}</pubDate>
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Nogizaka Blog</title>
<link>{BASE_URL}</link>
<description>乃木坂ブログRSS</description>
{rss_items}
</channel>
</rss>
"""

    with open("rss.xml", "w") as f:
        f.write(rss)


# --------------------------
# メイン
# --------------------------
async def main():
    old_data = load_data()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context()
        page = await context.new_page()

        new_items = await scrape(page, context)

        new_only = diff(new_items, old_data)

        print("新規:", len(new_only))

        new_urls = set(normalize_url(n["url"]) for n in new_only)

        all_data = new_only + [
            x for x in old_data
            if normalize_url(x["url"]) not in new_urls
        ]

        save_data(all_data)

        if new_only:
            save_by_member(new_only)

        generate_rss(all_data[:50])

        await browser.close()

    print("✅ 完全版RSS作成完了")


# --------------------------
# 実行
# --------------------------
if __name__ == "__main__":
    asyncio.run(main())