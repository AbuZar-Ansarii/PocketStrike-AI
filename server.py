#!/usr/bin/env python3
import json
import os
import sys
import socket
import threading
import time
import requests
import re
import ast
import shutil
from flask import Flask, request, jsonify, render_template, send_from_directory, Response

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

# ==========================================
# CUSTOM AI TOOLS DEFINITIONS
# ==========================================

# Define Android Internal Storage Workspace Folder
def get_android_workspace():
    paths = [
        os.path.expanduser("~/storage/shared/PocketStrike-AI"),
        "/sdcard/PocketStrike-AI",
        "/storage/emulated/0/PocketStrike-AI"
    ]
    for p in paths:
        try:
            # Check if parent is writable/exists, or try making the dir
            parent = os.path.dirname(p)
            if os.path.exists(parent) and os.access(parent, os.W_OK):
                os.makedirs(p, exist_ok=True)
                return os.path.abspath(p)
            os.makedirs(p, exist_ok=True)
            return os.path.abspath(p)
        except Exception:
            continue
    # Fallback to local subdirectory if shared storage is not accessible (e.g. running on PC/dev host)
    fallback = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))
    os.makedirs(fallback, exist_ok=True)
    return fallback

WORKSPACE_DIR = get_android_workspace()

def get_system_prompt():
    # Read persistent memory
    memory_content = "No facts stored yet."
    memory_path = os.path.join(WORKSPACE_DIR, "memory.json")
    if os.path.exists(memory_path):
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                memory_content = f.read().strip()
        except Exception:
            pass
            
    # Read learned instructions
    instructions_content = "No custom instructions saved yet."
    instructions_path = os.path.join(WORKSPACE_DIR, "instructions.txt")
    if os.path.exists(instructions_path):
        try:
            with open(instructions_path, "r", encoding="utf-8") as f:
                instructions_content = f.read().strip()
        except Exception:
            pass

    return f"""You are PKST AI, a powerful local security and system assistant running in Termux on the user's Android phone.
You are a self-evolving AI agent: you can grow, learn, and expand your capabilities over time by writing scripts, learning new rules, and persisting your memory.

Your workspace directory is: {WORKSPACE_DIR} (which is located in the phone's internal storage).
All file tools (list_directory, read_file_content, write_file_content, run_python_script) resolve relative paths inside this workspace directory. Always write/save files requested by the user inside this workspace folder.
Critical: You are forbidden from modifying, writing, or deleting files outside this workspace directory, especially the server's own scripts (server.py, setup.py, launch.sh, etc.) to prevent messing with your own running code.

AI PERSISTENT MEMORY (Use write_file_content to update 'memory.json' to store facts, user preferences, configurations, or network details):
{memory_content}

AI SELF-EVOLUTION INSTRUCTIONS (Use write_file_content to update 'instructions.txt' to add new behavioral rules or instructions for yourself):
{instructions_content}

If you need to use a tool to answer the user's request, you must respond with EXACTLY this trigger format and nothing else in that turn:
[TOOL_CALL: tool_name(arg1="value", arg2="value")]

Available Tools:
1. get_system_stats()
   Returns battery level, charging status, free RAM, and storage space in Termux.
2. local_port_scan(target_ip, ports_list=[...])
   Scans a target IP address for open ports. Use lists like [22, 80, 443]. Keep target list short.
3. list_directory(path=".")
   Lists files and directories. Defaults to your workspace directory ({WORKSPACE_DIR}).
4. read_file_content(file_path)
   Reads the content of a text file inside your workspace directory.
5. write_file_content(file_path, content)
   Creates or overwrites a file inside your workspace directory. Useful for saving Python scripts or files (like 'memory.json' and 'instructions.txt').
6. run_python_script(script_name, args=[...])
   Runs a Python script written by you inside your workspace directory and returns its output. Use this to run custom scripts, write new tools, or build calculations.

Instructions:
- When a user asks you a question that requires a tool, output ONLY the tool call trigger. Do not include any prefix, suffix, or explanation in that turn.
- Once you receive the tool result, read it carefully and answer the user's question directly.
- Maintain a helpful, technical, and professional tone.
"""

