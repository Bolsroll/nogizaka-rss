import asyncio
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

LOCK_FILE = "running.lock"

# =========================
# ▼ ここだけ変える
# =========================
MEMBER_ID = "48008"
START_PAGE = 1
END_PAGE = 3
# =========================

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"
OUTPUT_DIR = "members_archive_xml"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# --------------------------
# ID → 名前 / ローマ字
# --------------------------
def load_member_map(csv_path="members.csv"):
    id_map = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue

            member_id, jp_name, roma = parts

            jp_name = jp_name.replace(" ", "").replace("　", "")

            id_map[member_id] = {
                "name": jp_name,
                "roma": roma
            }

    return id_map


# --------------------------
# 日付変換
# --------------------------
def format_rss_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
    except:
        return ""


# --------------------------
# メイン
# --------------------------
async def main():

    MAP = load_member_map()

    if MEMBER_ID not in MAP:
        raise Exception(f"CSVに存在しないID: {MEMBER_ID}")

    MEMBER_NAME = MAP[MEMBER_ID]["name"]
    ROMA = MAP[MEMBER_ID]["roma"]

    print("対象:", MEMBER_NAME)

    items = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        detail = await context.new_page()

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

                # 重複防止
                if full_url in seen:
                    continue
                seen.add(full_url)

                await detail.goto(full_url, timeout=60000)

                html = await detail.content()
                body = await detail.inner_text("body")

                # ------------------
                # タイトル
                # ------------------
                title = "no title"
                t = re.search(r"<title>(.*?)</title>", html, re.S)
                if t:
                    title = t.group(1).strip()
                    title = re.sub(r"\d{4}\.\d{2}\.\d{2}.*", "", title).strip()

                # ------------------
                # 日付
                # ------------------
                date = ""
                m = re.search(r"\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", body)
                if m:
                    date = m.group(0)

                print("取得:", title)

                items.append({
                    "title": title,
                    "url": full_url,
                    "date": date
                })

                # 軽量化（過負荷防止）
                await asyncio.sleep(0.2)

        await detail.close()
        await browser.close()

    # --------------------------
    # RSS生成
    # --------------------------
    rss_items = ""

    for item in items:
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
<title>{MEMBER_NAME} Archive</title>
<link>{BASE_URL}</link>
<description>過去記事</description>
{rss_items}
</channel>
</rss>
"""

    path = os.path.join(OUTPUT_DIR, f"{ROMA}_archive.xml")

    with open(path, "w") as f:
        f.write(rss)

    print("✅ 完了:", path)


# --------------------------
# 実行
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