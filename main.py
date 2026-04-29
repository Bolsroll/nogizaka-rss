import asyncio
import os
import json
import re
import time
from datetime import datetime
from playwright.async_api import async_playwright

LOCK_FILE = "running.lock"

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
# ユーティリティ
# --------------------------
def clean_text(s):
    if not s:
        return ""
    return s.replace("\u00A0", " ").strip()


def normalize_url(url):
    return url.split("?")[0]


def format_rss_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
    except:
        return ""


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
# スクレイプ本体（超安定版）
# --------------------------
async def scrape(page, context):
    await page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_selector("a[href*='/diary/detail/']", timeout=10000)

    links = await page.locator("a[href*='/diary/detail/']").all()

    items = []
    seen = set()

    for link in links[:FETCH_LIMIT]:
        url = await link.get_attribute("href")
        if not url:
            continue

        if not url.startswith("http"):
            url = "https://www.nogizaka46.com" + url

        norm = normalize_url(url)
        if norm in seen:
            continue
        seen.add(norm)

        # ------------------
        # 詳細ページ（例外耐性あり）
        # ------------------
        detail = None
        try:
            detail = await context.new_page()
            await detail.goto(url, timeout=60000, wait_until="domcontentloaded")

            html = await detail.content()
            body_text = await detail.inner_text("body")

            html = clean_text(html)
            body_text = clean_text(body_text)

            # タイトル
            title = "no title"
            t = re.search(r"<title>(.*?)</title>", html, re.S)
            if t:
                title = clean_text(t.group(1))
                title = re.sub(r"\d{4}\.\d{2}\.\d{2}.*", "", title).strip()

            # 日付
            date = "unknown"
            m = re.search(r"\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", body_text)
            if m:
                date = m.group(0)

            # 名前
            name = "unknown"

            m = re.search(r'<p class="bd--prof__name">(.*?)</p>', html)
            if m:
                name = clean_text(m.group(1))

            if name == "unknown":
                m = re.search(r"<title>(.*?)</title>", html, re.S)
                if m:
                    t = clean_text(m.group(1))
                    if "｜" in t:
                        name = t.split("｜")[-1].strip()
                    elif "|" in t:
                        name = t.split("|")[-1].strip()

            print(f"取得: {title} / {name} / {date}")

            items.append({
                "title": title,
                "url": url,
                "date": date,
                "member": name
            })

        except Exception as e:
            print("⚠️ 取得失敗:", url)

        finally:
            if detail:
                try:
                    await detail.close()
                except:
                    pass

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
    seen = set()

    for item in items:
        norm = normalize_url(item["url"])
        if norm in seen:
            continue
        seen.add(norm)

        pub = format_rss_date(item["date"])

        rss_items += f"""
        <item>
            <title>{item['title']}</title>
            <link>{item['url']}</link>
            <guid>{item['url']}</guid>
            <pubDate>{pub}</pubDate>
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
# 実行（ロック完全版）
# --------------------------
if __name__ == "__main__":
    MAX_AGE = 30 * 60

    if os.path.exists(LOCK_FILE):
        age = time.time() - os.path.getmtime(LOCK_FILE)

        if age < MAX_AGE:
            print("⛔ 他の処理が動いてるので停止")
            exit()
        else:
            print("⚠️ 古いlock削除")
            os.remove(LOCK_FILE)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        asyncio.run(main())
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)