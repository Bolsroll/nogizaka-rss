import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import html

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"

async def fetch():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(BASE_URL)

        links = await page.eval_on_selector_all(
            'a[href*="/diary/detail/"]',
            'els => els.map(e => e.href)'
        )

        await browser.close()
        return list(set(links))[:10]

def escape_xml(text):
    return html.escape(text, quote=True)

def create_rss(links):
    items = ""

    for link in links:
        title = "Nogizaka Blog"
        pubDate = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        items += f"""
<item>
<title><![CDATA[{title}]]></title>
<link>{escape_xml(link)}</link>
<guid>{escape_xml(link)}</guid>
<pubDate>{pubDate}</pubDate>
<description><![CDATA[]]></description>
</item>
"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title><![CDATA[Nogizaka Blog]]></title>
<link>https://www.nogizaka46.com/</link>
<description><![CDATA[Nogizaka Member Blog]]></description>
{items}
</channel>
</rss>
"""

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss)

async def main():
    links = await fetch()
    print("取得数:", len(links))
    create_rss(links)
    print("RSS作成完了")

asyncio.run(main())
