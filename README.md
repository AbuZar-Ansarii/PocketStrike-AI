<img width="2009" height="461" alt="PocketStrike" src="https://github.com/user-attachments/assets/e4121dc8-b1d6-4bbd-b678-6d4853d8a33b" />



<p align="center">
  <img src="https://img.shields.io/badge/Platform-Termux%20%7C%20Android-green?style=for-the-badge&logo=android" alt="Platform" />
  <img src="https://img.shields.io/badge/Language-Python%20%7C%20JS-blue?style=for-the-badge&logo=python" alt="Languages" />
  <img src="https://img.shields.io/badge/Tools-52%20Built--in%20+%20MCP-purple?style=for-the-badge" alt="Tools" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="License" />
</p>

PocketStrike AI is a highly optimized, fully featured local AI assistant, background automation engine, and cybersecurity suite running directly inside Termux on Android. It couples a gorgeous, responsive, glassmorphic chat interface with an advanced ReAct (Reasoning and Action) Function Calling Framework and native Model Context Protocol (MCP) support. This allows you to inspect your phone’s system parameters, run subnet-wide network sweeps, execute background crons, dump active UI layouts for device automation, run sandboxed Python scripts, search the web using RAG, and connect to remote tool servers over SSE (Server-Sent Events) to execute cloud microservices.

Additionally, it integrates a Telegram Bot backend with unified session tracking, allowing you to trigger any of these system tools, check background schedules, or query your AI models remotely from your Telegram app.

---

## 🚀 Daily Quick Launch (One-Liner)
If you already completed the setup, open Termux and run this single command to launch your dashboard:
```bash
cd ~/PocketStrike-AI && bash launch.sh
```

---

## 📂 Project Structure
```text
📂 PocketStrike-AI/
├── 📄 LICENSE                # Open-source MIT License terms
├── 📄 README.md              # Detailed documentation, guides, and tool specifications
├── 📄 install.sh             # Dependency installer (Python, Git, Termux-API, Nmap, Curl, etc.)
├── 📄 launch.sh              # Terminal-based visual launcher dashboard and status check
├── 📄 server.py              # Main Flask server, AI ReAct framework, and Telegram bot loop
├── 📄 setup.py              # CLI Setup Wizard for API keys and Telegram bot options
├── 📂 static/                # Static assets for the Web chat interface
│   ├── 📄 script.js          # Web event handling, EventSource streaming, and markdown parsing
│   └── 📄 style.css          # obsidian-dark / royal-blue responsive layout stylesheet
└── 📂 templates/             # HTML Templates
    └── 📄 index.html         # Glassmorphic, modern chat dashboard interface
```

---

## ✨ Features

*   **Unified Chat History Engine**: The agent maintains a single unified mind across platforms. Messages sent via Telegram are instantly visible in the Web interface, and vice-versa, synchronizing context in real-time.
*   **60-Message sliding window**: Supports deep conversation tracking by passing up to the last 60 message states to the LLM API, while preserving complete logs on local storage.
*   **Self-Evolving Long-Term Memory**: The AI dynamically updates `memory.json` (user facts, parameters) and `instructions.txt` (core behaviors). These files are re-injected on every turn alongside a dynamic system clock header to calculate scheduled time offsets.
*   **Persistent Background Scheduler**: A daemon thread checks for scheduled reminders or recurring cron intervals (e.g. *"remind me to blink my eyes every 1 minute"*) and alerts you locally or via Telegram.
*   **Audio Beep & System Fallback**: If the device lacks Termux:API, the scheduler utilizes the ASCII Bell code (`\a`) to beep/vibrate Termux natively, and dynamically redirects screen alerts to Telegram.
*   **Robust ADB/Shizuku execution**: Features parameter-safe parsing and automatic standard ADB fallbacks if the Shizuku emulator binder (`rish`) becomes unauthorized or goes offline.
*   **Web & Network Security Auditors**: Built-in scanners to detect active Wi-Fi Man-in-the-Middle (ARP Spoofing) attacks, audit VPN connection leaks, and evaluate SSL certificates and HTTP security headers.
*   **Stateful persistent Terminal Session**: Maintains directory changes (`cd`) and environmental variables across multiple command runs, operating inside a persistent background shell.
*   **Subnet-Wide Network Sweeps**: Scans class C subnets (1-254) in less than 3 seconds using 80 parallel workers, resolving device hostnames automatically.
*   **Parallel Port Scanner**: Checks up to 100 ports concurrently on local hosts using thread pools, automatically identifying active service names (SSH, HTTP, Database, etc.).
*   **Deep RAG Web Search**: Scrapes DuckDuckGo HTML and automatically fetches the actual main body text of the top 2 web pages in the background. It feeds this text directly to the AI, bypassing knowledge cutoff limitations.

