#!/usr/bin/env python3
import json
import os
import sys
import socket
import threading
import time
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

# Setup Flask App
# We serve templates from 'templates' and static files from 'static'
app = Flask(__name__, template_folder='templates', static_folder='static')

# Global variables
CONFIG_FILE = "config.json"
config = {}
telegram_bot_thread = None

# Load configuration
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
    return False

# Get Local IP Address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external address (does not send data)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Call selected AI provider
def call_ai_api(messages):
    provider = config.get("provider")
    model = config.get("model")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    if not provider:
        return "Error: AI Provider is not configured."

    try:
        # 1. Google Gemini API
        if provider == "gemini":
            # Map OpenAI messages format to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": contents}

            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                data = res.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return f"Error: Unexpected Gemini response format. Details: {res.text}"
            else:
                return f"Gemini API Error (Status {res.status_code}): {res.text}"

        # 2. Anthropic Claude API
        elif provider == "anthropic":
            url = f"{base_url}/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Separate system prompt
            system_prompt = ""
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": anthropic_messages
            }
            if system_prompt:
                payload["system"] = system_prompt

            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                data = res.json()
                try:
                    return data["content"][0]["text"]
                except (KeyError, IndexError):
                    return f"Error: Unexpected Anthropic response format. Details: {res.text}"
            else:
                return f"Anthropic API Error (Status {res.status_code}): {res.text}"

        # 3. OpenAI and compatible APIs (OpenRouter, OpenCode, OpenCode Zen, Ollama, Custom)
        else:
            url = f"{base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "model": model,
                "messages": messages
            }

            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                data = res.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    return f"Error: Unexpected API response format. Details: {res.text}"
            else:
                return f"API Error (Status {res.status_code}): {res.text}"

    except Exception as e:
        return f"Request Error: {str(e)}"

# Telegram Bot Polling Thread
def telegram_bot_loop(token):
    offset = 0
    sessions = {} # Holds history for each telegram user: chat_id -> list of messages
    print(f"Telegram Bot started polling...")
    
    while True:
        try:
            # Poll for updates
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35)
            if res.status_code != 200:
                time.sleep(5)
                continue
                
            updates = res.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                
                message = update.get("message") or update.get("edited_message")
                if not message:
                    continue
                    
                chat = message.get("chat")
                if not chat:
                    continue
                    
                chat_id = chat["id"]
                text = message.get("text", "")
                
                if not text:
                    continue

                print(f"Telegram Msg from {chat_id}: {text[:30]}...")

                # Handle /start or initialize session
                if text.strip() == "/start":
                    sessions[chat_id] = [
                        {"role": "system", "content": "You are PocketstrikeAI, a helpful, cool, and highly advanced local AI assistant. Keep responses engaging."}
                    ]
                    welcome_text = "⚡ **PocketstrikeAI Online** ⚡\n\nHello! I am your AI assistant running locally on Termux. Ask me anything!"
                    send_telegram_msg(token, chat_id, welcome_text)
                    continue

                if chat_id not in sessions:
                    sessions[chat_id] = [
                        {"role": "system", "content": "You are PocketstrikeAI, a helpful, cool, and highly advanced local AI assistant. Keep responses engaging."}
                    ]
                
                # Append user prompt
                sessions[chat_id].append({"role": "user", "content": text})
                
                # Limit message history to prevent token overflow (keep last 15 messages)
                if len(sessions[chat_id]) > 15:
                    # Keep system prompt at index 0, then slice the last 14 messages
                    sessions[chat_id] = [sessions[chat_id][0]] + sessions[chat_id][-14:]

                # Send typing status
                requests.post(f"https://api.telegram.org/bot{token}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

                # Get AI answer
                ai_response = call_ai_api(sessions[chat_id])
                
                # Append AI response to session
                sessions[chat_id].append({"role": "assistant", "content": ai_response})
                
                # Send back to Telegram
                send_telegram_msg(token, chat_id, ai_response)

        except Exception as e:
            print(f"Telegram Bot error: {e}")
            time.sleep(5)

def send_telegram_msg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    # Try sending with Markdown
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        # Fallback to plain text if Telegram fails due to malformed markdown
        payload.pop("parse_mode", None)
        requests.post(url, json=payload)

# Web Server Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
        
    response_text = call_ai_api(messages)
    return jsonify({"response": response_text})

@app.route('/api/status', methods=['GET'])
def get_status():
    status = {
        "provider": config.get("provider_name", "None"),
        "model": config.get("model", "None"),
        "telegram_enabled": config.get("telegram_enabled", False),
        "telegram_status": "Active" if config.get("telegram_enabled", False) else "Disabled"
    }
    return jsonify(status)

# Serve static files correctly if needed
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # 1. Load config
    if not load_config():
        print("⚠️ Warning: config.json not found! Please run the Setup Wizard first.")
        print("Starting anyway in fallback mode...")

    # 2. Launch Telegram Bot if enabled
    if config.get("telegram_enabled") and config.get("telegram_token"):
        tg_token = config["telegram_token"]
        telegram_bot_thread = threading.Thread(target=telegram_bot_loop, args=(tg_token,), daemon=True)
        telegram_bot_thread.start()
        print("✓ Telegram Bot Thread Spawned.")
    else:
        print("✗ Telegram Bot integration is disabled or not configured.")

    # 3. Print access information
    local_ip = get_local_ip()
    green_color = "\033[38;5;46m"
    white_color = "\033[38;5;255m"
    reset_color = "\033[0m"
    banner_text = f"""{green_color}██████╗  ██████╗  ██████╗██╗  ██╗███████╗████████╗███████╗██████╗  ██╗██╗  ██╗███████╗     █████╗ ██╗
██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗ ██║██║ ██╔╝██╔════╝    ██╔══██╗██║
{white_color}██████╔╝██║   ██║██║     █████╔╝ █████╗     ██║   ███████╗██████╔╝ ██║█████╔╝ █████╗      ███████║██║
██╔═══╝ ██║   ██║██║     ██╔═██╗ ██╔══╝     ██║   ╚════██║██╔══██╗ ██║██╔═██╗ ██╔══╝      ██╔══██║██║
██║     ╚██████╔╝╚██████╗██║  ██╗███████╗   ██║   ███████║██║  ██║ ██║██║  ██╗███████╗    ██║  ██║██║
╚═╝      ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═╝╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝{reset_color}"""
    print(banner_text)
    print(f"{green_color}───────────────────────── Server is Starting ─────────────────────────{reset_color}")
    print(f"  Local URL:     {white_color}http://127.0.0.1:5000{reset_color}")
    print(f"  Network URL:   {white_color}http://{local_ip}:5000{reset_color}")
    print(f"  AI Provider:   {white_color}{config.get('provider_name', 'None')}{reset_color}")
    print(f"  Model:         {white_color}{config.get('model', 'None')}{reset_color}")
    print(f"{green_color}──────────────────────────────────────────────────────────────────────{reset_color}\n")

    # Run Flask
    # Host is 0.0.0.0 so they can access it from their phone browser as well as external devices on local network
    app.run(host='0.0.0.0', port=5000, debug=False)