def get_system_stats():
    stats = {}
    # Battery Capacity
    try:
        if os.path.exists("/sys/class/power_supply/battery/capacity"):
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                stats["battery_level"] = f.read().strip() + "%"
            with open("/sys/class/power_supply/battery/status", "r") as f:
                stats["battery_status"] = f.read().strip()
        else:
            raise FileNotFoundError()
    except Exception:
        # Fallback to termux command if available
        try:
            import subprocess
            res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                bat = json.loads(res.stdout)
                stats["battery_level"] = f"{bat.get('percentage')}%"
                stats["battery_status"] = bat.get("status")
        except Exception:
            stats["battery_level"] = "Unknown"
            stats["battery_status"] = "Unknown"
            
    # Disk Storage (Free Space in Termux home)
    try:
        total, used, free = shutil.disk_usage(os.path.expanduser("~"))
        stats["storage_total"] = f"{total / (2**30):.2f} GB"
        stats["storage_used"] = f"{used / (2**30):.2f} GB"
        stats["storage_free"] = f"{free / (2**30):.2f} GB"
    except Exception as e:
        stats["storage_error"] = str(e)
        
    # RAM Free (from /proc/meminfo)
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem_total = 0
                mem_free = 0
                mem_avail = 0
                for line in lines:
                    if "MemTotal" in line:
                        mem_total = int(line.split()[1])
                    elif "MemFree" in line:
                        mem_free = int(line.split()[1])
                    elif "MemAvailable" in line:
                        mem_avail = int(line.split()[1])
                if mem_total:
                    stats["ram_total"] = f"{mem_total / 1024:.2f} MB"
                    stats["ram_free"] = f"{mem_free / 1024:.2f} MB"
                    stats["ram_available"] = f"{mem_avail / 1024:.2f} MB"
        else:
            stats["ram"] = "Only readable on Android/Linux /proc/meminfo"
    except Exception:
        stats["ram"] = "Unknown"
        
    return json.dumps(stats, indent=2)

def local_port_scan(target_ip, ports_list=None):
    if not ports_list:
        ports_list = [21, 22, 23, 25, 53, 80, 110, 139, 443, 445, 1024, 1433, 3306, 3389, 5000, 8080, 8888]
    elif isinstance(ports_list, str):
        try:
            ports_list = json.loads(ports_list)
        except Exception:
            try:
                ports_list = [int(p.strip()) for p in ports_list.strip("[]").split(",") if p.strip()]
            except Exception:
                ports_list = [22, 80, 443, 8080]
                
    open_ports = []
    results = {"target": target_ip, "scanned_ports": len(ports_list)}
    
    # Limit number of ports to scan to prevent timeouts
    ports_list = ports_list[:30]
    
    for port in ports_list:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex((target_ip, int(port)))
            if result == 0:
                open_ports.append(int(port))
            s.close()
        except Exception:
            pass
    results["open_ports"] = open_ports
    return json.dumps(results, indent=2)

