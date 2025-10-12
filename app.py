"""
RbxPresenceMonitor
Author: Hcudsat
Description:
  Cloud-based Roblox presence tracker that monitors a user's online/offline/game activity
  and sends structured Discord embed notifications in real time.
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

check_already_running("app.py")

# === Discord Embed Notifier ===
def send_discord_embed(title: str, description: str, color: int, game_name: str = None):
    embed = {
        "author": {
            "name": "RbxPresenceMonitor",
            "url": "https://github.com/Hcudsat/RbxPresenceMonitor",
            "icon_url": "https://static.wikia.nocookie.net/roblox/images/8/84/Roblox_logo.png"
        },
        "title": title,
        "description": description,
        "color": color,
        "footer": {
            "text": f"{'Game: ' + game_name if game_name else 'No game active'} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    payload = {"embeds": [embed]}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        logging.info(f"Sent Discord embed: {title}")
    except Exception as e:
        logging.error(f"Discord send error: {e}")

# === Presence Monitoring ===
last_state = None
online_since = None
last_game_id = None

def get_user_presence(user_id: int):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()["userPresences"][0]
    state = data["userPresenceType"]  # 0=Offline, 1=Online, 2=In-Game
    game_id = data.get("gameId", None)
    place_id = data.get("placeId", None)
    return state, game_id, place_id

def get_game_name(place_id: str):
    try:
        if not place_id:
            return None
        response = requests.get(f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and len(data) > 0:
            return data[0]["name"]
    except Exception:
        return None
    return None

def monitor_presence():
    global last_state, online_since, last_game_id

    logging.info("Presence monitoring started.")
    while True:
        try:
            state, game_id, place_id = get_user_presence(int(USER_ID))
            game_name = get_game_name(place_id) if state == 2 else None

            if state != last_state or game_id != last_game_id:
                now = datetime.now().strftime("%H:%M:%S")
                if state == 0:
                    if online_since:
                        duration = int((time.time() - online_since) / 60)
                        send_discord_embed(
                            title="User Offline",
                            description=f"The user went offline. Total session time: {duration} minutes.",
                            color=0xE74C3C,
                        )
                    else:
                        send_discord_embed(
                            title="User Offline",
                            description="The user is now offline.",
                            color=0xE74C3C,
                        )
                    online_since = None

                elif state == 1:
                    send_discord_embed(
                        title="User Online",
                        description=f"The user is now online ({now}).",
                        color=0x2ECC71,
                    )
                    online_since = time.time()

                elif state == 2:
                    send_discord_embed(
                        title="User In Game",
                        description=f"The user started playing: {game_name or 'Unknown Game'}",
                        color=0x3498DB,
                        game_name=game_name
                    )
                    online_since = time.time()

                last_state = state
                last_game_id = game_id

        except Exception as e:
            logging.error(f"Presence check failed: {e}")

        time.sleep(CHECK_INTERVAL)

# === Flask App ===
app = Flask(__name__)

@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "service": "RbxPresenceMonitor"}), 200

def start_flask():
    app.run(host="0.0.0.0", port=5000)

# === Main Execution ===
if __name__ == "__main__":
    threading.Thread(target=monitor_presence, daemon=True).start()
    logging.info("Launching web server (port 5000)...")
    start_flask()