---

## 🛠️ Installation & Setup on Termux

Follow these steps to configure your Termux server:

### Step 1: Install Git in Termux
Run this command to install git 
```
pkg install git
```
### Step 2: Clone and Run the Installer
Launch Termux and run this one-line command to install all basic dependencies (Python, Git, Flask, Requests, Termux-API, Nmap, Dnsutils, Curl, Net-Tools, Iproute2, and Traceroute):
```bash
git clone https://github.com/AbuZar-Ansarii/PocketStrike-AI.git && cd PocketStrike-AI && sed -i 's/\r$//' install.sh && bash install.sh
```
*Note: During installation, the script will request Android Storage Permissions (`termux-setup-storage`). Tap "Allow" on the system popup.*

> [!TIP]
> **Getting "CANNOT LINK EXECUTABLE" Error?**
> This is a common Termux issue caused by a corrupted/outdated Termux environment (e.g. if installed from Google Play instead of F-Droid). Fix your Termux package manager by running:
> ```bash
> apt update && apt full-upgrade
> ```
> If Termux is completely locked, uninstall your current version and download the official updated build from **F-Droid** or **GitHub Releases**.

### Step 3: Configure Setup Wizard
Run the launcher:
```bash
bash launch.sh
```
1. Select option `1` to run the **Setup Wizard**.
2. Select your AI provider and fill in the details:
   *   **Google Gemini** (gemini-1.5-flash, gemini-1.5-pro)
   *   **OpenAI** (gpt-4o, gpt-4-turbo, etc.)
   *   **Anthropic Claude** (claude-3-5-sonnet, etc.)
   *   **Ollama** (Auto-configures to `http://localhost:11434` for offline local models like Llama3, Phi3, Gemma, etc.)
   *   **OpenRouter** & **Custom APIs** (compatible with OpenAI format)
3. Select whether to enable **Telegram Bot integration** (requires your Bot Token and Chat ID).

### Step 4: Run the Server
Choose option `2` from the launcher. Open the **Local URL** in your phone's browser or the **Network URL** on your PC to start chatting!

---

## 🔌 Model Context Protocol (MCP) Integration
PocketStrike AI natively supports the **Model Context Protocol (MCP)** using the HTTP/SSE (Server-Sent Events) transport. This turns your Termux AI agent into an MCP Client, enabling it to dynamically load, query, and run tools hosted on remote servers (e.g., your PC, local network, or cloud).

### How to Connect a Remote Server:
1. **Host Binding**: Start your MCP server on the host machine. To allow connections from your phone, ensure you bind it to `0.0.0.0` (all network cards) and select the SSE transport.
   * *Example running a Python FastMCP script:*
     ```bash
     fastmcp run --host 0.0.0.0 --transport sse your_script.py
     ```
2. **Retrieve PC IP**: Locate the host PC's local IP address (e.g., `192.168.11.131`).
3. **Register on Dashboard**: Open the PocketStrike Web UI on your phone:
   * Tap the **`+`** button in the **MCP Connections** section of the sidebar.
   * Provide a **Server Name** (e.g., `dice-roller`).
   * Enter the **SSE Endpoint URL** (e.g., `http://192.168.11.131:8000/sse`).
