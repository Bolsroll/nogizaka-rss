import tkinter as tk
from tkinter import messagebox
import json
import os
import sys
import threading

# --------------------------
# 実行ディレクトリ固定（.app対策）
# --------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# --------------------------
# Playwrightパス固定（.app対策）
# --------------------------
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


# --------------------------
# 設定 読み込み
# --------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass

    return {
        "member_id": "48008",
        "start_page": "1",
        "end_page": "3"
    }


# --------------------------
# 設定 保存
# --------------------------
def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# --------------------------
# 実行処理（別スレッド）
# --------------------------
def run_script():
    member_id = entry_member.get()
    start_page = entry_start.get()
    end_page = entry_end.get()

    # 入力チェック
    if not member_id or not start_page.isdigit() or not end_page.isdigit():
        messagebox.showerror("エラー", "入力値が不正です")
        return

    save_config({
        "member_id": member_id,
        "start_page": start_page,
        "end_page": end_page
    })

    btn_run.config(state="disabled", text="Running...")

    def task():
        try:
            import asyncio
            from archive_to_xml_auto import main

            asyncio.run(main(member_id, int(start_page), int(end_page)))

            messagebox.showinfo("完了", "処理が完了しました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
        finally:
            btn_run.config(state="normal", text="Run")

    threading.Thread(target=task).start()


# --------------------------
# GUI
# --------------------------
root = tk.Tk()
root.title("Nogizaka Archive Tool")
root.geometry("300x220")

config = load_config()

tk.Label(root, text="Member ID").pack()
entry_member = tk.Entry(root)
entry_member.insert(0, config["member_id"])
entry_member.pack()

tk.Label(root, text="Start Page").pack()
entry_start = tk.Entry(root)
entry_start.insert(0, config["start_page"])
entry_start.pack()

tk.Label(root, text="End Page").pack()
entry_end = tk.Entry(root)
entry_end.insert(0, config["end_page"])
entry_end.pack()

btn_run = tk.Button(root, text="Run", command=run_script)
btn_run.pack(pady=15)

root.mainloop()