def list_directory(path="."):
    if path == "." or not path:
        target_path = WORKSPACE_DIR
    else:
        if not os.path.isabs(os.path.expanduser(path)):
            target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path))
        else:
            target_path = os.path.abspath(os.path.expanduser(path))
            
    if not os.path.exists(target_path):
        return f"Error: Path '{path}' does not exist."
    try:
        items = os.listdir(target_path)
        results = []
        for item in items:
            item_path = os.path.join(target_path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            results.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size_bytes": size
            })
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_file_content(file_path):
    if not os.path.isabs(os.path.expanduser(file_path)):
        target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, file_path))
    else:
        target_path = os.path.abspath(os.path.expanduser(file_path))
        
    if not os.path.exists(target_path):
        return f"Error: File '{file_path}' does not exist."
    if os.path.isdir(target_path):
        return f"Error: '{file_path}' is a directory. Use list_directory to see its contents."
        
    try:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(15000)
            if len(content) >= 15000:
                return content + "\n\n[Content truncated due to size limit...]"
            return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file_content(file_path, content):
    if not os.path.isabs(os.path.expanduser(file_path)):
        target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, file_path))
    else:
        target_path = os.path.abspath(os.path.expanduser(file_path))
        
    # Security Sandbox Check: Prevent path traversal or writing outside the workspace directory
    real_target = os.path.realpath(target_path)
    real_workspace = os.path.realpath(WORKSPACE_DIR)
    
    if not real_target.startswith(real_workspace):
        return f"Error: Write access denied. You are only allowed to write files inside your workspace: {WORKSPACE_DIR}"
        
    # Prevent touching main codebase files specifically by name (extra safety check)
    forbidden_files = ["server.py", "setup.py", "launch.sh", "install.sh", "config.json"]
    if os.path.basename(real_target) in forbidden_files:
        return f"Error: Editing critical system files ({os.path.basename(real_target)}) is forbidden to prevent server crash."
        
    try:
        os.makedirs(os.path.dirname(real_target), exist_ok=True)
        with open(real_target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File '{file_path}' written successfully inside workspace."
    except Exception as e:
        return f"Error writing file: {str(e)}"

def run_python_script(script_name, args=None):
    if not args:
        args = []
    elif isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = [args]
            
    # Resolve and sandbox path
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, script_name))
    real_target = os.path.realpath(target_path)
    real_workspace = os.path.realpath(WORKSPACE_DIR)
    
    if not real_target.startswith(real_workspace):
        return "Error: Script execution denied. You can only execute scripts inside your workspace."
        
    if not os.path.exists(real_target):
        return f"Error: Script '{script_name}' does not exist. Write it first using write_file_content."
        
    try:
        import subprocess
        cmd = [sys.executable, real_target] + [str(a) for a in args]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        output = f"Exit Code: {res.returncode}\n"
        if res.stdout:
            output += f"Stdout:\n{res.stdout}\n"
        if res.stderr:
            output += f"Stderr:\n{res.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Script execution timed out (limit: 30 seconds)."
    except Exception as e:
        return f"Error running script: {str(e)}"

def parse_arguments(arg_str):
    if not arg_str.strip():
        return {}
    kwargs = {}
    pattern = r'(\w+)\s*=\s*("[^"]*"|\'[^\']*\'|\[[^\]]*\]|[^,]+)'
    matches = re.findall(pattern, arg_str)
    for key, val in matches:
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        elif val.startswith('[') and val.endswith(']'):
            try:
                val = json.loads(val.replace("'", '"'))
            except Exception:
                try:
                    val = [int(x.strip()) for x in val[1:-1].split(",") if x.strip()]
                except Exception:
                    try:
                        val = [x.strip().strip('"\'') for x in val[1:-1].split(",") if x.strip()]
                    except Exception:
                        pass
        else:
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val.lower() == "none":
                val = None
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
        kwargs[key] = val
    return kwargs

def execute_local_tool(name, args_str):
    try:
        kwargs = parse_arguments(args_str)
        if name == "get_system_stats":
            return get_system_stats()
        elif name == "local_port_scan":
            target_ip = kwargs.get("target_ip")
            ports_list = kwargs.get("ports_list")
            if not target_ip:
                return "Error: Missing required argument 'target_ip'."
            return local_port_scan(target_ip, ports_list)
        elif name == "list_directory":
            path = kwargs.get("path", ".")
            return list_directory(path)
        elif name == "read_file_content":
            file_path = kwargs.get("file_path")
            if not file_path:
                return "Error: Missing required argument 'file_path'."
            return read_file_content(file_path)
        elif name == "write_file_content":
            file_path = kwargs.get("file_path")
            content = kwargs.get("content")
            if not file_path or content is None:
                return "Error: Missing required arguments 'file_path' and/or 'content'."
            return write_file_content(file_path, content)
        elif name == "run_python_script":
            script_name = kwargs.get("script_name")
            args = kwargs.get("args")
            if not script_name:
                return "Error: Missing required argument 'script_name'."
            return run_python_script(script_name, args)
        else:
            return f"Error: Tool '{name}' is not recognized."
    except Exception as e:
        return f"Error executing tool: {str(e)}"

