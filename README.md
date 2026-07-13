# ⚡ PocketstrikeAI ⚡

A fully-featured, gorgeous, local AI chat server designed to run efficiently on **Android via Termux**. 

PocketstrikeAI provides a stunning glassmorphic web interface (inspired by Claude, GPT, and Gemini) with full conversation history stored locally on your device, auto-resizing textareas, syntax-highlighted code blocks, and instant copying. Additionally, it integrates a **Telegram Bot** backend, allowing you to query your configured AI models directly through Telegram.

---

## ✨ Features

- **Beautiful Web Interface**: Obsidians, purples, and hot-pinks with a futuristic glassmorphic aesthetic. Responsive sidebar for chat history, custom editable titles, suggestions grid, and smooth micro-animations.
- **Termux Optimized**: Extremely lightweight. Built with vanilla Python, Flask, and raw HTTP calls. No heavy C-based packages (like official OpenAI or Google SDKs) that often fail to compile or take hours on mobile processors.
- **Multi-Provider Setup Wizard**: Configures and runs major AI providers out of the box:
  - Google Gemini
  - OpenAI (GPT-4o, etc.)
  - Anthropic Claude
  - Ollama (for running offline local LLMs directly on your phone)
  - OpenRouter (for free/paid endpoints)
  - OpenCode & OpenCode Zen (curated developer model gateways)
  - Custom API (any OpenAI-compatible base URL)
- **Telegram Bot Integration**: A background thread polling system that routes Telegram messages to your configured AI and maintains separate chat sessions for users.
- **One-Line Installation**: Straightforward install process designed specifically for Android Termux environment.

---

## 🛠️ Installation & Setup on Termux

Follow these steps to get PocketstrikeAI running on your Android phone:

### Step 1: Open Termux and Run the Installer
Run this one-line command to clone the repository and run the setup dependencies installer automatically:

```bash
git clone https://github.com/AbuZar-Ansarii/PocketStrike-AI.git && cd PocketStrike-AI && chmod +x install.sh && ./install.sh
```

### Step 2: Launch and Run Setup
Run the launcher:
```bash
./launch.sh
```

You will see the launcher menu:
```
==================================================
          PocketstrikeAI Launcher                 
==================================================
 Please choose an option:

  [ ] 1. Run Setup Wizard
      2. Launch PocketstrikeAI Server & Bot
      3. Exit
==================================================
```

1. Enter **`1`** to run the setup wizard.
2. Select your AI provider, enter your API key (if needed), choose a model (or enter a custom one), and decide if you want Telegram Bot integration.
3. Once completed, a green checkmark `[✓]` will appear next to the Setup option.

### Step 3: Launch the AI Server
Choose option **`2`** from the launcher menu. PocketstrikeAI will boot up:

```
==================================================
      PocketstrikeAI Server is Starting! 
==================================================
Local URL:     http://127.0.0.1:5000
Network URL:   http://192.168.1.15:5000
AI Provider:   Google Gemini
Model:         gemini-1.5-flash
==================================================
```

Open the **Local URL** in your Android web browser to start chatting!
If your phone and PC are connected to the same Wi-Fi, you can open the **Network URL** on your PC to chat using your phone's Termux server!

---

## 📂 Project Structure

- `install.sh`: Automated package updater and dependency installer.
- `launch.sh`: Interactive shell dashboard.
- `setup.py`: Step-by-step terminal CLI wizard for configuring `config.json`.
- `server.py`: Flask application serving the web UI and proxying requests. Spawns the Telegram bot thread if enabled.
- `templates/index.html`: Fully self-contained interface, using inline SVG graphics for offline reliability.
- `static/style.css`: Responsive, glassmorphic visual stylesheet.
- `static/script.js`: State manager, chat layout generator, and custom Markdown compiler.
