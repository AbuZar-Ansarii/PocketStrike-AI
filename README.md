# ⚡ PocketStrike AI ⚡

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Termux%20%7C%20Android-green?style=for-the-badge&logo=android" alt="Platform" />
  <img src="https://img.shields.io/badge/Language-Python%20%7C%20JS-blue?style=for-the-badge&logo=python" alt="Languages" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="License" />
</p>

PocketStrike AI is a highly optimized, fully featured local AI assistant and security suite running directly inside **Termux on Android**. It couples a gorgeous, responsive, glassmorphic chat interface with an advanced **ReAct (Reasoning and Action) Function Calling Framework** to inspect your phone’s system parameters, run subnet-wide network sweeps, write and execute local sandboxed python scripts, search the web using RAG, and audit Android system security.

Additionally, it integrates a **Telegram Bot** backend, allowing you to trigger any of these system tools or query your AI models remotely from your Telegram app.

---

## 🚀 Daily Quick Launch (One-Liner)
If you already completed the setup, open Termux and run this single command to launch your dashboard:
```bash
cd ~/PocketStrike-AI && ./launch.sh
```

---

## ✨ Features

*   **Beautiful Responsive UI**: Stunning default Obsidian Dark Mode (with Emerald Green highlights) and a clean Royal Blue Light Mode. Features a glassmorphic sidebar for chat history, editable chat sessions, and instant message copying.
*   **Termux & Mobile Optimized**: Pure lightweight code. Uses raw Python `requests` and vanilla JS. Compiles and starts instantly without heavy compiled C-based SDKs (like official OpenAI or Google GenAI libraries) that freeze mobile chips.
*   **Stateful persistent Terminal Session**: Maintains directory changes (`cd`) and environmental variables across multiple command runs, operating inside a persistent background shell.
*   **Subnet-Wide Network Sweeps**: Scans class C subnets (1-254) in less than 3 seconds using 80 parallel workers, resolving device hostnames automatically.
*   **Parallel Port Scanner**: Checks up to 100 ports concurrently on local hosts using thread pools, automatically identifying active service names (SSH, HTTP, Database, etc.).
*   **Deep RAG Web Search**: Scrapes DuckDuckGo HTML and automatically fetches the actual main body text of the top 2 web pages in the background. It feeds this text directly to the AI, bypassing knowledge cutoff limitations.
*   **Android Security Auditor**: Checks Android OS release version, API SDK level, root trails (`su` binaries), USB debugging developer options, and package update states to compile local security recommendation lists.
*   **AI Self-Evolution (Persistent Memory)**: Uses a local sandboxed file workspace. The AI can dynamically write to `memory.json` (facts, settings) or `instructions.txt` (core behaviors). These files are dynamically re-injected into the system prompt on every turn so the AI grows and learns with you.
*   **Collapsible Console Badges**: Keeps chat logs tidy! Execution logs and system tool outputs are rendered as dark collapsible terminal blocks in the chat window, hidden by default with a clean `(Click to Expand)` header.
*   **Multiline Mobile Input**: Full Shift+Enter newlines on desktop, and native keyboard Return/Enter newlines on mobile keyboards to type long, structured prompts.

---

## 🛠️ Installation & Setup on Termux

Follow these steps to configure your Termux server:

### Step 1: Clone and Run the Installer
Launch Termux and run this one-line command to install all basic dependencies (Python, Git, Flask, Requests):
```bash
git clone https://github.com/AbuZar-Ansarii/PocketStrike-AI.git && cd PocketStrike-AI && chmod +x install.sh && ./install.sh
```
*Note: During installation, the script will request Android Storage Permissions (`termux-setup-storage`). Tap "Allow" on the system popup.*

### Step 2: Configure Setup Wizard
Run the launcher:
```bash
./launch.sh
```
1. Select option `1` to run the **Setup Wizard**.
2. Select your AI provider and fill in the details:
   *   **Google Gemini** (gemini-1.5-flash, gemini-1.5-pro)
   *   **OpenAI** (gpt-4o, gpt-4-turbo, etc.)
   *   **Anthropic Claude** (claude-3-5-sonnet, etc.)
   *   **Ollama** (Auto-configures to `http://localhost:11434` for offline local models like Llama3, Phi3, Gemma, etc.)
   *   **OpenCode & OpenCode Zen** (mimo, deepseek-v4-flash-free, etc.)
   *   **OpenRouter** & **Custom APIs** (compatible with OpenAI format)
3. Select whether to enable **Telegram Bot integration** (requires your Bot Token and Chat ID).

### Step 3: Run the Server
Choose option `2` from the launcher. Open the **Local URL** in your phone's browser or the **Network URL** on your PC to start chatting!

---

## 🔧 ReAct Function Calling Tools
PocketStrike AI has access to 28 local tools to audit, crawl, and control systems:

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
| 12 | `read_file_content(path)` | Reads a text file from the workspace (up to 15,000 characters). |
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
| 24 | `take_screenshot()` | Captures the phone's active screen (requires local ADB). |
| 25 | `tap_screen(x, y)` | Simulates a screen touch event at coordinates (x, y) using local ADB. |
| 26 | `swipe_screen(x1, y1, x2, y2, ms)`| Simulates a screen swipe gesture from (x1, y1) to (x2, y2) using local ADB. |
| 27 | `press_key(key_code)` | Simulates a physical key event (Home, Back, Power, volume keys) using ADB. |
| 28 | `launch_app(pkg_name)` | Opens any application on the device by its package bundle name using ADB. |
| 29 | `control_android_system(act, tgt)`| Toggles flashlight, Wi-Fi, Bluetooth, dark mode, battery saver, DND, auto-rotate, expand/collapse notifications, gets current focal app, or types text. |

---

## 🔒 Security Sandbox Guardrails
*   **Path Enforcement**: The AI is strictly sandboxed. All write/read operations normalize path traversals (`..`) and resolve absolute real paths. If the AI tries to write or modify anything outside of `~/storage/shared/PocketStrike-AI`, the sandbox blocks it with an access denied error.
*   **Core Code Protection**: Overwriting or modifying critical codebase files (like `server.py`, `setup.py`, `launch.sh`, etc.) is blocked by name, keeping the AI from corrupting its own server threads.
*   **Command Filter**: `execute_termux_command` filters and blocks dangerous destructive tokens (such as `rm -rf`, `rm -f /`, `mkfs`, `dd`) to protect the device.

---

## 📂 Project Layout
*   `server.py`: Main Flask application, proxy APIs, stream response generators, ReAct engine, and Telegram Polling loop.
*   `setup.py`: CLI Setup Wizard.
*   `install.sh`: Setup dependency installer script.
*   `launch.sh`: Main visual console launcher dashboard.
*   `templates/index.html`: Chat dashboard template.
*   `static/style.css`: Layout stylesheet.
*   `static/script.js`: Event handlers, Stream EventSource reader, and Markdown parsing compiler.
