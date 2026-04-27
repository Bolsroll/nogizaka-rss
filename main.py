import asyncio
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"

OUTPUT_DIR = "members"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# メンバー辞書（必要に応じて追加）
MEMBERS = {
    "矢田 萌華": "moeka_yada",
    "森平 麗心": "urumi_morihira",
    "増田 三莉音": "mirine_masuda",
}

def sanitize(text):
    return re.sub(r"\s+", " ", text).strip()

def get_member_slug(name):
    return MEMBERS.get(name, "unknown")

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("アクセス中...")
        await page.goto(BASE_URL, timeout=60000)

        # 🔥 最強待機（これが重要）
        await page.wait_for_load_state("networkidle")

        # 🔥 JS実行で直接取る（セレクタ崩れ対策）
        items = await page.evaluate("""
        () => {
            const results = [];
            document.querySelectorAll("a[href*='/diary/detail/']").forEach(a => {
                const title = a.innerText;
                const url = a.href;

                // 親からメンバー名探す
                let parent = a.closest("li, div");
                let member = "unknown";

                if (parent) {
                    const nameEl = parent.querySelector("*");
                    if (nameEl) member = nameEl.innerText;
                }

                results.push({title, url, member});
            });
            return results;
        }
        """)

        await browser.close()
        return items


def save_member_feed(member, entries):
    filename = os.path.join(OUTPUT_DIR, f"{member}.xml")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
""")
        for e in entries:
            f.write(f"""
<item>
<title>{e['title']}</title>
<link>{e['url']}</link>
<pubDate>{datetime.utcnow()}</pubDate>
</item>
""")
        f.write("</channel></rss>")


async def main():
    items = await scrape()

    print("取得数:", len(items))

    if not items:
        print("❌ 取得失敗")
        return

    grouped = {}

    for item in items:
        name = sanitize(item["member"])
        slug = get_member_slug(name)

        if slug not in grouped:
            grouped[slug] = []

        grouped[slug].append(item)

    # 🔥 メンバー別保存
    for slug, entries in grouped.items():
        save_member_feed(slug, entries)

    print("✅ RSS作成完了")


if __name__ == "__main__":
    asyncio.run(main())
