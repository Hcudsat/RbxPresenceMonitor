"""
Roblox Presence Notifier
Author: Hcudsat
Description:
  Monitor Roblox user activity via Roblox Presence API
  and send Discord notifications automatically.
"""

import os
import sys
import time
import logging
import threading
import requests
import psutil
from datetime import datetime
from flask import Flask, jsonify

# === Configuration ===
CHECK_INTERVAL = 5  # seconds
USER_ID = os.getenv("ROBLOX_USER_ID")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not USER_ID or not WEBHOOK_URL:
    sys.exit("Environment variables ROBLOX_USER_ID and DISCORD_WEBHOOK_URL are required.")

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# === Prevent Duplicate Run ===
def check_already_running(script_name: str):
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if (
                proc.info['pid'] != current_pid
                and 'python' in (proc.info['name'] or '').lower()
                and script_name in ' '.join(proc.info.get('cmdline') or [])
            ):
                logging.warning(f"Already running (PID: {proc.info['pid']}). Exiting.")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

check_already_running("roblox_presence_notifier.py")

# === Discord Notifier ===
def send_discord(content: str):
    try:
        r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=10)
        r.raise_for_status()
        logging.info(f"Sent to Discord → {content}")
    except requests.RequestException as e:
        logging.error(f"Discord send error: {e}")

# === Presence Monitoring ===
last_state = None
online_since = None

def get_user_presence(user_id: int):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()["userPresences"][0]["userPresenceType"]

def monitor_presence():
    global last_state, online_since

    logging.info("Presence monitoring started.")
    while True:
        try:
            state = get_user_presence(int(USER_ID))
            if state != last_state:
                now = datetime.now().strftime("%H:%M:%S")
                if state == 0:
                    if online_since:
                        duration = int((time.time() - online_since) / 60)
                        send_discord(f"Offline ({duration} min)")
                    else:
                        send_discord("Offline")
                    online_since = None
                elif state == 1:
                    send_discord(f"Online ({now})")
                    online_since = time.time()
                elif state == 2:
                    send_discord(f"Playing ({now})")
                    online_since = time.time()
                last_state = state
        except Exception as e:
            logging.error(f"Presence check failed: {e}")
        time.sleep(CHECK_INTERVAL)

# === Flask App ===
app = Flask(__name__)

@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "service": "Roblox Monitor"}), 200

def start_flask():
    app.run(host="0.0.0.0", port=5000)

# === Main Execution ===
if __name__ == "__main__":
    threading.Thread(target=monitor_presence, daemon=True).start()
    logging.info("Launching web server (port 5000)...")
    start_flask()
