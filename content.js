(function() {
  // === Create main panel ===
  const panel = document.createElement("div");
  panel.id = "rbx-presence-panel";
  panel.innerHTML = `
    <h3>RbxPresence Monitor</h3>
    <label>User IDs (comma separated)</label>
    <input type="text" id="userIds" placeholder="e.g. 5726041083,12345">
    <label>Discord Webhook URL</label>
    <input type="text" id="webhookUrl" placeholder="e.g. https://discord.com/api/webhooks/...">
    <div class="buttons">
      <button id="startBtn">Start</button>
      <button id="stopBtn">Stop</button>
    </div>
    <p id="status">Ready</p>
    <div style="margin-top:8px;font-size:11px">
      <a href="#" id="openOptions">Token / Cookie settings</a>
    </div>
  `;
  document.body.appendChild(panel);

  // === Create toggle button ===
  const toggleBtn = document.createElement("div");
  toggleBtn.id = "rbx-toggle-btn";
  toggleBtn.innerHTML = "<span>⚙️</span>";
  document.body.appendChild(toggleBtn);

  let panelVisible = true;
  toggleBtn.addEventListener("click", () => {
    panelVisible = !panelVisible;
    panel.style.transform = panelVisible ? "translateY(0)" : "translateY(120%)";
    const gear = toggleBtn.querySelector("span");
    gear.classList.toggle("spinning", !panelVisible);
  });

  const userIdsInput = panel.querySelector("#userIds");
  const webhookInput = panel.querySelector("#webhookUrl");
  const status = panel.querySelector("#status");
  const openOptions = panel.querySelector("#openOptions");

  // load saved
  chrome.storage.sync.get(["userIds", "webhookUrl"], (data) => {
    if (data.userIds) userIdsInput.value = data.userIds;
    if (data.webhookUrl) webhookInput.value = data.webhookUrl;
  });

  [userIdsInput, webhookInput].forEach((el) => {
    el.addEventListener("input", () => {
      chrome.storage.sync.set({
        userIds: userIdsInput.value.trim(),
        webhookUrl: webhookInput.value.trim(),
      });
    });
  });

  panel.querySelector("#startBtn").addEventListener("click", async () => {
    const userIdsRaw = userIdsInput.value.trim();
    const webhookUrl = webhookInput.value.trim();
    if (!userIdsRaw || !webhookUrl) {
      status.style.color = "red";
      status.textContent = "Please fill both fields.";
      return;
    }
    const userIds = userIdsRaw.split(",").map(s => parseInt(s.trim())).filter(Boolean);

    status.style.color = "white";
    status.textContent = "Starting monitor...";

    chrome.runtime.sendMessage({ type: "start_monitor", userIds, webhook: webhookUrl, intervalMinutes: 5 }, (resp) => {
      if (!resp) {
        status.style.color = "red";
        status.textContent = "No response from background.";
        return;
      }
      if (resp.ok) {
        status.style.color = "lightgreen";
        status.textContent = "Monitoring started.";
      } else {
        status.style.color = "red";
        status.textContent = `Error: ${resp.error || resp.message}`;
      }
    });
  });

  panel.querySelector("#stopBtn").addEventListener("click", () => {
    status.style.color = "white";
    status.textContent = "Stopping...";
    chrome.runtime.sendMessage({ type: "stop_monitor" }, (resp) => {
      if (resp && resp.ok) {
        status.style.color = "lightblue";
        status.textContent = "Monitoring stopped.";
      } else {
        status.style.color = "red";
        status.textContent = "Failed to stop.";
      }
    });
  });

  openOptions.addEventListener("click", (e) => {
    e.preventDefault();
    // open extension options page (where user can set manual token / toggle cookie usage)
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open(chrome.runtime.getURL("options.html"));
    }
  });

  // theme watcher (keeps original)
  const htmlEl = document.querySelector("html");
  const observer = new MutationObserver(() => {
    const isDark = htmlEl.classList.contains("dark-theme");
    document.querySelector("#rbx-presence-panel").setAttribute("data-theme", isDark ? "dark" : "light");
  });
  observer.observe(htmlEl, { attributes: true, attributeFilter: ["class"] });
})();