def get_ai_response_with_tools(messages):
    # Ensure system prompt is present at index 0
    system_present = False
    for msg in messages:
        if msg["role"] == "system":
            system_present = True
            break
            
    if not system_present:
        messages.insert(0, {
            "role": "system",
            "content": get_system_prompt()
        })
        
    loop_count = 0
    max_loops = 5
    
    while loop_count < max_loops:
        response_text = call_ai_api(messages)
        
        # Check for tool call trigger
        match = re.search(r'\[TOOL_CALL:\s*(\w+)\((.*)\)\s*\]', response_text)
        if not match:
            messages.append({"role": "assistant", "content": response_text})
            return response_text, messages
            
        tool_name = match.group(1)
        tool_args_str = match.group(2)
        
        print(f"🔧 AI requested tool: {tool_name}({tool_args_str})")
        
        # Execute tool
        tool_result = execute_local_tool(tool_name, tool_args_str)
        
        # Append tool call and output to conversation
        messages.append({"role": "assistant", "content": response_text})
        messages.append({
            "role": "user",
            "content": f"[TOOL_RESULT: {tool_name} output]\n{tool_result}"
        })
        
        loop_count += 1
        
    fallback = "Error: Tool execution loop limit reached."
    messages.append({"role": "assistant", "content": fallback})
    return fallback, messages

# Streaming AI calls for ReAct and responses
def call_ai_api_stream(messages):
    provider = config.get("provider")
    model = config.get("model")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    if not provider:
        yield "Error: AI Provider is not configured."
        return

    try:
        # 1. Google Gemini API Stream
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}"
            gemini_messages = []
            for msg in messages:
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            payload = {"contents": gemini_messages}
            res = requests.post(url, json=payload, stream=True, timeout=60)
            
            for line in res.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("["):
                        line_str = line_str[1:]
                    if line_str.endswith("]"):
                        line_str = line_str[:-1]
                    if line_str.startswith(","):
                        line_str = line_str[1:]
                    try:
                        data = json.loads(line_str)
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        yield text
                    except Exception:
                        pass

        # 2. Anthropic API Stream
        elif provider == "anthropic":
            url = f"{base_url}/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            system_prompt = ""
            filtered_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_prompt = m["content"]
                else:
                    role = "assistant" if m["role"] == "assistant" else "user"
                    filtered_messages.append({"role": role, "content": m["content"]})
            
            payload = {
                "model": model,
                "messages": filtered_messages,
                "max_tokens": 4096,
                "stream": True
            }
            if system_prompt:
                payload["system"] = system_prompt
                
            res = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
            for line in res.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        data_json = line_str[6:]
                        try:
                            data = json.loads(data_json)
                            if data.get("type") == "content_block_delta":
                                yield data["delta"].get("text", "")
                        except Exception:
                            pass

        # 3. OpenAI and compatible APIs Stream
        else:
            if provider == "ollama":
                url = f"{base_url}/v1/chat/completions"
            else:
                url = f"{base_url}/chat/completions"
                
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            res = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
            for line in res.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        data_json = line_str[6:]
                        if data_json == "[DONE]":
                            break
                        try:
                            data = json.loads(data_json)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except Exception:
                            pass

    except Exception as e:
        yield f"Stream Request Error: {str(e)}"

