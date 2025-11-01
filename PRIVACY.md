# Privacy Policy (Draft)

This is a short privacy summary for the RbxPresenceMonitor browser extension.

- What we collect: Only the .ROBLOSECURITY token if you paste it explicitly into the extension options. The extension can optionally attempt to read the browser cookie .ROBLOSECURITY if you enable the "Use browser cookie" toggle in options. The extension also stores the target Discord webhook URL and the user IDs you choose to monitor. None of these values are sent to our servers by default.
- Where we store it: All sensitive data (manual token) is stored locally using chrome.storage.local. Webhook URL and user IDs are stored using chrome.storage.sync for convenience.
- Do we send it to servers?: No. The extension will not transmit your .ROBLOSECURITY token to remote servers. Webhook URLs are used only to send notifications and do not include session tokens.
- How to delete: Open the extension options and press "Clear token", or uninstall the extension to remove all stored data. You may also clear browser extension storage manually.
- Contact: https://github.com/Hcudsat/RbxPresenceMonitor
