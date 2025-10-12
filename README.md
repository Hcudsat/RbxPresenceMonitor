# RbxPresenceMonitor

A lightweight cloud-based Python service that tracks a Roblox user's presence status (Online / Offline / In-Game) and delivers real-time notifications to a Discord channel via Webhooks.

---

## Features

- Real-time Roblox Presence API polling  
- Designed for always-on cloud platforms (Render, Railway, etc.)  
- Automatic Discord Webhook notifications  
- Built-in Flask health endpoint (`/health`)  
- Prevents duplicate runtime instances using `psutil`

---

## Tech Stack

- **Python 3.11+**
- **Flask** — lightweight web server for health checks  
- **Requests** — for API communication  
- **psutil** — process management  
- **Render / Railway** — for deployment

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/Hcudsat/RbxPresenceMonitor.git
cd RbxPresenceMonitor