4. **Automatic Handshake**: PocketStrike AI will establish an active SSE stream connection, perform the official **initialize/initialized protocol handshake**, fetch the available tools, and automatically inject the remote tool schemas directly into the AI's instruction set.
5. **Real-time Execution**: When the AI runs a remote tool, the request is wrapped in a standard JSON-RPC 2.0 structure, POSTed over the Wi-Fi network, and the result is returned live to the chat thread!

---

## 🛡️ Local Privacy & Unified Memory Core

PocketStrike AI is built with privacy-first principles. **Zero conversation data is leaked to external cloud history trackers.**

*   **Unified Conversation Log (`unified_history.json`):** Your conversations are saved locally in a single private JSON database in your internal workspace, syncing Web chats and Telegram streams.
*   **Self-Evolution Memory Loop:** 
    *   **`memory.json`**: The AI maintains a local log of user preferences, habits, working styles, and goals. It updates this file dynamically using its tools when it learns new facts about you.
    *   **`instructions.txt`**: Saves custom behavior directives, formatting preferences, and script execution rules.
    *   *These memory blocks are automatically re-injected into the system prompt on every turn, allowing the agent to dynamically grow and adapt specifically to you over time.*

## 🔒 Security Sandbox Guardrails
*   **Path Enforcement**: The AI is strictly sandboxed. All write/read operations normalize path traversals (`..`) and resolve absolute real paths. If the AI tries to write or modify anything outside of `~/storage/shared/PocketStrike-AI`, the sandbox blocks it with an access denied error.
*   **Core Code Protection**: Overwriting or modifying critical codebase files (like `server.py`, `setup.py`, `launch.sh`, etc.) is blocked by name, keeping the AI from corrupting its own server threads.
*   **Command Filter**: `execute_termux_command` filters and blocks dangerous destructive tokens (such as `rm -rf`, `rm -f /`, `mkfs`, `dd`) to protect the device.

---

## 🔧 ReAct Function Calling Tools

PocketStrike AI has access to **50 built-in local tools** to audit, crawl, and control systems:

