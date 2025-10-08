# Overview

This is a Roblox presence monitoring application that tracks a user's online status and sends notifications to Discord via webhooks. The system periodically checks if a specific Roblox user is online/offline and sends status updates to a Discord channel. It includes duplicate process prevention to ensure only one instance runs at a time. The application also runs a Flask web server to enable health checks and keep-alive pings from external monitoring services.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Design Pattern
The application follows a **polling-based monitoring pattern** with state tracking:

**Problem**: Need to monitor Roblox user presence in real-time and notify via Discord
**Solution**: Continuous polling of Roblox Presence API with state change detection
**Rationale**: Roblox doesn't provide webhooks, so polling is necessary. State tracking prevents duplicate notifications.

## Application Flow
1. **Duplicate Prevention**: On startup, checks for existing instances using process inspection
2. **State Management**: Maintains global state variables (`last_state`, `online_since`) to track presence changes
3. **Background Monitoring**: Launches Roblox presence monitoring in a daemon thread
4. **Web Server**: Starts Flask web server on port 5000 with health check endpoints
5. **Polling Loop**: Background thread periodically queries Roblox API and compares against last known state
6. **Notification**: Sends Discord webhook messages only when state changes occur

## Key Architectural Decisions

### Duplicate Process Prevention
- Uses `psutil` to enumerate running processes
- Compares process names and command-line arguments
- Ensures only one monitoring instance runs (critical for avoiding notification spam)

### State Change Detection
- Tracks previous state globally
- Only triggers notifications on actual state transitions
- Prevents redundant Discord messages during continuous online/offline periods

### Web Server Integration
- Flask web server runs on port 5000 to enable external health checks and keep-alive pings
- Monitoring loop executes in a daemon thread, allowing both services to run concurrently
- Provides two endpoints: `/` (JSON health status) and `/ping` (simple pong response)
- Enables integration with uptime monitoring services (UptimeRobot, etc.) to keep the app alive

### Error Handling
- Implements timeout protection for Discord webhook calls (10s timeout)
- Uses try-except blocks to handle API failures gracefully
- Process enumeration handles zombie/inaccessible processes safely

# External Dependencies

## Third-Party Services
- **Roblox Presence API**: `https://presence.roblox.com/v1/presence/users` - REST endpoint for querying user online status
- **Discord Webhooks**: Incoming webhook for posting messages to Discord channels

## Python Libraries
- `flask`: Lightweight web framework for health check endpoints
- `psutil`: Process and system utilities for duplicate detection
- `requests`: HTTP client for API calls (Roblox API and Discord webhooks)
- Standard library: `os`, `sys`, `time`, `datetime`, `threading`

## Configuration
- Roblox user ID stored securely in `ROBLOX_USER_ID` environment variable
- Discord webhook URL stored securely in `DISCORD_WEBHOOK_URL` environment variable
- No database or persistent storage used
- State maintained in-memory only (resets on restart)

## Security
- Both Roblox user ID and Discord webhook URL protected via Replit Secrets (environment variables)
- Early exit with error messages if required environment variables are not set
- No sensitive credentials or personal information stored in code