import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"

DATA_FILE = "data.json"
MEMBER_DIR = "members"

FETCH_LIMIT = 50   # 取得数
MAX_ITEMS = 30     # 保存数

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
# 名前取得（最強安定版）
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
# スクレイピング
# --------------------------
async def scrape(page, context):
    print("アクセス中...")

    # 軽量化（画像・CSSカット）
    await context.route("**/*", lambda route, request:
        route.abort() if request.resource_type in ["image", "stylesheet", "font"] else route.continue_()
    )

    await page.goto(BASE_URL, timeout=60000)
    await page.wait_for_timeout(2000)

    links = await page.query_selector_all("a[href*='/diary/detail/']")
    results = []

    # タブ使い回し
    detail = await context.new_page()

    for link in links[:FETCH_LIMIT]:
        try:
            href = await link.get_attribute("href")
            if not href:
                continue

            url = "https://www.nogizaka46.com" + href
            title = (await link.inner_text()).strip()

            await detail.goto(url, timeout=60000)

            # 👇 time取得（fallback付き）
            try:
                await detail.wait_for_selector("time", timeout=3000)
                date = await detail.locator("time").inner_text()
            except:
                try:
                    date = await detail.locator("p[class*='date']").inner_text()
                except:
                    date = "unknown"

            # 👇 名前取得（強化版）
            try:
                name = await detail.locator("p[class*='name']").inner_text()
            except:
                try:
                    name = await detail.locator("h1").inner_text()
                except:
                    name = "unknown"

            print(f"取得: {title} / {name}")

            results.append({
                "title": title,
                "url": url,
                "date": date,
                "member": name
            })

        except Exception as e:
            print("エラー:", e)

    await detail.close()

    print("取得数:", len(results))
    return results


# --------------------------
# 差分
# --------------------------
def diff(new, old):
    old_urls = set(normalize_url(x["url"]) for x in old)
    return [x for x in new if normalize_url(x["url"]) not in old_urls]

# --------------------------
# メンバー別保存
# --------------------------
def normalize_url(url):
    return url.split("?")[0]

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

        # 👇 URL正規化して比較
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

        # 常に最新データ作る
        new_urls = set(normalize_url(n["url"]) for n in new_only)

        all_data = new_only + [
            x for x in old_data
            if normalize_url(x["url"]) not in new_urls
        ]

#   いらねーんだってさ　てめえで入れろっつったくせに
#        all_data = sorted(all_data, key=lambda x: x["date"], reverse=True)

        # 新規があるときだけ保存
        save_data(all_data)

        if new_only:
            save_by_member(new_only)


        # 👇毎回実行（ここだけが今回の修正ポイント）
        generate_rss(all_data[:50])

        await browser.close()

    print("✅ 完全版RSS作成完了")


# --------------------------
# 実行
# --------------------------
if __name__ == "__main__":
    asyncio.run(main())