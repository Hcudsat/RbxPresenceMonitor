"""
RbxPresenceMonitor — Batch Monitoring (Commercial Edition)
Author: Hcudsat
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
from flask_cors import CORS

# === Flask Setup ===
app = Flask(__name__)
CORS(app)

CHECK_INTERVAL = 5  # seconds between each batch check
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
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

# === Discord Embed Sender ===
def send_discord_embed(webhook_url, title, description, color, game_name=None):
    embed = {
        "author": {
            "name": "RbxPresenceMonitor",
            "url": "https://github.com/Hcudsat/RbxPresenceMonitor"
        },
        "title": title,
        "description": description,
        "color": color,
        "footer": {
            "text": f"{'Game: ' + game_name if game_name else 'No game active'} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }
    try:
        requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        logging.error(f"Discord send error: {e}")

# === Roblox API ===
def get_batch_presence(user_ids):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [int(uid) for uid in user_ids]}
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()["userPresences"]

def get_game_name(place_id: str):
    if not place_id:
        return None
    try:
        r = requests.get(f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            logging.warning(f"No game details found for placeId {place_id}")
            return None
        return data[0].get("name", None)
    except Exception as e:
        logging.error(f"get_game_name error for {place_id}: {e}")
        return None

# === Data Stores ===
monitored_users = {}  # user_id: webhook_url
user_states = {}      # user_id: (state, game_id)
stop_flag = False

# === Batch Monitor Loop ===
def monitor_all_users():
    global stop_flag
    logging.info("Started batch monitoring loop.")
    while not stop_flag:
        try:
            if not monitored_users:
                time.sleep(3)
                continue

            user_ids = list(monitored_users.keys())
            presences = get_batch_presence(user_ids)

            for user_data in presences:
                user_id = str(user_data["userId"])
                state = user_data["userPresenceType"]
                game_id = user_data.get("gameId")
                place_id = user_data.get("placeId")

                last_state, last_game = user_states.get(user_id, (None, None))
                webhook_url = monitored_users[user_id]

                # Skip if no change
                if state == last_state and game_id == last_game:
                    continue

                game_name = None
                if state == 2:
                    if not place_id:
                        time.sleep(2)
                        refreshed = get_batch_presence([user_id])[0]
                        place_id = refreshed.get("placeId")
                    game_name = get_game_name(place_id)

                if state == 0:
                    send_discord_embed(webhook_url, "User Offline", f"User {user_id} went offline.", 0xE74C3C)
                elif state == 1:
                    send_discord_embed(webhook_url, "User Online", f"User {user_id} is online.", 0x2ECC71)
                elif state == 2:
                    send_discord_embed(webhook_url, "User In Game", f"User {user_id} started playing {game_name or 'a private or unknown game'}.", 0x3498DB, game_name)

                user_states[user_id] = (state, game_id)

        except Exception as e:
            logging.error(f"Batch loop error: {e}")
        time.sleep(CHECK_INTERVAL)

# === Flask API Endpoints ===
@app.route("/start_monitoring", methods=["POST"])
def start_monitoring():
    data = request.get_json()
    user_id = data.get("user_id")
    webhook_url = data.get("webhook_url")

    if not user_id or not webhook_url:
        return jsonify({"error": "Missing user_id or webhook_url"}), 400

    if webhook_url in monitored_users.values():
        return jsonify({
            "error": "This webhook is already monitoring another user. Please stop monitoring first before starting a new one."
        }), 400

    monitored_users[user_id] = webhook_url
    logging.info(f"Added user {user_id} for monitoring.")
    return jsonify({"status": "started", "user_id": user_id}), 200

@app.route("/stop_monitoring", methods=["POST"])
def stop_monitoring():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if user_id not in monitored_users:
        return jsonify({"status": "not_running", "user_id": user_id}), 200

    monitored_users.pop(user_id)
    user_states.pop(user_id, None)
    logging.info(f"Stopped monitoring user {user_id}.")
    return jsonify({"status": "stopped", "user_id": user_id}), 200

@app.route("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "active_users": list(monitored_users.keys())
    }), 200

# === Main ===
if __name__ == "__main__":
    t = threading.Thread(target=monitor_all_users, daemon=True)
    t.start()
    logging.info("Launching batch monitor server (port 5000)...")
    app.run(host="0.0.0.0", port=5000)
