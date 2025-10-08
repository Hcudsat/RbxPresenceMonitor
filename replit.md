# Overview

This is a Roblox presence monitoring application that tracks a user's online status and sends notifications to Discord via webhooks. The system periodically checks if a specific Roblox user is online/offline and sends status updates to a Discord channel. It includes duplicate process prevention to ensure only one instance runs at a time.

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
3. **Polling Loop**: Periodically queries Roblox API and compares against last known state
4. **Notification**: Sends Discord webhook messages only when state changes occur

## Key Architectural Decisions

### Duplicate Process Prevention
- Uses `psutil` to enumerate running processes
- Compares process names and command-line arguments
- Ensures only one monitoring instance runs (critical for avoiding notification spam)

### State Change Detection
- Tracks previous state globally
- Only triggers notifications on actual state transitions
- Prevents redundant Discord messages during continuous online/offline periods

### Error Handling
- Implements timeout protection for Discord webhook calls (10s timeout)
- Uses try-except blocks to handle API failures gracefully
- Process enumeration handles zombie/inaccessible processes safely

# External Dependencies

## Third-Party Services
- **Roblox Presence API**: `https://presence.roblox.com/v1/presence/users` - REST endpoint for querying user online status
- **Discord Webhooks**: Incoming webhook for posting messages to Discord channels

## Python Libraries
- `psutil`: Process and system utilities for duplicate detection
- `requests`: HTTP client for API calls (Roblox API and Discord webhooks)
- Standard library: `os`, `sys`, `time`, `datetime`

## Configuration
- User ID is hardcoded constant (5726041083)
- Discord webhook URL stored securely in `DISCORD_WEBHOOK_URL` environment variable
- No database or persistent storage used
- State maintained in-memory only (resets on restart)

## Security
- Discord webhook URL protected via Replit Secrets (environment variable)
- Early exit with error message if webhook URL environment variable is not set
- No sensitive credentials stored in code