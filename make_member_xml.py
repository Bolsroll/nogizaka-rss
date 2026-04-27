import os
import json

MEMBER_DIR = "members"
OUTPUT_DIR = "members_xml"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------
# 名前マップ（完全版）
# --------------------------
NAME_MAP = {
    # ===== 6期 =====
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

    # ===== 5期 =====
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

    # ===== 4期 =====
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
    "遠藤 さくら": "endo_sakura",
    "一ノ瀬 美空": "miku_ichinose",
}


# --------------------------
# XML生成
# --------------------------
def generate_xml(member_name, items):
    safe_name = NAME_MAP.get(member_name, "unknown")

    xml_items = ""

    for item in items:
        xml_items += f"""
        <item>
            <title>{item['title']}</title>
            <link>{item['url']}</link>
            <pubDate>{item['date']}</pubDate>
        </item>
        """

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{member_name} Blog</title>
<link>https://www.nogizaka46.com/</link>
<description>{member_name}のブログRSS</description>
{xml_items}
</channel>
</rss>
"""

    path = os.path.join(OUTPUT_DIR, f"{safe_name}.xml")

    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    print("XML生成:", member_name, "→", safe_name)


# --------------------------
# メイン
# --------------------------
def main():
    files = os.listdir(MEMBER_DIR)

    for file in files:
        if not file.endswith(".json"):
            continue

        path = os.path.join(MEMBER_DIR, file)

        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        if not items:
            continue

        member_name = items[0]["member"]

        generate_xml(member_name, items)

    print("✅ メンバー別XML生成完了")


if __name__ == "__main__":
    main()
