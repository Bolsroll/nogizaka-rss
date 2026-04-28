import asyncio
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

LOCK_FILE = "running.lock"

# =========================
# ▼ 設定
# =========================
MEMBER_ID = "48008"
START_PAGE = 0
END_PAGE = 1
# =========================

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"
OUTPUT_DIR = "members_archive_xml"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --------------------------
# CSV → ID / 名前 / ローマ字
# --------------------------
def load_members(csv_path="members.csv"):
    id_to_name = {}
    name_to_roma = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue

            member_id, jp_name, roma = parts

            jp_name = jp_name.replace(" ", "").replace("　", "")

            id_to_name[member_id] = jp_name
            name_to_roma[jp_name] = roma

    return id_to_name, name_to_roma


# --------------------------
# 日付変換
# --------------------------
def format_rss_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
    except:
        return ""


def parse_rss_pubdate(pub):
    try:
        return datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return datetime.min


# --------------------------
# 既存XML読み込み（重複防止）
# --------------------------
def load_existing_items(path):
    items = []
    if not os.path.exists(path):
        return items

    with open(path, "r", encoding="utf-8") as f:
        xml = f.read()

    blocks = re.findall(r"<item>(.*?)</item>", xml, re.S)

    for b in blocks:
        link = re.search(r"<link>(.*?)</link>", b)
        title = re.search(r"<title>(.*?)</title>", b)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", b)

        items.append({
            "url": link.group(1) if link else "",
            "title": title.group(1) if title else "",
            "pub": pub.group(1) if pub else ""
        })

    return items


# --------------------------
# メイン
# --------------------------
async def main():

    id_to_name, name_to_roma = load_members()

    MEMBER_NAME = id_to_name.get(MEMBER_ID)
    if not MEMBER_NAME:
        raise Exception(f"CSVに存在しないID: {MEMBER_ID}")

    roma = name_to_roma[MEMBER_NAME]
    output_path = os.path.join(OUTPUT_DIR, f"{roma}_archive.xml")

    print("名前:", MEMBER_NAME)

    existing_items = load_existing_items(output_path)
    existing_urls = set(i["url"] for i in existing_items)

    new_items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for pageno in range(START_PAGE, END_PAGE + 1):
            url = f"{BASE_URL}?ct={MEMBER_ID}&page={pageno}"
            print("ページ:", url)

            await page.goto(url, timeout=60000)

            links = await page.locator("a[href*='/diary/detail/']").all()

            if not links:
                break

            for a in links:
                href = await a.get_attribute("href")
                if not href:
                    continue

                full_url = "https://www.nogizaka46.com" + href

                # 重複スキップ
                if full_url in existing_urls:
                    continue

                detail = await context.new_page()
                await detail.goto(full_url, timeout=60000)

                html = await detail.content()
                body = await detail.inner_text("body")

                # タイトル
                title = "no title"
                t = re.search(r"<title>(.*?)</title>", html, re.S)
                if t:
                    title = t.group(1).strip()
                    title = re.sub(r"\d{4}\.\d{2}\.\d{2}.*", "", title).strip()

                # 日付
                date = ""
                m = re.search(r"\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", body)
                if m:
                    date = m.group(0)

                print("取得:", title)

                new_items.append({
                    "title": title,
                    "url": full_url,
                    "date": date
                })

                await detail.close()

        await browser.close()

    # --------------------------
    # 統合＋ソート
    # --------------------------
    all_items = []

    # 既存（pubDateをそのまま使う）
    for i in existing_items:
        all_items.append({
            "title": i["title"],
            "url": i["url"],
            "pub": i["pub"]
        })

    # 新規（date → pubDate変換）
    for n in new_items:
        pub = format_rss_date(n["date"])
        all_items.append({
            "title": n["title"],
            "url": n["url"],
            "pub": pub
        })

    # 重複排除
    unique = {}
    for item in all_items:
        unique[item["url"]] = item

    all_items = list(unique.values())

    # 日付ソート（新しい順）
    all_items.sort(key=lambda x: parse_rss_pubdate(x["pub"]), reverse=True)

    # --------------------------
    # RSS生成
    # --------------------------
    rss_items = ""

    for item in all_items:
        rss_items += f"""
        <item>
            <title>{item['title']}</title>
            <link>{item['url']}</link>
            <guid>{item['url']}</guid>
            <pubDate>{item['pub']}</pubDate>
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{MEMBER_NAME} Archive</title>
<link>{BASE_URL}</link>
<description>過去記事</description>
{rss_items}
</channel>
</rss>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rss)

    print("✅ 完了:", output_path)


# --------------------------
# ロック制御
# --------------------------
if __name__ == "__main__":
    if os.path.exists(LOCK_FILE):
        print("⛔ 他の処理が動いてるので停止")
        exit()

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        asyncio.run(main())
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)