def get_ai_response_stream(messages):
    system_present = False
    for msg in messages:
        if msg["role"] == "system":
            system_present = True
            break
            
    if not system_present:
        messages.insert(0, {
            "role": "system",
            "content": get_system_prompt()
        })
        
    loop_count = 0
    max_loops = 5
    
    while loop_count < max_loops:
        stream = call_ai_api_stream(messages)
        
        buffer = ""
        is_tool_call = None
        accumulated_response = ""
        
        for chunk in stream:
            accumulated_response += chunk
            buffer += chunk
            
            if is_tool_call is None:
                if len(buffer) >= 11:
                    if buffer.startswith("[TOOL_CALL:"):
                        is_tool_call = True
                    else:
                        is_tool_call = False
                        yield buffer
                        buffer = ""
            else:
                if not is_tool_call:
                    yield chunk
                    
        if is_tool_call is False or is_tool_call is None:
            messages.append({"role": "assistant", "content": accumulated_response})
            yield f"\n[HISTORY_SYNC]:{json.dumps(messages)}"
            return
            
        match = re.search(r'\[TOOL_CALL:\s*(\w+)\((.*)\)\s*\]', accumulated_response)
        if not match:
            messages.append({"role": "assistant", "content": accumulated_response})
            yield accumulated_response
            yield f"\n[HISTORY_SYNC]:{json.dumps(messages)}"
            return
            
        tool_name = match.group(1)
        tool_args_str = match.group(2)
        
        yield accumulated_response
        
        tool_result = execute_local_tool(tool_name, tool_args_str)
        
        tool_result_msg = f"\n[TOOL_RESULT: {tool_name} output]\n{tool_result}"
        yield tool_result_msg
        
        messages.append({"role": "assistant", "content": accumulated_response})
        messages.append({
            "role": "user",
            "content": f"[TOOL_RESULT: {tool_name} output]\n{tool_result}"
        })
        
        loop_count += 1
        
    fallback = "Error: Tool execution loop limit reached."
    yield fallback
    messages.append({"role": "assistant", "content": fallback})
    yield f"\n[HISTORY_SYNC]:{json.dumps(messages)}"

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
            if provider == "ollama":
                url = f"{base_url}/v1/chat/completions"
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

                # Get AI answer (handles ReAct tool calls internally)
                ai_response, updated_history = get_ai_response_with_tools(sessions[chat_id])
                sessions[chat_id] = updated_history
                
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
        
    def generate():
        for chunk in get_ai_response_stream(messages):
            yield chunk

    return Response(generate(), mimetype='text/event-stream')

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
    import logging
    import flask.cli
    # Suppress Flask default serving banner and Werkzeug log requests
    flask.cli.show_server_banner = lambda *args, **kwargs: None
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # 1. Load config
    if not load_config():
        print("⚠️ Warning: config.json not found! Please run the Setup Wizard first.")
        print("Starting anyway in fallback mode...")

    # 2. Launch Telegram Bot if enabled
    telegram_status = "Disabled"
    if config.get("telegram_enabled") and config.get("telegram_token"):
        tg_token = config["telegram_token"]
        telegram_bot_thread = threading.Thread(target=telegram_bot_loop, args=(tg_token,), daemon=True)
        telegram_bot_thread.start()
        telegram_status = "Active"

    # 3. Print access information
    local_ip = get_local_ip()
    green_color = "\033[38;5;46m"
    white_color = "\033[38;5;255m"
    reset_color = "\033[0m"
    banner_text = f"""{green_color}██████╗ ██╗  ██╗███████╗████████╗    █████╗ ██╗
██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝   ██╔══██╗██║
{white_color}██████╔╝█████╔╝ ███████╗   ██║      ███████║██║
██╔═══╝ ██╔═██╗ ╚════██║   ██║      ██╔══██║██║
██║     ██║  ██╗███████║   ██║      ██║  ██║██║
╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝      ╚═╝  ╚═╝╚═╝{reset_color}"""
    print(banner_text)
    print(f"{green_color}───────────────────────── Server is Starting ─────────────────────────{reset_color}")
    print(f"  Local URL:     {white_color}http://127.0.0.1:5000{reset_color}")
    print(f"  Network URL:   {white_color}http://{local_ip}:5000{reset_color}")
    print(f"  AI Provider:   {white_color}{config.get('provider_name', 'None')}{reset_color}")
    print(f"  Model:         {white_color}{config.get('model', 'None')}{reset_color}")
    print(f"  Telegram Bot:  {white_color}{telegram_status}{reset_color}")
    print(f"{green_color}──────────────────────────────────────────────────────────────────────{reset_color}\n")

    # Run Flask
    # Host is 0.0.0.0 so they can access it from their phone browser as well as external devices on local network
    app.run(host='0.0.0.0', port=5000, debug=False)