| # | Tool Name | Description |
|---|---|---|
| 1 | `get_system_stats()` | Returns battery capacity, charging state, free RAM, and storage space. |
| 2 | `local_network_scan()` | Discovers active subnet hosts in parallel, returning IPs and hostnames. |
| 3 | `subnet_port_sweep(port)` | Sweeps the entire subnet checking which hosts are listening on a specific port. |
| 4 | `local_port_scan(ip, ports)` | Scans up to 100 ports concurrently, returning open ports and service details. |
| 5 | `execute_termux_command(cmd)`| Executes shell commands inside a persistent, stateful background bash process. |
| 6 | `audit_android_security()` | Performs a security check on Android patch age, root binaries, and USB debugging. |
| 7 | `web_search(query)` | DDG Search with background parallel RAG content fetching. |
| 8 | `fetch_url(url)` | Downloads clean text from any URL, stripping HTML layout and JS scripts. |
| 9 | `list_local_listeners()` | Lists active listening ports on the local Termux host (similar to `netstat`). |
| 10 | `get_network_details()` | Returns IP address interfaces, routing tables, and gateway IPs. |
| 11 | `list_directory(path)` | Lists files inside the sandboxed workspace folder. |
| 12 | `read_file_content(path, off, lim)`| Reads a text file from the workspace. Supports paging via offset/limit parameters. |
| 13 | `write_file_content(path, c)`| Writes or overwrites a script/file inside the workspace. |
| 14 | `search_files(pattern)` | Recursively searches workspace files using glob matching. |
| 15 | `run_python_script(name, args)`| Runs a Python script written by the AI inside the workspace sandbox. |
| 16 | `send_android_notification()`| Sends a system lockscreen notification banner using Termux:API. |
| 17 | `vibrate_device(ms)` | Vibrates the phone for a specified duration. |
| 18 | `take_camera_photo(cam_id)` | Snaps a photo using front ("1") or back ("0") camera and saves to workspace. |
| 19 | `get_phone_location()` | Retrieves GPS coordinates of the device (latitude, longitude, altitude). |
| 20 | `make_phone_call(number)` | Places an outgoing call to the specified number using Termux:API. |
| 21 | `send_sms(number, msg)` | Sends an SMS text message using Termux:API. |
| 22 | `set_brightness(level)` | Adjusts screen brightness level (0 to 255) using Termux:API. |
| 23 | `set_volume(stream, level)` | Adjusts volume streams (music, ring, alarm, notification, system). |
| 24 | `take_screenshot()` | Captures the phone's active screen (requires local ADB or Shizuku). |
| 25 | `tap_screen(x, y)` | Simulates a screen touch event at coordinates (x, y) using local ADB/Shizuku. |
| 26 | `swipe_screen(x1, y1, x2, y2, ms)`| Simulates a screen swipe gesture from (x1, y1) to (x2, y2) using ADB/Shizuku. |
| 27 | `press_key(key_code)` | Simulates a physical key event (Home, Back, Power) using ADB/Shizuku. |
| 28 | `launch_app(pkg_name)` | Opens any application on the device by its package bundle name using ADB/Shizuku. |
| 29 | `control_android_system(act, tgt)`| Flashlight, Wi-Fi, Bluetooth, Dark Mode, expand notifications, input text. |
| 30 | `get_clipboard()` | Returns the current text contents of the Android system clipboard. |
| 31 | `set_clipboard(text)` | Overwrites the Android system clipboard with the specified text. |
| 32 | `list_installed_apps(user_only)`| Lists all installed app package names and their APK paths (user or system apps). |
| 33 | `scan_wifi_networks()` | Scans nearby Wi-Fi hotspots and returns network details. |
| 34 | `speak_text(text)` | Uses the Android Text-To-Speech (TTS) engine to read the specified text aloud. |
| 35 | `dns_lookup(domain, rec_type)`| Performs custom DNS queries (A, MX, TXT, CNAME, etc.) for a domain. |
| 36 | `whois_lookup(domain)` | Queries WHOIS registry details to look up domain registrars and age info. |
| 37 | `analyze_hash(hash_str)` | Analyzes cryptographic hashes (MD5, SHA, bcrypt) to identify algorithms. |
| 38 | `open_url_on_phone(url)` | Launches a browser intent to view a URL or open a Google search query on screen. |
| 39 | `execute_root_command(cmd)` | Executes a root shell instruction via 'su -c' (requires root privileges). |
| 40 | `audit_sms_inbox(limit)` | Audits recent SMS inbox messages for scam links or spam threats (Termux-API). |
| 41 | `ip_geolocation_lookup(ip)`| Performs a geographic coordinates and ISP lookup on a remote IP address. |
| 42 | `read_phone_sensors(name)` | Lists all hardware sensors or reads real-time data from a selected sensor. |
| 43 | `dump_ui_layout()` | Dumps active screen layout XML and returns a parsed list of click targets. |
| 44 | `add_scheduled_task(type, trig, desc, tgt)`| Schedules a background reminder ('reminder') or recurring job ('cron'). |
| 45 | `list_scheduled_tasks()` | Displays all active, pending, or recurring schedules. |
| 46 | `remove_scheduled_task(id)`| Cancels and deletes a scheduled task or cron job by its ID. |
| 47 | `detect_arp_spoofing()` | Inspects ARP tables to detect active Man-in-the-Middle network sniffers. |
| 48 | `audit_vpn_connection()` | Audits public IP/ISP and checks local interface tables for VPN leaks. |
| 49 | `audit_website_security(url)`| Audits HTTP security headers and queries SSL handshake validity parameters. |
| 50 | `search_file_content(q, pat)`| Recursively searches text inside all workspace files matching a glob filter. |
| 51 | `delete_file(file_path)` | Deletes a file or recursively deletes a directory inside your workspace directory. |
| 52 | `download_file(url, file_name)` | Downloads a file (binary or text, like images, scripts, security payloads) from a web URL and saves it directly in your workspace directory. |
