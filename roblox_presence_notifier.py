import os
import sys
import psutil
import requests
import time
from datetime import datetime

# === RobloxユーザーIDとWebhook設定 ===
USER_ID = "5726041083"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not WEBHOOK_URL:
    print("エラー: DISCORD_WEBHOOK_URL環境変数が設定されていません")
    sys.exit(1)

# === 二重起動防止（Replitでも有効） ===
def check_already_running(script_name):
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if (
                proc.info['pid'] != current_pid and
                'python' in (proc.info['name'] or '').lower() and
                script_name in ' '.join(proc.info.get('cmdline') or [])
            ):
                print(f"Already running (PID: {proc.info['pid']}). Exiting.")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

check_already_running('roblox_presence_notifier.py')

# === Discord送信関数 ===
def send_discord_message(content):
    payload = {"content": content}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] → {content}")
    except Exception as e:
        print(f"Discord送信エラー: {e}")

# === 状態監視関数 ===
last_state = None
online_since = None

def check_presence():
    global last_state, online_since

    url = "https://presence.roblox.com/v1/presence/users"
    headers = {"Content-Type": "application/json"}
    data = {"userIds": [int(USER_ID)]}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        user_data = response.json()["userPresences"][0]
        state = user_data["userPresenceType"]  # 0=オフライン, 1=オンライン, 2=ゲーム中
    except Exception as e:
        print("エラー:", e)
        return

    if state != last_state:
        if state == 0:
            if online_since:
                duration = int((time.time() - online_since) / 60)
                send_discord_message(f"User is now Offline 🥀（Playtime: {duration}分）")
            else:
                send_discord_message("User is now Offline 🥀")
            online_since = None

        elif state == 1:
            send_discord_message("User is now Online 🔥（ホーム画面）")
            online_since = time.time()

        elif state == 2:
            send_discord_message("User is Playing RN 🌟")
            online_since = time.time()

        last_state = state

# === メインループ ===
print("Robloxのステータス監視を開始します...")
while True:
    check_presence()
    time.sleep(5)
