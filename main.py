import asyncio
import json
import os
from datetime import datetime
from xml.sax.saxutils import escape
from playwright.async_api import async_playwright

BASE_URL = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list?ima=0000"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
FEED_FILE = os.path.join(BASE_DIR, "feed.xml")
MEMBERS_DIR = os.path.join(BASE_DIR, "members")

MAX_ALL = 50
MAX_MEMBER = 20

os.makedirs(MEMBERS_DIR, exist_ok=True)

# =========================
# ローマ字マップ（あなたの最新版）
# =========================
ROMAJI_MAP = {
    "矢田 萌華": "moeka_yada","森平 麗心": "urumi_morihira","増田 三莉音": "mirine_masuda",
    "瀬戸口 心月": "mitsuki_setoguchi","鈴木 佑捺": "yuuna_suzuki","川端 晃菜": "hina_kawabata",
    "海邉 朱莉": "akari_kaibe","小津 玲奈": "reina_ozu","大越 ひなの": "hinano_okoshi",
    "愛宕 心響": "kokone_atago","長嶋 凛桜": "rio_nagashima",
    "岡本 姫奈": "hina_okamoto","川﨑 桜": "sakura_kawasaki","池田 瑛紗": "teresa_ikeda",
    "五百城 茉央": "mao_ioki","中西 アルノ": "aruno_nakanishi","奥田 いろは": "iroha_okuda",
    "冨里 奈央": "nao_tomisato","小川 彩": "aya_ogawa","菅原 咲月": "satsuki_sugawara",
    "井上 和": "nagi_inoue","一ノ瀬 美空": "miku_ichinose",
    "弓木 奈於": "yumiki_nao","松尾 美佑": "matsuo_miyu","林 瑠奈": "hayashi_runa",
    "佐藤 璃果": "sato_rika","黒見 明香": "kuromi_haruka",
    "清宮 レイ": "seimiya_rei","北川 悠理": "kitagawa_yuri","金川 紗耶": "kanagawa_saya",
    "矢久保 美緒": "yakubo_mio","早川 聖来": "hayakawa_seira","掛橋 沙耶香": "kakehashi_sayaka",
    "賀喜 遥香": "kaki_haruka","筒井 あやめ": "tsutsui_ayame","田村 真佑": "tamura_mayu",
    "柴田 柚菜": "shibata_yuna","遠藤 さくら": "endo_sakura"
}

def get_safe_name(member):
    member = member.replace("　", " ").strip()
    return ROMAJI_MAP.get(member, member.encode("utf-8").hex())

# =========================
# RSS生成
# =========================
def build_rss(items, title):
    rss_items = ""
    for item in items:
        img = f'<img src="{item.get("image","")}" /><br>' if item.get("image") else ""

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
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{BASE_URL}</link>
<description>Nogizaka Blog</description>
{rss_items}
</channel>
</rss>
"""

def save_rss(path, items, title):
    with open(path, "w") as f:
        f.write(build_rss(items, title))

# =========================
# データ保存
# =========================
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

# =========================
# スクレイピング（100%安定版）
# =========================
async def scrape():
    print("アクセス中...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(BASE_URL, timeout=60000)

        # JS描画待ち
        await page.wait_for_selector('a[href*="/diary/detail/"]', timeout=60000)
        await page.wait_for_timeout(3000)

        items = []

        links = await page.query_selector_all('a[href*="/diary/detail/"]')

        for link in links[:100]:
            try:
                href = await link.get_attribute("href")
                title = await link.inner_text()

                parent = await link.evaluate_handle("el => el.closest('li')")
                parent = parent.as_element()

                if not parent:
                    continue

                # メンバー名
                member_el = await parent.query_selector("p")
                member = await member_el.inner_text() if member_el else "unknown"
                member = member.replace("　", " ").strip()

                # 画像
                img_el = await parent.query_selector("img")
                img = ""
                if img_el:
                    img = await img_el.get_attribute("src") or ""
                    if not img:
                        img = await img_el.get_attribute("data-src") or ""

                items.append({
                    "title": title.strip(),
                    "link": "https://www.nogizaka46.com" + href,
                    "date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                    "member": member,
                    "image": img
                })

            except Exception as e:
                print("取得エラー:", e)

        await browser.close()

        print("取得数:", len(items))
        return items

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

    all_dict = {item["link"]: item for item in old_items}
    for item in new_items:
        all_dict[item["link"]] = item

    all_items = list(all_dict.values())

    # 全体RSS
    save_rss(FEED_FILE, all_items[:MAX_ALL], "Nogizaka All")

    # メンバー別
    members = split_by_member(all_items)

    for member, items in members.items():
        safe = get_safe_name(member)
        path = os.path.join(MEMBERS_DIR, f"{safe}.xml")
        save_rss(path, items[:MAX_MEMBER], member)

    save_data(all_items[:500])

    print("RSS作成完了")

# =========================
if __name__ == "__main__":
    asyncio.run(main())
