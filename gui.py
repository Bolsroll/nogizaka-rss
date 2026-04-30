import tkinter as tk
from tkinter import messagebox
import json
import asyncio
from archive_to_xml_auto import main

CONFIG_FILE = "config.json"


# --------------------------
# 設定読み込み
# --------------------------
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "member_id": "48008",
            "start_page": 3,
            "end_page": 11
        }


# --------------------------
# 設定保存
# --------------------------
def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# --------------------------
# 実行
# --------------------------
def run_script():
    try:
        member_id = entry_member.get()
        start = int(entry_start.get())
        end = int(entry_end.get())

        # 保存
        save_config({
            "member_id": member_id,
            "start_page": start,
            "end_page": end
        })

        # 実行
        asyncio.run(main(member_id, start, end))

        messagebox.showinfo("完了", "処理が終わりました")
    except Exception as e:
        messagebox.showerror("エラー", str(e))


# --------------------------
# GUI
# --------------------------
config = load_config()

root = tk.Tk()
root.title("Nogizaka Archive Tool")

tk.Label(root, text="Member ID").grid(row=0, column=0)
entry_member = tk.Entry(root)
entry_member.insert(0, config["member_id"])
entry_member.grid(row=0, column=1)

tk.Label(root, text="Start Page").grid(row=1, column=0)
entry_start = tk.Entry(root)
entry_start.insert(0, config["start_page"])
entry_start.grid(row=1, column=1)

tk.Label(root, text="End Page").grid(row=2, column=0)
entry_end = tk.Entry(root)
entry_end.insert(0, config["end_page"])
entry_end.grid(row=2, column=1)

tk.Button(root, text="Run", command=run_script).grid(row=3, column=0, columnspan=2)

root.mainloop()
