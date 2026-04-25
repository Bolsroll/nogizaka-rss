import asyncio
import random
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from feedgen.feed import FeedGenerator

URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"

async def delay():
    await asyncio.sleep(random.uniform(3, 6))

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            locale="ja-JP",
            timezone_id="Asia/Tokyo"
        )

        page = await context.new_page()

        print("アクセス中...")
        await page.goto(URL, wait_until="domcontentloaded")

        await delay()
        await page.evaluate("window.scrollBy(0, 1000)")
        await delay()

        items = await page.query_selector_all("a[href*='/diary/detail/']")

        print("取得数:", len(items))

        results = []
        for item in items[:20]:
            title = await item.inner_text()
            link = await item.get_attribute("href")

            results.append({
                "title": title.strip(),
                "link": "https://www.nogizaka46.com" + link,
                "date": datetime.now(timezone.utc)
            })

        await browser.close()
        return results

def make_rss(items):
    fg = FeedGenerator()
    fg.title("乃木坂ブログRSS")
    fg.link(href="https://example.com")
    fg.description("auto rss")

    for item in items:
        fe = fg.add_entry()
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.pubDate(item["date"])

    fg.rss_file("feed.xml")
    print("RSS作成完了")

async def main():
    items = await scrape()
    make_rss(items)

asyncio.run(main())
