"""
RbxPresenceMonitor — Multi-user API version
Author: Hcudsat
Description:
  Receives Roblox user IDs and Discord webhooks from browser extensions,
  monitors each user in the background, and sends Discord embed notifications
  whenever their presence changes.
"""

import os
import sys
import time
import logging
import threading
import requests
import psutil
from datetime import datetime
from flask import Flask, jsonify, request

# === Configuration ===
CHECK_INTERVAL = 5  # seconds
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# === Flask App ===
app = Flask(__name__)

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
def send_discord_embed(webhook_url: str, title: str, description: str, color: int, game_name: str = None):
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

    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        r.raise_for_status()
        logging.info(f"Sent embed → {title}")
    except Exception as e:
        logging.error(f"Discord send error: {e}")

# === Roblox API Functions ===
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
        response = requests.get(
            f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data and len(data) > 0:
            return data[0]["name"]
    except Exception:
        return None
    return None

# === Multi-user Monitoring ===
active_threads = {}

def monitor_presence(user_id: str, webhook_url: str):
    last_state = None
    online_since = None
    last_game_id = None

    logging.info(f"Started monitoring Roblox user {user_id}")
    while True:
        try:
            state, game_id, place_id = get_user_presence(int(user_id))
            game_name = get_game_name(place_id) if state == 2 else None

            if state != last_state or game_id != last_game_id:
                now = datetime.now().strftime("%H:%M:%S")
                if state == 0:
                    if online_since:
                        duration = int((time.time() - online_since) / 60)
                        send_discord_embed(
                            webhook_url,
                            title="User Offline",
                            description=f"User {user_id} went offline. Playtime: {duration} minutes.",
                            color=0xE74C3C
                        )
                    else:
                        send_discord_embed(
                            webhook_url,
                            title="User Offline",
                            description=f"User {user_id} is offline.",
                            color=0xE74C3C
                        )
                    online_since = None

                elif state == 1:
                    send_discord_embed(
                        webhook_url,
                        title="User Online",
                        description=f"User {user_id} is online ({now}).",
                        color=0x2ECC71
                    )
                    online_since = time.time()

                elif state == 2:
                    send_discord_embed(
                        webhook_url,
                        title="User In Game",
                        description=f"User {user_id} started playing {game_name or 'an unknown game'}.",
                        color=0x3498DB,
                        game_name=game_name
                    )
                    online_since = time.time()

                last_state = state
                last_game_id = game_id

        except Exception as e:
            logging.error(f"Error monitoring {user_id}: {e}")
        time.sleep(CHECK_INTERVAL)

# === API Endpoint (for extension) ===
@app.route("/start_monitoring", methods=["POST"])
def start_monitoring():
    data = request.get_json()
    user_id = data.get("user_id")
    webhook_url = data.get("webhook_url")

    if not user_id or not webhook_url:
        return jsonify({"error": "Missing user_id or webhook_url"}), 400

    if user_id in active_threads:
        return jsonify({"status": "already_running", "user_id": user_id}), 200

    thread = threading.Thread(target=monitor_presence, args=(user_id, webhook_url), daemon=True)
    thread.start()
    active_threads[user_id] = thread

    return jsonify({"status": "started", "user_id": user_id}), 200

@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "active_users": list(active_threads.keys())}), 200

# === Main Execution ===
if __name__ == "__main__":
    logging.info("Launching multi-user monitor server (port 5000)...")
    app.run(host="0.0.0.0", port=5000)
