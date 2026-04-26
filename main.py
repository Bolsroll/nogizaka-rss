import asyncio
import json
import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list?ima=0000"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
FEED_FILE = os.path.join(BASE_DIR, "feed.rss")
MEMBERS_DIR = os.path.join(BASE_DIR, "members")

SITE_URL = "https://bolsroll.github.io/nogizaka-rss"

MAX_ALL = 50
MAX_MEMBER = 20

os.makedirs(MEMBERS_DIR, exist_ok=True)

# =========================
# ローマ字マップ（完全版）
# =========================
ROMAJI_MAP = {
    "矢田 萌華": "moeka_yada",
    "森平 麗心": "urumi_morihira",
    "増田 三莉音": "mirine_masuda",
    "瀬戸口 心月": "mitsuki_setoguchi",
    "鈴木 佑捺": "yuuna_suzuki",
    "川端 晃菜": "hina_kawabata",
    "海邉 朱莉": "akari_kaibe",
    "小津 玲奈": "reina_ozu",
    "大越 ひなの": "hinano_okoshi",
    "愛宕 心響": "kokone_atago",
    "長嶋 凛桜": "rio_nagashima",

    "岡本 姫奈": "hina_okamoto",
    "川﨑 桜": "sakura_kawasaki",
    "池田 瑛紗": "teresa_ikeda",
    "五百城 茉央": "mao_ioki",
    "中西 アルノ": "aruno_nakanishi",
    "奥田 いろは": "iroha_okuda",
    "冨里 奈央": "nao_tomisato",
    "小川 彩": "aya_ogawa",
    "菅原 咲月": "satsuki_sugawara",
    "井上 和": "nagi_inoue",
    "一ノ瀬 美空": "miku_ichinose",

    "弓木 奈於": "yumiki_nao",
    "松尾 美佑": "matsuo_miyu",
    "林 瑠奈": "hayashi_runa",
    "佐藤 璃果": "sato_rika",
    "黒見 明香": "kuromi_haruka",

    "清宮 レイ": "seimiya_rei",
    "北川 悠理": "kitagawa_yuri",
    "金川 紗耶": "kanagawa_saya",
    "矢久保 美緒": "yakubo_mio",
    "早川 聖来": "hayakawa_seira",
    "掛橋 沙耶香": "kakehashi_sayaka",
    "賀喜 遥香": "kaki_haruka",
    "筒井 あやめ": "tsutsui_ayame",
    "田村 真佑": "tamura_mayu",
    "柴田 柚菜": "shibata_yuna",
    "遠藤 さくら": "endo_sakura"
}

def get_safe_name(member):
    member = member.replace("　", " ").strip()

    if member in ROMAJI_MAP:
        return ROMAJI_MAP[member]

    # fallback（壊れない）
    safe = member.replace(" ", "_")
    safe = re.sub(r'[^\w_]', '', safe)
    return safe.lower()

# =========================
# データ
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

# =========================
# RSS生成
# =========================
def build_rss(items, title, feed_path):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    rss_items = ""
    for item in items:
        img = f'<img src="{item.get("image", "")}" /><br>' if item.get("image") else ""

        rss_items += f"""
<item>
<title>{escape(item['title'])}</title>
<link>{item['link']}</link>
<guid>{item['link']}</guid>
<pubDate>{item['date']}</pubDate>
<description><![CDATA[{img}{escape(item['member'])}]]></description>
</item>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
 xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>{title}</title>
<link>{SITE_URL}</link>
<description>Nogizaka Blog</description>

<atom:link href="{SITE_URL}/{feed_path}" rel="self" type="application/rss+xml"/>
<lastBuildDate>{now}</lastBuildDate>

{rss_items}
</channel>
</rss>
"""

def save_rss(path, items, title, feed_path):
    with open(path, "w") as f:
        f.write(build_rss(items, title, feed_path))

# =========================
# スクレイピング
# =========================
async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(3)

        links = await page.query_selector_all("a[href*='/diary/detail/']")

        items = []
        for link in links[:100]:
            try:
                href = await link.get_attribute("href")
                title = await link.inner_text()

                parent = await link.evaluate_handle("el => el.closest('li')")

                member_el = await parent.query_selector("p")
                member = await member_el.inner_text() if member_el else "不明"

                img_el = await parent.query_selector("img")
                img = await img_el.get_attribute("src") if img_el else ""

                items.append({
                    "title": title.strip(),
                    "link": "https://www.nogizaka46.com" + href,
                    "member": member.strip(),
                    "image": img or ""
                })

            except:
                pass

        await browser.close()
        return items

# =========================
# 差分管理
# =========================
def merge_items(new_items, old_items):
    old_map = {item["link"]: item for item in old_items}
    merged = []

    for item in new_items:
        if item["link"] in old_map:
            item["date"] = old_map[item["link"]]["date"]
        else:
            item["date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        merged.append(item)

    for link, item in old_map.items():
        if link not in [i["link"] for i in merged]:
            merged.append(item)

    merged.sort(key=lambda x: x["date"], reverse=True)
    return merged

# =========================
def split_by_member(items):
    result = {}
    for item in items:
        result.setdefault(item["member"], []).append(item)
    return result

# =========================
async def main():
    new_items = await scrape()
    old_items = load_data()

    all_items = merge_items(new_items, old_items)

    # 全体RSS
    save_rss(FEED_FILE, all_items[:MAX_ALL], "Nogizaka All", "feed.rss")

    # メンバー別RSS
    members = split_by_member(all_items)
    for member, items in members.items():
        safe = get_safe_name(member)
        path = os.path.join(MEMBERS_DIR, f"{safe}.xml")
        save_rss(path, items[:MAX_MEMBER], member, f"members/{safe}.xml")

    save_data(all_items[:500])

    print("完全版 完了")

# =========================
if __name__ == "__main__":
    asyncio.run(main())
