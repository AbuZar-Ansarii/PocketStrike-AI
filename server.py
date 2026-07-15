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

# Get Termux Package Name/Application ID
def get_termux_package_id():
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    match = re.search(r'/data/data/([^/]+)', prefix)
    return match.group(1) if match else "com.termux"

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

    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (Day: %A)")

    return f"""You are PocketStrike AI, a powerful local security and system assistant running in Termux on the user's Android phone.
Current local time and date: {current_time}
You are a self-evolving AI agent: you can grow, learn, and expand your capabilities over time by writing scripts, learning new rules, and persisting your memory.

Your workspace directory is: {WORKSPACE_DIR} (which is located in the phone's internal storage).
All file tools (list_directory, read_file_content, write_file_content, run_python_script) resolve relative paths inside this workspace directory. Always write/save files requested by the user inside this workspace folder.
Critical: You are forbidden from modifying, writing, or deleting files outside this workspace directory, especially the server's own scripts (server.py, setup.py, launch.sh, etc.) to prevent messing with your own running code.

AI PERSISTENT MEMORY (Stored locally and privately on user's device):
You are a privacy-focused, self-evolving AI. You must actively maintain a deep understanding of the user.
Whenever the user shares their name, preferences, goals, habits, working style, or local system parameters, you MUST immediately call write_file_content to save these facts in 'memory.json'. This forms your long-term memory and is re-injected on every single turn.
Current Memory:
{memory_content}

AI SELF-EVOLUTION INSTRUCTIONS (Stored locally and privately on user's device):
Use write_file_content to update 'instructions.txt' to add new behavioral rules, customized script styles, or operational guidelines for yourself as you grow with the user.
Current Instructions:
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
7. execute_termux_command(command)
   Runs a shell command inside Termux (e.g. 'whoami', 'uname -a', 'ping', 'curl', 'nmap', etc.) and returns the standard output.
   Note: This operates inside a persistent stateful background shell session. Directory changes ('cd') and environment variables carry over to subsequent commands.
8. web_search(query)
   Scrapes DuckDuckGo HTML for live search results. Use this to lookup CVEs or current information.
9. fetch_url(url)
   Downloads clean text from any website (strips HTML layout) so you can read articles or documentation.
10. get_network_details()
    Returns network details including active interfaces, SSID, local subnet mask, and routing info.
11. list_local_listeners()
    Lists active listening ports on the local Termux host (like a netstat scan).
12. send_android_notification(title, message)
    Sends a system notification banner to the user's Android phone screen.
13. vibrate_device(duration_ms)
    Vibrates the phone for the specified duration (default: 500ms).
14. search_files(pattern)
    Searches for files recursively inside your workspace using glob patterns (e.g. "*.py").
15. local_network_scan()
    Scans the local subnet for active connected devices (fast ARP and ICMP ping sweep). Use this when the user asks to scan the network.
16. audit_android_security()
    Audits the Android device's firmware release version, developer options (USB debugging), root signature binary trails, and outdated packages.
17. subnet_port_sweep(port_number)
    Performs a high-speed parallel sweep checking which hosts on the local network subnet have a specific port open (e.g., check for SSH port 22 or HTTP port 80).
18. take_camera_photo(camera_id="0")
    Captures a photo using the phone's front ("1") or back ("0") camera and saves it to the workspace.
19. get_phone_location()
    Retrieves GPS coordinates of the phone (latitude, longitude, altitude, accuracy).
20. make_phone_call(phone_number)
    Places an outgoing phone call to the specified number.
21. send_sms(phone_number, message)
    Sends an SMS text message to the specified phone number.
22. set_brightness(level)
    Adjusts screen brightness level (0 to 255).
23. set_volume(stream, level)
    Adjusts stream volume levels. stream can be 'music', 'ring', 'alarm', 'notification', or 'system'.
24. take_screenshot()
    Captures the current active screen of the phone (runs via local ADB or Shizuku shell).
25. tap_screen(x, y)
    Simulates a screen touch/tap event at coordinates (x, y) (runs via local ADB or Shizuku shell).
26. swipe_screen(x1, y1, x2, y2, duration_ms)
    Simulates a screen swipe gesture from (x1, y1) to (x2, y2) over the specified duration (runs via local ADB or Shizuku shell).
27. press_key(key_code)
    Simulates a hardware key event (e.g. 3=Home, 4=Back, 26=Power, 82=Menu/Unlock) (runs via local ADB or Shizuku shell).
28. launch_app(package_name)
    Opens an application by its package name (e.g. 'com.whatsapp', 'com.android.chrome') (runs via local ADB or Shizuku shell).
29. control_android_system(action, target="")
    Executes system utility commands on the device. Supported action tokens: 'flashlight_on', 'flashlight_off', 'wifi_on', 'wifi_off', 'bluetooth_on', 'bluetooth_off', 'dark_mode_on', 'dark_mode_off', 'battery_saver_on', 'battery_saver_off', 'dnd_on', 'dnd_off', 'auto_rotate_on', 'auto_rotate_off', 'expand_notifications', 'collapse_notifications', 'get_current_app', 'type_text'. target is used for 'type_text' (specify string to type).
30. get_clipboard()
    Returns the current text contents of the Android system clipboard.
31. set_clipboard(text)
    Overwrites the Android system clipboard with the specified text.
32. list_installed_apps(user_only=True)
    Lists all installed app package names and their APK paths. Defaults to listing third-party user-installed apps (specify user_only=False to list system apps as well).
33. scan_wifi_networks()
    Scans nearby Wi-Fi hotspots and returns network details (SSID, BSSID, RSSI, channel, security mode).
34. speak_text(text)
    Uses the Android Text-To-Speech engine to read the specified text aloud.
35. dns_lookup(domain, record_type="A")
    Queries DNS records (A, AAAA, MX, TXT, CNAME, NS) for a target domain using Cloudflare DNS-over-HTTPS.
36. whois_lookup(domain)
    Queries domain registration and registrar details using public RDAP APIs.
37. analyze_hash(hash_str)
    Analyzes a cryptographic hash string to determine its likely algorithm (e.g. MD5, SHA-1, SHA-256, bcrypt).
38. open_url_on_phone(url)
    Opens a URL/Google search in the default browser on the Android phone screen (runs via local ADB or Shizuku shell). Use this when the user asks to open Google, search for something on their phone screen, or view a website.
39. execute_root_command(command)
    Executes a shell command as SuperUser/Root (using 'su -c') inside Termux and returns the standard output. Only use this if the device has active root privileges, and when standard execute_termux_command is insufficient (e.g., to read protected app files, inspect low-level system attributes, or modify restricted network properties).
40. audit_sms_inbox(limit=10)
    Lists recent SMS messages from the inbox. Use this to audit for spam, phishing links, or suspicious text messages. (runs via local Termux-API).
41. ip_geolocation_lookup(ip_address)
    Performs a geographic lookup of an external IP address, resolving its country, region, city, ISP, and geographic coordinates. Use this to trace the origin of network connections or audit remote IPs.
42. read_phone_sensors(sensor_name="")
    Reads real-time data from phone hardware sensors. If sensor_name is omitted, lists all available sensors. If sensor_name is specified (e.g., 'Gravity', 'Light'), reads the sensor's current data values once. (runs via local Termux-API).
43. dump_ui_layout()
    Dumps the current screen's XML UI layout, parses it, and returns a clean, token-efficient list of all visible text elements, buttons, and input fields, along with their screen center coordinates. Use this to locate buttons or inputs on screen when automating app usage. (runs via local ADB or Shizuku shell).
44. add_scheduled_task(task_type, trigger, description, target="telegram")
    Schedules a reminder or a recurring task. task_type is either 'reminder' (one-shot alert) or 'cron' (recurring task). trigger is an offset ('10m', '2h', '1d', or specific time '18:30') for reminders, or an interval ('5m', '1h', '1d') for crons. description is the message or task content. target is 'telegram', 'system', or 'both'. (runs via local background thread).
45. list_scheduled_tasks()
    Lists all active, pending, or recurring tasks/crons.
46. remove_scheduled_task(task_id)
    Removes a scheduled task/cron by its unique ID.
47. detect_arp_spoofing()
    Scans the local ARP cache to check if multiple IP addresses point to the same MAC address. Use this to audit for active Wi-Fi MITM/ARP spoofing interception attacks. (runs via local Linux file).
48. audit_vpn_connection()
    Checks the current public IP, ISP provider, and verifies if the connection is currently protected or leaking metadata through a VPN, proxy, or Tor exit node. (queries ip-api.com).
49. audit_website_security(url)
    Inspects a web domain or local server URL for SSL/TLS certificate validity (expiration date, issuer) and evaluates the presence of critical security headers (HSTS, CSP, X-Frame-Options, XSS protection).

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
    # Curated list of the top 100 most common network service ports
    TOP_100_PORTS = [
        21, 22, 23, 25, 53, 67, 68, 69, 80, 110, 111, 119, 123, 135, 137, 138, 139, 143, 161, 162,
        179, 389, 443, 445, 465, 500, 514, 515, 548, 554, 587, 631, 636, 873, 990, 993, 995, 1025,
        1080, 1433, 1434, 1521, 1723, 1812, 1813, 2049, 3000, 3128, 3268, 3306, 3389, 4443, 4500,
        5000, 5060, 5061, 5432, 5631, 5632, 5900, 5984, 6000, 6379, 7077, 8000, 8080, 8081, 8443,
        8888, 9000, 9092, 9100, 9200, 9418, 9999, 11211, 27017, 27018, 27019, 50030, 50070
    ]

    # Parse ports_list intelligently
    if isinstance(ports_list, int):
        ports_list = TOP_100_PORTS[:min(ports_list, 100)]
    elif isinstance(ports_list, str) and ports_list.strip().isdigit():
        ports_list = TOP_100_PORTS[:min(int(ports_list.strip()), 100)]
    elif not ports_list:
        ports_list = TOP_100_PORTS[:30] # Default to top 30 ports
    elif isinstance(ports_list, str):
        try:
            ports_list = json.loads(ports_list)
        except Exception:
            try:
                ports_list = [int(p.strip()) for p in ports_list.strip("[]").split(",") if p.strip()]
            except Exception:
                ports_list = TOP_100_PORTS[:30]
                
    # Parse target target hostname to IP
    try:
        resolved_ip = socket.gethostbyname(target_ip)
    except Exception:
        resolved_ip = target_ip
        
    open_ports = []
    # Convert all items to integers and filter to top 100 limits
    ports_list = [int(p) for p in ports_list][:100]
    
    import concurrent.futures
    
    def check_port(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            result = s.connect_ex((resolved_ip, port))
            s.close()
            if result == 0:
                return port
        except Exception:
            pass
        return None
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        scanned_results = executor.map(check_port, ports_list)
        
    for p in scanned_results:
        if p is not None:
            open_ports.append(p)
            
    open_ports.sort()
    
    # Simple banner lookup for common ports
    banner_details = {}
    for p in open_ports:
        if p == 22: banner_details["22"] = "SSH"
        elif p == 80: banner_details["80"] = "HTTP Web Server"
        elif p == 443: banner_details["443"] = "HTTPS Secure Web Server"
        elif p == 21: banner_details["21"] = "FTP"
        elif p == 3306: banner_details["3306"] = "MySQL Database"
        elif p == 8080: banner_details["8080"] = "HTTP Alternate Web Server"
        elif p == 5000: banner_details["5000"] = "Flask/PocketStrike AI Server"
        else: banner_details[str(p)] = "Unknown Service"
        
    results = {
        "target": target_ip,
        "resolved_ip": resolved_ip,
        "scanned_ports": len(ports_list),
        "open_ports": open_ports,
        "discovered_services": banner_details
    }
    return json.dumps(results, indent=2)

def local_network_scan():
    try:
        import subprocess
        import concurrent.futures
        
        # 1. Identify local subnet by checking routing rules or IP address
        res = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5)
        routes = res.stdout if res.returncode == 0 else ""
        
        subnet = None
        for line in routes.split("\n"):
            if "proto kernel" in line and "scope link" in line and "/" in line:
                parts = line.strip().split()
                for p in parts:
                    if "/" in p and p[0].isdigit():
                        subnet = p
                        break
            if subnet:
                break
                
        if not subnet:
            addr_res = subprocess.run(["ip", "addr"], capture_output=True, text=True, timeout=5)
            addr_out = addr_res.stdout if addr_res.returncode == 0 else ""
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)\s+[^>]*wlan0', addr_out)
            if match:
                ip = match.group(1)
                mask = match.group(2)
                ip_parts = ip.split(".")
                subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/{mask}"
                
        if not subnet:
            subnet = "192.168.1.0/24"
            
        base_ip = ".".join(subnet.split("/")[0].split(".")[:-1])
        
        # Found hosts dict to store details (IP -> hostname)
        found_hosts = {}
        
        # 2. Fast ping sweep on the entire Class C range (1-254) in parallel
        def check_host(ip):
            try:
                # Fast timeout of 0.8s
                ping_res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, timeout=1.2)
                if ping_res.returncode == 0:
                    # Attempt quick reverse hostname lookup
                    try:
                        name_info = socket.gethostbyaddr(ip)
                        hostname = name_info[0]
                    except Exception:
                        hostname = "Unknown Host"
                    return ip, hostname
            except Exception:
                pass
            return None
            
        # Scan full subnet range (1-254)
        ips_to_scan = [f"{base_ip}.{i}" for i in range(1, 255)]
        
        # Speed up with 80 parallel threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
            scanned_results = executor.map(check_host, ips_to_scan)
            
        for r in scanned_results:
            if r:
                ip, hostname = r
                found_hosts[ip] = hostname
                
        # 3. Read ARP cache to catch silent devices
        try:
            with open("/proc/net/arp", "r") as f:
                arp_lines = f.readlines()
                for line in arp_lines[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00" and ip.startswith(base_ip) and ip not in found_hosts:
                            try:
                                name_info = socket.gethostbyaddr(ip)
                                hostname = name_info[0]
                            except Exception:
                                hostname = "Unknown Host"
                            found_hosts[ip] = hostname
        except Exception:
            pass
            
        # Format list output
        hosts_output = []
        for ip in sorted(found_hosts.keys(), key=lambda x: int(x.split(".")[-1])):
            hosts_output.append({
                "ip": ip,
                "hostname": found_hosts[ip]
            })
            
        scan_details = {
            "scanned_subnet": subnet,
            "active_hosts_found": len(hosts_output),
            "devices": hosts_output
        }
        return json.dumps(scan_details, indent=2)
    except Exception as e:
        return f"Error scanning local network subnet: {str(e)}"


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

    except Exception as e:
        return f"Error running script: {str(e)}"

# =======================================================
# STATEFUL BACKGROUND SHELL SESSION CONTROLLER
# =======================================================
class StatefulShell:
    def __init__(self):
        self.process = None
        self.stdout_queue = None
        self.stderr_queue = None
        self.current_directory = WORKSPACE_DIR
        self.init_shell()

    def init_shell(self):
        try:
            import subprocess
            import queue
            import threading
            
            # Start background shell process
            shell_executable = "bash" if shutil.which("bash") else "sh"
            self.process = subprocess.Popen(
                [shell_executable],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.current_directory
            )
            
            self.stdout_queue = queue.Queue()
            self.stderr_queue = queue.Queue()
            
            # Start background non-blocking output reader threads
            def read_output(stream, q):
                for line in iter(stream.readline, ''):
                    q.put(line)
                stream.close()
                
            self.stdout_thread = threading.Thread(target=read_output, args=(self.process.stdout, self.stdout_queue))
            self.stderr_thread = threading.Thread(target=read_output, args=(self.process.stderr, self.stderr_queue))
            
            self.stdout_thread.daemon = True
            self.stderr_thread.daemon = True
            
            self.stdout_thread.start()
            self.stderr_thread.start()
        except Exception as e:
            print(f"Failed to initialize stateful shell: {str(e)}")

    def execute(self, cmd_str, timeout=30):
        # Safety token validation
        forbidden_tokens = ["rm -rf", "rm -f /", "mkfs", "dd if="]
        for token in forbidden_tokens:
            if token in cmd_str:
                return f"Error: Command execution blocked. Forbidden token: '{token}'"
                
        if not self.process or self.process.poll() is not None:
            # Restart shell if it crashed or terminated
            self.init_shell()
            
        import time
        import queue
        
        # Clear out any residual queue data
        while not self.stdout_queue.empty():
            try: self.stdout_queue.get_nowait()
            except queue.Empty: break
        while not self.stderr_queue.empty():
            try: self.stderr_queue.get_nowait()
            except queue.Empty: break
            
        # Append sentinel marker to detect command completion
        sentinel = f"__PKST_CMD_DONE_{int(time.time())}__"
        full_command = f"{cmd_str}\npwd\necho '{sentinel}'\necho '{sentinel}' >&2\n"
        
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
        except Exception as e:
            self.init_shell()
            return f"Error: Failed to write to shell input. Shell restarted. Details: {str(e)}"
            
        stdout_buf = []
        stderr_buf = []
        start_time = time.time()
        
        # Poll stdout and stderr until sentinel marker is encountered or timeout expires
        while time.time() - start_time < timeout:
            # Read stdout
            while True:
                try:
                    line = self.stdout_queue.get_nowait()
                    if sentinel in line:
                        break
                    stdout_buf.append(line)
                except queue.Empty:
                    break
                    
            # Read stderr
            while True:
                try:
                    line = self.stderr_queue.get_nowait()
                    if sentinel in line:
                        break
                    stderr_buf.append(line)
                except queue.Empty:
                    break
                    
            # Break if sentinel marks command completion
            if (stdout_buf and sentinel in stdout_buf[-1]) or (any(sentinel in l for l in stdout_buf)):
                break
                
            time.sleep(0.05)
            
        # Strip sentinel from logs
        stdout_clean = [l for l in stdout_buf if sentinel not in l]
        stderr_clean = [l for l in stderr_buf if sentinel not in l]
        
        # Update working directory tracking
        if stdout_clean:
            # The last clean line printed is our 'pwd' output from the sentinel call
            potential_pwd = stdout_clean[-1].strip()
            if os.path.exists(potential_pwd):
                self.current_directory = potential_pwd
                stdout_clean = stdout_clean[:-1] # Remove pwd line from user stdout logs
                
        output = ""
        if stdout_clean:
            output += "".join(stdout_clean)
        if stderr_clean:
            output += "Stderr:\n" + "".join(stderr_clean)
            
        if not output.strip():
            # If timed out
            if time.time() - start_time >= timeout:
                return "Command execution completed (or timed out after 30 seconds)."
            return "Command executed successfully (no output)."
            
        return output

# Initialize single global stateful shell instance
GLOBAL_SHELL = StatefulShell()

def execute_termux_command(command):
    # Route command execution dynamically to our persistent stateful shell
    return GLOBAL_SHELL.execute(command)

def audit_android_security():
    audit = {}
    try:
        import subprocess
        # 1. Check Android OS parameters via getprop interface
        release_res = subprocess.run(["getprop", "ro.build.version.release"], capture_output=True, text=True, timeout=3)
        patch_res = subprocess.run(["getprop", "ro.build.version.security_patch"], capture_output=True, text=True, timeout=3)
        sdk_res = subprocess.run(["getprop", "ro.build.version.sdk"], capture_output=True, text=True, timeout=3)
        brand_res = subprocess.run(["getprop", "ro.product.brand"], capture_output=True, text=True, timeout=3)
        model_res = subprocess.run(["getprop", "ro.product.model"], capture_output=True, text=True, timeout=3)
        
        audit["android_version"] = release_res.stdout.strip() if release_res.returncode == 0 else "Unknown"
        audit["security_patch"] = patch_res.stdout.strip() if patch_res.returncode == 0 else "Unknown"
        audit["sdk_api_level"] = sdk_res.stdout.strip() if sdk_res.returncode == 0 else "Unknown"
        audit["device_brand"] = brand_res.stdout.strip() if brand_res.returncode == 0 else "Unknown"
        audit["device_model"] = model_res.stdout.strip() if model_res.returncode == 0 else "Unknown"
    except Exception as e:
        audit["properties_error"] = str(e)
        
    # 2. Check for SuperUser/Root trail binary signatures
    root_signatures = ["/system/bin/su", "/system/xbin/su", "/sbin/su", "/system/sd/xbin/su", "/system/bin/failsafe/su", "/data/local/xbin/su", "/data/local/bin/su"]
    su_found = False
    for path in root_signatures:
        if os.path.exists(path):
            su_found = True
            break
            
    if not su_found:
        # Check command path trail
        su_found = shutil.which("su") is not None
        
    audit["superuser_root_access"] = "Active/Rooted" if su_found else "Not Rooted / Standard User"
    
    # 3. Audit Termux installations security dependencies (outdated pkg check)
    try:
        import subprocess
        # Check if packages can be updated or list them
        upgradable_res = subprocess.run(["pkg", "list-upgradable"], capture_output=True, text=True, timeout=10)
        if upgradable_res.returncode == 0:
            lines = [l.strip() for l in upgradable_res.stdout.split("\n") if l.strip()]
            audit["upgradable_packages_count"] = len(lines)
            audit["upgradable_packages_list"] = lines[:15] # Return top 15 upgradable packages
        else:
            audit["upgradable_packages_count"] = "Unknown"
    except Exception:
        pass
        
    # 4. Check USB Debugging Developer Options state
    try:
        adb_res = subprocess.run(["getprop", "init.svc.adbd"], capture_output=True, text=True, timeout=3)
        audit["adb_debugging_status"] = "Active/Enabled" if "running" in adb_res.stdout else "Disabled"
    except Exception:
        pass
        
    # 5. Extract security evaluation recommendation
    evaluation = []
    if su_found:
        evaluation.append("WARNING: SuperUser root access detected. Ensure you have custom firewalls or verified root binaries installed to prevent malicious permission escalations.")
    if audit.get("security_patch") != "Unknown":
        # Check patch age
        try:
            from datetime import datetime
            patch_date = datetime.strptime(audit["security_patch"], "%Y-%m-%d")
            diff = (datetime.now() - patch_date).days
            if diff > 180: # Outdated by more than 6 months
                evaluation.append(f"WARNING: Android security patch is {diff} days outdated (Last updated: {audit['security_patch']}). The device is susceptible to older CVE exploits.")
        except Exception:
            pass
            
    if audit.get("upgradable_packages_count") != "Unknown" and isinstance(audit.get("upgradable_packages_count"), int) and audit["upgradable_packages_count"] > 10:
        evaluation.append(f"TIP: Termux has {audit['upgradable_packages_count']} packages outdated. Run 'pkg upgrade' to patch local software dependencies.")
        
    if not evaluation:
        evaluation.append("Device security configuration is optimal. No critical vulnerabilities found in default interface checklist.")
        
    audit["audit_recommendations"] = evaluation
    return json.dumps(audit, indent=2)

def subnet_port_sweep(port_number):
    try:
        import subprocess
        import concurrent.futures
        
        # 1. Resolve subnet range
        res = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5)
        routes = res.stdout if res.returncode == 0 else ""
        
        subnet = None
        for line in routes.split("\n"):
            if "proto kernel" in line and "scope link" in line and "/" in line:
                parts = line.strip().split()
                for p in parts:
                    if "/" in p and p[0].isdigit():
                        subnet = p
                        break
            if subnet:
                break
                
        if not subnet:
            addr_res = subprocess.run(["ip", "addr"], capture_output=True, text=True, timeout=5)
            addr_out = addr_res.stdout if addr_res.returncode == 0 else ""
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)\s+[^>]*wlan0', addr_out)
            if match:
                ip = match.group(1)
                mask = match.group(2)
                ip_parts = ip.split(".")
                subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/{mask}"
                
        if not subnet:
            subnet = "192.168.1.0/24"
            
        base_ip = ".".join(subnet.split("/")[0].split(".")[:-1])
        
        target_port = int(port_number)
        active_listeners = []
        
        # 2. Parallel thread sweep to scan the target port across all subnet hosts (1-254)
        def scan_host_port(ip):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.8) # Keep it extremely fast
                result = s.connect_ex((ip, target_port))
                s.close()
                if result == 0:
                    try:
                        name_info = socket.gethostbyaddr(ip)
                        hostname = name_info[0]
                    except Exception:
                        hostname = "Unknown Host"
                    return {
                        "ip": ip,
                        "hostname": hostname
                    }
            except Exception:
                pass
            return None
            
        ips_to_scan = [f"{base_ip}.{i}" for i in range(1, 255)]
        
        # Sweep with 80 parallel threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
            scanned_results = executor.map(scan_host_port, ips_to_scan)
            
        for r in scanned_results:
            if r:
                active_listeners.append(r)
                
        sweep_details = {
            "scanned_subnet": subnet,
            "target_port": target_port,
            "hosts_found_listening": len(active_listeners),
            "devices": active_listeners
        }
        return json.dumps(sweep_details, indent=2)
    except Exception as e:
        return f"Error performing subnet port sweep: {str(e)}"

# =======================================================
# PHONE HARDWARE & SYSTEM CONTROL TOOLS (TERMUX:API)
# =======================================================
def take_camera_photo(camera_id="0"):
    try:
        import subprocess
        # camera_id: "0" = back, "1" = front
        target_name = "captured_photo.jpg"
        target_path = os.path.join(WORKSPACE_DIR, target_name)
        
        # Cleanup old photo
        if os.path.exists(target_path):
            os.remove(target_path)
            
        cmd = ["termux-camera-photo", "-c", str(camera_id), target_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if res.returncode == 0 and os.path.exists(target_path):
            return f"Success: Photo captured. Saved to workspace as '{target_name}'. Path: {target_path}."
        return f"Error taking photo: {res.stderr} (Ensure Termux:API app is installed and camera permission is granted)"
    except Exception as e:
        return f"Error executing camera photo tool: {str(e)}"

def get_phone_location():
    try:
        import subprocess
        res = subprocess.run(["termux-location"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return res.stdout
        return f"Error getting location: {res.stderr} (Ensure GPS location permissions are granted)"
    except Exception as e:
        return f"Error executing location tool: {str(e)}"

def make_phone_call(phone_number):
    try:
        import subprocess
        cmd = ["termux-telephony-call", str(phone_number)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Success: Initiated phone call to {phone_number}."
        return f"Error making call: {res.stderr}"
    except Exception as e:
        return f"Error executing phone call tool: {str(e)}"

def send_sms(phone_number, message):
    try:
        import subprocess
        cmd = ["termux-sms-send", "-n", str(phone_number), message]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            return f"Success: SMS sent to {phone_number}."
        return f"Error sending SMS: {res.stderr}"
    except Exception as e:
        return f"Error executing SMS tool: {str(e)}"

def set_brightness(level):
    try:
        import subprocess
        # level: 0 to 255
        level_val = max(0, min(int(level), 255))
        cmd = ["termux-brightness", str(level_val)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Success: Screen brightness set to {level_val}."
        return f"Error setting brightness: {res.stderr}"
    except Exception as e:
        return f"Error executing brightness tool: {str(e)}"

def set_volume(stream, level):
    try:
        import subprocess
        # stream: music, ring, alarm, notification, system
        # level: varies by stream, usually 0 to 15
        cmd = ["termux-volume", str(stream), str(level)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Success: Volume for stream '{stream}' set to {level}."
        return f"Error setting volume: {res.stderr}"
    except Exception as e:
        return f"Error executing volume tool: {str(e)}"

def get_clipboard():
    try:
        import subprocess
        res = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error getting clipboard: {res.stderr}"
    except Exception as e:
        return f"Error executing clipboard get: {str(e)} (Ensure Termux:API is installed)"

def set_clipboard(text):
    try:
        import subprocess
        res = subprocess.run(["termux-clipboard-set", text], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return "Success: Clipboard updated."
        return f"Error setting clipboard: {res.stderr}"
    except Exception as e:
        return f"Error executing clipboard set: {str(e)} (Ensure Termux:API is installed)"

def list_installed_apps(user_only=True):
    try:
        import subprocess
        # -f lists package file locations, -3 lists only third-party (user-installed) apps
        cmd = ["pm", "list", "packages", "-f"]
        if user_only:
            cmd.append("-3")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if res.returncode != 0:
            return f"Error listing packages: {res.stderr}"
        
        packages = []
        for line in res.stdout.strip().split("\n"):
            if line.startswith("package:"):
                # line format: package:/data/app/~~.../base.apk=com.example.app
                parts = line[8:].split("=")
                if len(parts) >= 2:
                    apk_path = parts[0]
                    package_name = "=".join(parts[1:])
                    packages.append({
                        "package": package_name,
                        "apk_path": apk_path
                    })
        return json.dumps(packages, indent=2)
    except Exception as e:
        return f"Error executing app audit: {str(e)}"

def scan_wifi_networks():
    try:
        import subprocess
        res = subprocess.run(["termux-wifi-scaninfo"], capture_output=True, text=True, timeout=12)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error scanning Wi-Fi: {res.stderr} (Ensure GPS location service is enabled and location permission is granted to Termux)"
    except Exception as e:
        return f"Error executing wifi scan: {str(e)} (Ensure Termux:API is installed)"

def speak_text(text):
    try:
        import subprocess
        res = subprocess.run(["termux-tts-speak", text], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            return "Success: Speaking text."
        return f"Error triggering speech: {res.stderr}"
    except Exception as e:
        return f"Error executing speak tool: {str(e)} (Ensure Termux:API is installed)"

# =======================================================
# LOCAL ADB AUTOMATION CONTROLLER (SCREEN CONTROL)
# =======================================================
def run_adb_command(cmd_str):
    try:
        import subprocess
        import shutil
        import os
        import glob
        import shlex
        
        # Check if rish (Shizuku's Termux shell interface) is installed and available
        rish_path = shutil.which("rish")
        
        # Auto-install Shizuku client files if found in the user's exported /sdcard/Shizuku/ directory
        if rish_path is None:
            possible_srcs = [
                "/sdcard/Shizuku/rish",
                "/storage/emulated/0/Shizuku/rish",
                os.path.expanduser("~/storage/shared/Shizuku/rish"),
                os.path.expanduser("~/storage/downloads/rish"),
                os.path.expanduser("~/storage/downloads/Shizuku/rish"),
                "/sdcard/Download/rish",
                "/sdcard/Download/Shizuku/rish",
                "/storage/emulated/0/Download/rish",
                "/storage/emulated/0/Download/Shizuku/rish",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "rish")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace", "rish"))
            ]
            
            shizuku_src = None
            for path in possible_srcs:
                if os.path.exists(path):
                    shizuku_src = path
                    break
                
            if shizuku_src:
                try:
                    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
                    termux_bin = os.path.join(prefix, "bin")
                    if os.path.exists(termux_bin):
                        # Copy all files matching rish* (including dex loader)
                        src_dir = os.path.dirname(shizuku_src)
                        for fpath in glob.glob(os.path.join(src_dir, "rish*")):
                            dest_file = os.path.join(termux_bin, os.path.basename(fpath))
                            shutil.copy(fpath, dest_file)
                            
                        # Grant execution permissions
                        os.chmod(os.path.join(termux_bin, "rish"), 0o755)
                        
                        # dex loader MUST be read-only (chmod 444) for Shizuku security
                        dex_file = os.path.join(termux_bin, "rish_shizuku.dex")
                        if os.path.exists(dex_file):
                            os.chmod(dex_file, 0o444)
                            
                        rish_path = os.path.join(termux_bin, "rish")
                        print(f"PocketstrikeAI: Auto-installed Shizuku rish binaries successfully to {termux_bin}!")
                except Exception as e:
                    print(f"PocketstrikeAI: Shizuku auto-install failed: {e}")
                    
        use_shizuku = rish_path is not None
        shizuku_err = None
        adb_err = None

        env = os.environ.copy()
        env["RISH_APPLICATION_ID"] = get_termux_package_id()
        env.pop("LD_LIBRARY_PATH", None)
        env.pop("LD_PRELOAD", None)
        shell_exe = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "sh"

        # --- 1. TRY SHIZUKU FIRST IF AVAILABLE ---
        if use_shizuku:
            try:
                if cmd_str.startswith("shell "):
                    shell_cmd = cmd_str[6:] # Strip "shell "
                    
                    if shell_cmd == "screencap -p":
                        return True, "STDOUT_STREAMING_ACTIVE"
                        
                    res = subprocess.run([shell_exe, rish_path, "-c", shell_cmd], capture_output=True, text=True, timeout=15, env=env)
                    if res.returncode == 0:
                        return True, res.stdout
                    else:
                        shizuku_err = f"Shizuku shell cmd failed (code {res.returncode}): {res.stderr.strip() or res.stdout.strip()}"
                
                elif cmd_str.startswith("devices"):
                    # Check if Shizuku daemon is running and responds
                    res = subprocess.run([shell_exe, rish_path, "-c", "echo 1"], capture_output=True, text=True, timeout=3, env=env)
                    if res.returncode == 0:
                        return True, "List of devices attached\nshizuku_localhost\tdevice"
                    else:
                        shizuku_err = f"Shizuku test failed: {res.stderr.strip() or res.stdout.strip()}"
                
                elif cmd_str.startswith("pull "):
                    parts = shlex.split(cmd_str)
                    if len(parts) >= 3:
                        src = parts[1]
                        dest = parts[2]
                        try:
                            with open(dest, "wb") as f:
                                res = subprocess.run([shell_exe, rish_path, "-c", f"cat {src}"], stdout=f, env=env, timeout=15)
                            if res.returncode == 0:
                                return True, "Pulled via Shizuku shell cat"
                            else:
                                shizuku_err = f"Shizuku cat failed (code {res.returncode})"
                        except Exception as e:
                            shizuku_err = f"Shizuku pull exception: {e}"
                    else:
                        shizuku_err = "Invalid pull command parameters"
            except Exception as e:
                shizuku_err = f"Shizuku exception: {str(e)}"

        # --- 2. TRY ADB FALLBACK IF SHIZUKU FAILED OR NOT AVAILABLE ---
        try:
            if cmd_str.startswith("shell "):
                shell_cmd = cmd_str[6:]
                res = subprocess.run(["adb", "shell", shell_cmd], capture_output=True, text=True, timeout=15)
            elif cmd_str.startswith("pull "):
                parts = shlex.split(cmd_str)
                res = subprocess.run(["adb"] + parts, capture_output=True, text=True, timeout=15)
            else:
                parts = shlex.split(cmd_str)
                res = subprocess.run(["adb"] + parts, capture_output=True, text=True, timeout=15)

            if res.returncode == 0:
                return True, res.stdout
            else:
                adb_err = f"ADB cmd failed (code {res.returncode}): {res.stderr.strip() or res.stdout.strip()}"
        except Exception as e:
            adb_err = f"ADB exception: {str(e)}"

        # --- 3. BOTH FAILED: COMPILE DIAGNOSTIC ERROR MESSAGE ---
        errors = []
        if shizuku_err:
            errors.append(f"[Shizuku] {shizuku_err}")
        if adb_err:
            errors.append(f"[ADB Fallback] {adb_err}")
        
        if not errors:
            errors.append("No execution methods succeeded (Shizuku not configured, ADB not found/connected).")
            
        return False, "\n".join(errors)
    except Exception as e:
        return False, str(e)

def take_screenshot():
    target_name = "captured_screenshot.png"
    target_path = os.path.join(WORKSPACE_DIR, target_name)
    
    if os.path.exists(target_path):
        try: os.remove(target_path)
        except Exception: pass
        
    # Check if Shizuku is set up
    import shutil
    use_shizuku = shutil.which("rish") is not None or os.path.exists("/sdcard/Shizuku/rish") or os.path.exists(os.path.expanduser("~/storage/shared/Shizuku/rish"))
    
    if use_shizuku:
        # Trigger auto-provisioning
        run_adb_command("devices")
        rish_path = shutil.which("rish") or "/data/data/com.termux/files/usr/bin/rish"
        
        env = os.environ.copy()
        env["RISH_APPLICATION_ID"] = get_termux_package_id()
        env.pop("LD_LIBRARY_PATH", None)
        env.pop("LD_PRELOAD", None)
        shell_exe = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "sh"
        
        try:
            with open(target_path, "wb") as f:
                res = subprocess.run([shell_exe, rish_path, "-c", "screencap -p"], stdout=f, env=env, timeout=20)
            if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                return f"Success: Screenshot captured via Shizuku. Saved to workspace as '{target_name}'. Path: {target_path}."
        except Exception as e:
            # Fallback to standard ADB below if rish failed
            pass
            
    # Verify standard ADB connection state fallback
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: Neither Shizuku nor Local ADB is connected. Enable 'Wireless Debugging' in Android Developer Options, connect Termux locally (e.g. run 'adb connect localhost:5555' or authorize Shizuku via rish), and try again."
        
    # 2. Capture screenshot on phone storage
    ok, out = run_adb_command("shell screencap -p /sdcard/screenshot.png")
    if not ok:
        return f"Error: Screen capture command failed. Details: {out}"
        
    # 3. Pull photo from device storage to Termux workspace
    ok, out = run_adb_command(f"pull /sdcard/screenshot.png {target_path}")
    if not ok:
        return f"Error: Failed to transfer screenshot to workspace. Details: {out}"
        
    # Clean up device temp file
    run_adb_command("shell rm /sdcard/screenshot.png")
    
    return f"Success: Screenshot captured. Saved to workspace as '{target_name}'. Path: {target_path}."

def tap_screen(x, y):
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: ADB is not connected. Connect Termux to local Wireless Debugging first."
        
    ok, out = run_adb_command(f"shell input tap {int(x)} {int(y)}")
    if ok:
        return f"Success: Simulated screen tap at coordinates ({int(x)}, {int(y)})."
    return f"Error simulating tap: {out}"

def swipe_screen(x1, y1, x2, y2, duration_ms=500):
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: ADB is not connected. Connect Termux to local Wireless Debugging first."
        
    ok, out = run_adb_command(f"shell input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")
    if ok:
        return f"Success: Simulated screen swipe from ({int(x1)}, {int(y1)}) to ({int(x2)}, {int(y2)}) over {duration_ms}ms."
    return f"Error simulating swipe: {out}"

def press_key(key_code):
    # Key event codes: 3=Home, 4=Back, 26=Power, 24=VolumeUp, 25=VolumeDown, 82=Unlock
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: ADB is not connected. Connect Termux to local Wireless Debugging first."
        
    ok, out = run_adb_command(f"shell input keyevent {int(key_code)}")
    if ok:
        return f"Success: Simulated physical key press event code {int(key_code)}."
    return f"Error simulating key event: {out}"

def launch_app(package_name):
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: ADB is not connected. Connect Termux to local Wireless Debugging first."
        
    ok, out = run_adb_command(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    if ok:
        return f"Success: Opened application matching package name '{package_name}'."
    return f"Error launching application: {out}"

def control_android_system(action, target=""):
    # Controls Android system parameters using local shell commands via Shizuku/ADB
    cmd_map = {
        "flashlight_on": "cmd notification set_flashlight 1",
        "flashlight_off": "cmd notification set_flashlight 0",
        "wifi_on": "svc wifi enable",
        "wifi_off": "svc wifi disable",
        "bluetooth_on": "svc bluetooth enable",
        "bluetooth_off": "svc bluetooth disable",
        "dark_mode_on": "cmd uimode night yes",
        "dark_mode_off": "cmd uimode night no",
        "battery_saver_on": "settings put global low_power 1",
        "battery_saver_off": "settings put global low_power 0",
        "dnd_on": "cmd notification set_dnd on",
        "dnd_off": "cmd notification set_dnd off",
        "auto_rotate_on": "settings put system accelerometer_rotation 1",
        "auto_rotate_off": "settings put system accelerometer_rotation 0",
        "expand_notifications": "cmd statusbar expand-notifications",
        "collapse_notifications": "cmd statusbar collapse",
        "get_current_app": "dumpsys window | grep mCurrentFocus",
        "type_text": f"input text '{target}'"
    }
    
    if action not in cmd_map:
        return f"Error: Unsupported action '{action}'. Options: {', '.join(cmd_map.keys())}"
        
    ok, out = run_adb_command("devices")
    if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
        return "Error: ADB/Shizuku is not connected. Make sure Shizuku or local Wireless Debugging is running."
        
    cmd = cmd_map[action]
    ok, out = run_adb_command(f"shell {cmd}")
    if ok:
        return f"Success: Executed system action '{action}' on device. Output: {out.strip() if out else 'Done'}"
    return f"Error executing system action '{action}': {out}"

def web_search(query):
    try:
        import urllib.parse
        import html as html_parser
        
        # Safe URL encoding using urllib.parse.quote
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return f"Error: Search failed (Status {res.status_code})."
            
        html_content = res.text
        results = []
        
        # Robust regex targeting result titles and snippets regardless of attribute orders
        titles = re.findall(r'<a\s+[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_content, re.DOTALL)
        snippets = re.findall(r'<a\s+[^>]*class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL)
        
        for i in range(min(len(titles), len(snippets), 5)):
            raw_href, title = titles[i]
            
            # Extract clean redirect target URL if present in DuckDuckGo redirect link
            parsed_url = urllib.parse.urlparse(raw_href)
            queries = urllib.parse.parse_qs(parsed_url.query)
            clean_href = queries.get("uddg", [raw_href])[0]
            if clean_href.startswith("//"):
                clean_href = "https:" + clean_href
                
            title_clean = html_parser.unescape(re.sub(r'<[^>]*>', '', title).strip())
            snippet_clean = html_parser.unescape(re.sub(r'<[^>]*>', '', snippets[i]).strip())
            
            results.append({
                "index": i + 1,
                "title": title_clean,
                "link": clean_href,
                "summary": snippet_clean
            })
            
        if not results:
            return "No search results found or search was blocked by rate-limiting."
            
        # Build search results output
        output_parts = ["=== SEARCH ENGINE SUMMARY ==="]
        for r in results:
            output_parts.append(f"[{r['index']}] {r['title']}\nLink: {r['link']}\nSnippet: {r['summary']}")
            
        # Perform Smart Fetching of actual body text for the top 2 web pages
        fetched_count = 0
        output_parts.append("\n=== DEEP WEB CONTENT FETCHED ===")
        for r in results:
            link = r['link']
            # Skip non-crawlable domains and attachments
            if any(domain in link.lower() for domain in ["duckduckgo.com", "google.com", "facebook.com", "twitter.com", "instagram.com"]):
                continue
            if link.lower().endswith((".pdf", ".zip", ".tar", ".gz", ".apk")):
                continue
                
            output_parts.append(f"\n[Deep Content from Link #{r['index']}: {r['title']}]")
            try:
                page_res = requests.get(link, headers=headers, timeout=8)
                if page_res.status_code == 200:
                    page_html = page_res.text
                    # Clean tags
                    page_clean = re.sub(r'<(script|style).*?>([\s\S]*?)</\1>', '', page_html, flags=re.IGNORECASE)
                    text = re.sub(r'<[^>]*>', '', page_clean)
                    text = html_parser.unescape(text)
                    text = re.sub(r'\n\s*\n', '\n\n', text)
                    text = re.sub(r'[ \t]+', ' ', text)
                    
                    body_snippet = text.strip()[:1500]
                    if not body_snippet:
                        body_snippet = "Empty or failed to parse main body text."
                    output_parts.append(body_snippet)
                else:
                    output_parts.append(f"Failed to load full page content (Status {page_res.status_code}).")
            except Exception as e:
                output_parts.append(f"Could not load full page content: {str(e)}")
                
            fetched_count += 1
            if fetched_count >= 2:
                break
                
        return "\n---\n".join(output_parts)
    except Exception as e:
        return f"Error performing search: {str(e)}"

def fetch_url(url):
    try:
        import html as html_parser
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return f"Error: Page fetch failed (Status {res.status_code})."
            
        html_content = res.text
        # Remove script and style tags completely
        html_clean = re.sub(r'<(script|style).*?>([\s\S]*?)</\1>', '', html_content, flags=re.IGNORECASE)
        # Strip all HTML tags
        text = re.sub(r'<[^>]*>', '', html_clean)
        # Convert HTML entities to clean characters
        text = html_parser.unescape(text)
        # Normalize whitespace and empty lines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        cleaned_text = text.strip()[:10000]
        if len(text) > 10000:
            cleaned_text += "\n\n[Content truncated due to size limit...]"
        return cleaned_text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def get_network_details():
    details = {}
    try:
        details["hostname"] = socket.gethostname()
    except Exception:
        pass
        
    try:
        import subprocess
        res = subprocess.run(["ip", "addr"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            details["interfaces"] = res.stdout
        else:
            res_if = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
            if res_if.returncode == 0:
                details["interfaces"] = res_if.stdout
    except Exception as e:
        details["interfaces_error"] = str(e)
        
    try:
        import subprocess
        res = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            details["routing_table"] = res.stdout
    except Exception:
        pass
        
    return json.dumps(details, indent=2)

def list_local_listeners():
    try:
        import subprocess
        res = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
            
        res = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
            
        res = subprocess.run(["netstat", "-an"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = res.stdout.split("\n")
            listeners = [line for line in lines if "LISTEN" in line]
            return "\n".join(listeners) if listeners else "No active listeners found."
    except Exception as e:
        return f"Error retrieving listeners: {str(e)}"

def send_android_notification(title, message):
    try:
        import subprocess
        cmd = ["termux-notification", "-t", title, "-c", message]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return "Success: Notification sent."
        return f"Error: Command exited with code {res.returncode}. Output: {res.stderr}"
    except Exception as e:
        return f"Error triggering notification: {str(e)} (Ensure Termux:API is installed)"

def vibrate_device(duration_ms=500):
    try:
        import subprocess
        cmd = ["termux-vibrate", "-d", str(duration_ms)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Success: Device vibrated for {duration_ms}ms."
        return f"Error: Command exited with code {res.returncode}. Output: {res.stderr}"
    except Exception as e:
        return f"Error vibrating device: {str(e)} (Ensure Termux:API is installed)"

def search_files(pattern):
    try:
        import fnmatch
        matches = []
        for root, dirnames, filenames in os.walk(WORKSPACE_DIR):
            for filename in fnmatch.filter(filenames, pattern):
                rel_dir = os.path.relpath(root, WORKSPACE_DIR)
                matches.append(os.path.join(rel_dir, filename) if rel_dir != "." else filename)
        if not matches:
            return f"No files matching pattern '{pattern}' found."
        return json.dumps(matches, indent=2)
    except Exception as e:
        return f"Error searching files: {str(e)}"

def dns_lookup(domain, record_type="A"):
    try:
        import requests
        url = "https://cloudflare-dns.com/dns-query"
        headers = {"Accept": "application/dns-json"}
        params = {"name": domain, "type": record_type}
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            return f"Error: DNS query failed with status code {res.status_code}"
        data = res.json()
        if "Answer" not in data:
            return f"No records of type {record_type} found for {domain}."
        answers = []
        for ans in data["Answer"]:
            answers.append(f"Name: {ans.get('name')}, Type: {ans.get('type')}, TTL: {ans.get('TTL')}, Data: {ans.get('data')}")
        return "\n".join(answers)
    except Exception as e:
        return f"Error during DNS lookup: {str(e)}"

def whois_lookup(domain):
    try:
        import requests
        url = f"https://rdap.org/domain/{domain.strip().lower()}"
        res = requests.get(url, timeout=10)
        if res.status_code == 404:
            return f"Domain {domain} not found or not supported by RDAP."
        elif res.status_code != 200:
            return f"Error: RDAP query failed with status code {res.status_code}"
        
        data = res.json()
        registrar = "Unknown"
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                vcard = entity.get("vcardArray", [])
                if len(vcard) > 1:
                    for field in vcard[1]:
                        if field[0] == "fn":
                            registrar = field[3]
                            break
        
        events = []
        for event in data.get("events", []):
            event_action = event.get("eventAction", "")
            event_date = event.get("eventDate", "")
            events.append(f"{event_action.capitalize()}: {event_date}")
            
        summary = [
            f"Domain: {data.get('ldhName', domain)}",
            f"Registrar: {registrar}",
            "Status: " + ", ".join(data.get("status", ["Unknown"])),
            "Events:\n  " + "\n  ".join(events) if events else "Events: Unknown"
        ]
        
        nameservers = [ns.get("ldhName") for ns in data.get("nameservers", []) if ns.get("ldhName")]
        if nameservers:
            summary.append("Nameservers: " + ", ".join(nameservers))
            
        return "\n".join(summary)
    except Exception as e:
        return f"Error during WHOIS lookup: {str(e)}"

def analyze_hash(hash_str):
    try:
        hash_str = hash_str.strip()
        length = len(hash_str)
        
        import re
        is_hex = bool(re.match(r'^[a-fA-F0-9]+$', hash_str))
        
        possible_types = []
        if is_hex:
            if length == 32:
                possible_types.append("MD5")
            elif length == 40:
                possible_types.append("SHA-1")
            elif length == 56:
                possible_types.append("SHA-224")
            elif length == 64:
                possible_types.append("SHA-256")
            elif length == 96:
                possible_types.append("SHA-384")
            elif length == 128:
                possible_types.append("SHA-512")
                
        if hash_str.startswith("$2a$") or hash_str.startswith("$2b$") or hash_str.startswith("$2y$"):
            if length == 60:
                possible_types.append("bcrypt")
        elif hash_str.startswith("$pbkdf2-sha256$"):
            possible_types.append("PBKDF2-SHA256")
        elif hash_str.startswith("$argon2id$") or hash_str.startswith("$argon2i$"):
            possible_types.append("Argon2")
            
        if not possible_types:
            if length == 16:
                possible_types.append("Half-MD5")
            else:
                return f"Could not identify the hash format of '{hash_str}'. Length: {length}."
                
        return f"Hash: {hash_str}\nLikely Algorithm(s): {', '.join(possible_types)}"
    except Exception as e:
        return f"Error analyzing hash: {str(e)}"

def open_url_on_phone(url):
    try:
        # Standardize URL
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        ok, out = run_adb_command("devices")
        if not ok or len([line for line in out.strip().split("\n") if "device" in line and not "devices" in line]) == 0:
            return "Error: ADB/Shizuku is not connected. Enable Wireless Debugging or start Shizuku app first."
            
        ok, out = run_adb_command(f"shell am start -a android.intent.action.VIEW -d '{url}'")
        if ok:
            return f"Success: Opened URL '{url}' on Android phone screen."
        return f"Error opening URL on phone: {out}"
    except Exception as e:
        return f"Error executing open URL tool: {str(e)}"

def execute_root_command(command):
    try:
        import subprocess
        import shutil
        
        # 1. Check if 'su' binary is available
        su_path = shutil.which("su")
        root_signatures = ["/system/bin/su", "/system/xbin/su", "/sbin/su", "/system/sd/xbin/su", "/system/bin/failsafe/su", "/data/local/xbin/su", "/data/local/bin/su"]
        su_exists = su_path is not None or any(os.path.exists(p) for p in root_signatures)
        
        if not su_exists:
            return "Error: SuperUser 'su' binary not found. This tool requires a rooted Android device."
            
        # Safety token validation (prevent basic bricking scenarios)
        forbidden_tokens = ["rm -rf", "rm -f /", "mkfs", "dd if="]
        for token in forbidden_tokens:
            if token in command:
                return f"Error: Root command blocked. Forbidden token: '{token}'"
                
        # Run command with su -c
        # On Android, su -c "command" runs the command as root.
        res = subprocess.run(["su", "-c", command], capture_output=True, text=True, timeout=30)
        
        output = f"Exit Code: {res.returncode}\n"
        if res.stdout:
            output += f"Stdout:\n{res.stdout}\n"
        if res.stderr:
            output += f"Stderr:\n{res.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Root command execution timed out (limit: 30 seconds)."
    except Exception as e:
        return f"Error executing root command: {str(e)}"

def audit_sms_inbox(limit=10):
    try:
        import subprocess
        limit_val = max(1, min(int(limit), 50))
        cmd = ["termux-sms-list", "-l", str(limit_val)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error listing SMS: {res.stderr} (Ensure Termux:API is installed and SMS read permission is granted)"
    except Exception as e:
        return f"Error executing SMS audit tool: {str(e)}"

def ip_geolocation_lookup(ip_address):
    try:
        import requests
        ip_clean = ip_address.strip()
        # Use ip-api.com (free, no key required)
        url = f"http://ip-api.com/json/{ip_clean}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                details = {
                    "query": data.get("query"),
                    "status": "success",
                    "country": data.get("country"),
                    "region_name": data.get("regionName"),
                    "city": data.get("city"),
                    "zip": data.get("zip"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "timezone": data.get("timezone"),
                    "isp": data.get("isp"),
                    "org": data.get("org"),
                    "as": data.get("as")
                }
                return json.dumps(details, indent=2)
            else:
                return f"Error looking up IP: {data.get('message', 'Failed query')}"
        return f"Error: Request failed with status code {res.status_code}"
    except Exception as e:
        return f"Error executing IP geolocation: {str(e)}"

def read_phone_sensors(sensor_name=""):
    try:
        import subprocess
        if not sensor_name:
            cmd = ["termux-sensor", "-l"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return res.stdout.strip()
            return f"Error listing sensors: {res.stderr} (Ensure Termux:API is installed)"
        else:
            # Read specific sensor once
            cmd = ["termux-sensor", "-n", "1", "-s", sensor_name]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if res.returncode == 0:
                return res.stdout.strip()
            return f"Error reading sensor '{sensor_name}': {res.stderr}"
    except Exception as e:
        return f"Error executing sensor reader: {str(e)}"

def scheduler_worker_loop():
    import time
    import datetime
    
    schedules_file = os.path.join(WORKSPACE_DIR, "schedules.json")
    print("PocketstrikeAI Scheduler Thread started...")
    
    while True:
        # Sleep for 15 seconds between ticks
        time.sleep(15)
        
        if not os.path.exists(schedules_file):
            continue
            
        try:
            with open(schedules_file, "r") as f:
                tasks = json.load(f)
        except Exception:
            continue
            
        now = time.time()
        modified = False
        token = config.get("telegram_token")
        
        for task in tasks:
            if task.get("status") != "pending":
                continue
                
            trigger_time = task.get("trigger_time")
            task_type = task.get("type", "reminder")
            
            # For one-shot reminders
            if task_type == "reminder":
                if now >= trigger_time:
                    execute_scheduled_action(task, token)
                    task["status"] = "completed"
                    task["fired_at"] = now
                    modified = True
                    
            # For recurring cron jobs
            elif task_type == "cron":
                last_run = task.get("last_run", 0)
                interval = task.get("interval_seconds", 0)
                
                if interval > 0 and (now - last_run) >= interval:
                    execute_scheduled_action(task, token)
                    task["last_run"] = now
                    modified = True
                    
        if modified:
            try:
                with open(schedules_file, "w") as f:
                    json.dump(tasks, f, indent=2)
            except Exception as e:
                print(f"Error saving schedules: {e}")

def execute_scheduled_action(task, token):
    desc = task.get("description", "Scheduled Reminder")
    target = task.get("target", "system")
    
    # 1. Print a visual warning in the Termux console and emit the ASCII Bell sound (\a)
    import sys
    import shutil
    print(f"\n\033[1;32m🔔 [SCHEDULED ALERT] {desc}\033[0m\n", flush=True)
    sys.stdout.write('\a')
    sys.stdout.flush()
    
    # 2. Check if Termux:API is set up. If not, dynamically fallback to Telegram (if token exists)
    termux_api_available = shutil.which("termux-notification") is not None
    if not termux_api_available and target == "system":
        if token:
            target = "both"
            
    msg = f"🔔 **PocketstrikeAI Alert** 🔔\n\nTask: {desc}"
    
    if target == "system" or target == "both":
        send_android_notification("PocketstrikeAI Alert", desc)
        vibrate_device(800)
        speak_text(f"Notification: {desc}")
        
    if (target == "telegram" or target == "both") and token:
        sessions = load_telegram_sessions()
        for cid in sessions.keys():
            send_telegram_msg(token, cid, msg)

def parse_time_offset(trigger_str):
    import datetime
    import re
    now = datetime.datetime.now()
    
    match = re.match(r'^(\d+)([mhdw])$', trigger_str.strip().lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == 'm':
            delta = datetime.timedelta(minutes=amount)
        elif unit == 'h':
            delta = datetime.timedelta(hours=amount)
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
        elif unit == 'w':
            delta = datetime.timedelta(weeks=amount)
        return (now + delta).timestamp()
        
    match_abs = re.match(r'^(\d{1,2}):(\d{2})$', trigger_str.strip())
    if match_abs:
        hour = int(match_abs.group(1))
        minute = int(match_abs.group(2))
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_time < now:
            target_time += datetime.timedelta(days=1)
        return target_time.timestamp()
        
    return None

def add_scheduled_task(task_type, trigger, description, target="telegram"):
    try:
        import time
        schedules_file = os.path.join(WORKSPACE_DIR, "schedules.json")
        
        tasks = []
        if os.path.exists(schedules_file):
            try:
                with open(schedules_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
            except Exception:
                pass
                
        task_id = f"task_{int(time.time())}"
        task_type = task_type.strip().lower()
        target = target.strip().lower()
        
        if task_type not in ["reminder", "cron"]:
            return "Error: task_type must be either 'reminder' or 'cron'."
            
        if target not in ["telegram", "system", "both"]:
            return "Error: target must be 'telegram', 'system', or 'both'."
            
        new_task = {
            "id": task_id,
            "type": task_type,
            "description": description,
            "target": target,
            "status": "pending",
            "created_at": time.time()
        }
        
        if task_type == "reminder":
            trigger_time = parse_time_offset(trigger)
            if not trigger_time:
                return f"Error: Could not parse reminder time '{trigger}'. Use formats like '10m', '2h', '1d', or '18:30'."
            new_task["trigger_time"] = trigger_time
            new_task["trigger_desc"] = trigger
            
        elif task_type == "cron":
            import re
            match = re.match(r'^(\d+)([mhdw])$', trigger.strip().lower())
            if not match:
                return f"Error: Could not parse cron interval '{trigger}'. Use formats like '5m', '1h', or '1d'."
            amount = int(match.group(1))
            unit = match.group(2)
            
            interval_seconds = 0
            if unit == 'm':
                interval_seconds = amount * 60
            elif unit == 'h':
                interval_seconds = amount * 3600
            elif unit == 'd':
                interval_seconds = amount * 86400
            elif unit == 'w':
                interval_seconds = amount * 604800
                
            new_task["interval_seconds"] = interval_seconds
            new_task["interval_desc"] = trigger
            new_task["last_run"] = time.time()
            
        tasks.append(new_task)
        
        with open(schedules_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
            
        desc_type = "One-shot reminder" if task_type == "reminder" else f"Recurring cron (every {trigger})"
        return f"Success: Scheduled task '{task_id}' successfully. Type: {desc_type}. Target: {target}."
        
    except Exception as e:
        return f"Error scheduling task: {str(e)}"

def list_scheduled_tasks():
    try:
        schedules_file = os.path.join(WORKSPACE_DIR, "schedules.json")
        if not os.path.exists(schedules_file):
            return "No scheduled tasks found."
            
        with open(schedules_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            
        if not tasks:
            return "No scheduled tasks found."
            
        import datetime
        output = ["=== SCHEDULED TASKS & CRONS ==="]
        for t in tasks:
            status_badge = f"[{t.get('status').upper()}]"
            details = f"ID: {t.get('id')} | {t.get('description')} | Target: {t.get('target')}"
            
            if t.get("type") == "reminder":
                trigger_dt = datetime.datetime.fromtimestamp(t.get("trigger_time")).strftime('%Y-%m-%d %H:%M:%S')
                output.append(f"{status_badge} Reminder -> Trigger Time: {trigger_dt} ({t.get('trigger_desc')}) | {details}")
            else:
                last_dt = datetime.datetime.fromtimestamp(t.get("last_run")).strftime('%Y-%m-%d %H:%M:%S') if t.get("last_run") else "Never"
                output.append(f"{status_badge} Cron -> Interval: {t.get('interval_desc')} | Last Run: {last_dt} | {details}")
                
        return "\n".join(output)
    except Exception as e:
        return f"Error listing scheduled tasks: {str(e)}"

def remove_scheduled_task(task_id):
    try:
        schedules_file = os.path.join(WORKSPACE_DIR, "schedules.json")
        if not os.path.exists(schedules_file):
            return "Error: No scheduled tasks found."
            
        with open(schedules_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            
        filtered_tasks = [t for t in tasks if t.get("id") != task_id]
        
        if len(filtered_tasks) == len(tasks):
            return f"Error: Task ID '{task_id}' not found."
            
        with open(schedules_file, "w", encoding="utf-8") as f:
            json.dump(filtered_tasks, f, indent=2, ensure_ascii=False)
            
        return f"Success: Removed scheduled task '{task_id}'."
    except Exception as e:
        return f"Error removing scheduled task: {str(e)}"

def detect_arp_spoofing():
    try:
        arp_file = "/proc/net/arp"
        if not os.path.exists(arp_file):
            return "Error: ARP table file /proc/net/arp is not accessible. This tool requires Android/Linux environment."
            
        with open(arp_file, "r") as f:
            lines = f.readlines()
            
        mac_to_ips = {}
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[3].lower()
                
                if mac not in ["00:00:00:00:00:00", "*", "00:00:00:00:00:00:00:00"]:
                    if mac not in mac_to_ips:
                        mac_to_ips[mac] = []
                    mac_to_ips[mac].append(ip)
                    
        spoofed_entries = []
        for mac, ips in mac_to_ips.items():
            if len(ips) > 1:
                spoofed_entries.append({
                    "mac": mac,
                    "ips": ips
                })
                
        results = {
            "status": "safe",
            "message": "No active ARP spoofing detected. All MAC mappings are unique.",
            "mappings_checked": len(mac_to_ips)
        }
        
        if spoofed_entries:
            results["status"] = "warning"
            results["message"] = "WARNING: Potential ARP Spoofing / MITM attack detected! Multiple IP addresses map to the same MAC address."
            results["conflicting_entries"] = spoofed_entries
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error executing ARP spoofing detector: {str(e)}"

def audit_vpn_connection():
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("http://ip-api.com/json/", headers=headers, timeout=10)
        
        if res.status_code != 200:
            return f"Error connecting to lookup server (code {res.status_code})."
            
        data = res.json()
        if data.get("status") != "success":
            return f"Lookup failed: {data.get('message', 'Unknown failure')}"
            
        ip = data.get("query")
        isp = data.get("isp", "")
        org = data.get("org", "")
        country = data.get("country", "")
        
        vpn_interface_active = False
        vpn_interfaces = []
        try:
            import socket
            if hasattr(socket, "if_nameindex"):
                interfaces = [x[1] for x in socket.if_nameindex()]
                for name in interfaces:
                    if any(prefix in name.lower() for prefix in ["tun", "tap", "wg", "ppp", "vpn", "p2p"]):
                        vpn_interface_active = True
                        vpn_interfaces.append(name)
        except Exception:
            pass
            
        vpn_keywords = ["vpn", "hosting", "cloud", "mullvad", "nordvpn", "expressvpn", "surfshark", "cloudflare", "ovh", "digitalocean", "linode", "amazon", "google", "microsoft"]
        isp_org_str = (isp + " " + org).lower()
        is_vpn_isp = any(kw in isp_org_str for kw in vpn_keywords)
        
        status = "unprotected"
        message = "No VPN connection detected. Your connection appears to be direct and unprotected."
        
        if vpn_interface_active or is_vpn_isp:
            status = "protected"
            reasons = []
            if vpn_interface_active:
                reasons.append(f"active VPN interface(s) detected: {', '.join(vpn_interfaces)}")
            if is_vpn_isp:
                reasons.append(f"public IP is owned by hosting/VPN provider ({isp})")
            message = f"VPN connection detected. Your connection is protected via: {' and '.join(reasons)}."
            
        audit = {
            "public_ip": ip,
            "isp": isp,
            "org": org,
            "location": f"{data.get('city')}, {data.get('regionName')}, {country}",
            "vpn_detection_status": status,
            "message": message
        }
        return json.dumps(audit, indent=2)
    except Exception as e:
        return f"Error executing connection auditor: {str(e)}"

def audit_website_security(url):
    try:
        import urllib.parse
        import requests
        import ssl
        import socket
        import datetime
        
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        if ":" in domain:
            domain = domain.split(":")[0]
            
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=12, verify=False)
        resp_headers = res.headers
        
        security_headers = {
            "Strict-Transport-Security": resp_headers.get("Strict-Transport-Security"),
            "Content-Security-Policy": resp_headers.get("Content-Security-Policy"),
            "X-Frame-Options": resp_headers.get("X-Frame-Options"),
            "X-Content-Type-Options": resp_headers.get("X-Content-Type-Options"),
            "Referrer-Policy": resp_headers.get("Referrer-Policy"),
            "X-XSS-Protection": resp_headers.get("X-XSS-Protection")
        }
        
        header_evals = {}
        score = 0
        total = len(security_headers)
        for h, val in security_headers.items():
            if val:
                header_evals[h] = f"Present: {val[:40]}..." if len(val) > 40 else f"Present: {val}"
                score += 1
            else:
                header_evals[h] = "MISSING! Susceptible to attacks."
                
        ssl_details = {}
        if url.startswith("https://") or parsed_url.scheme == "https" or not parsed_url.scheme:
            try:
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        
                subject = dict(x[0] for x in cert.get('subject', ()))
                issuer = dict(x[0] for x in cert.get('issuer', ()))
                not_before = cert.get('notBefore')
                not_after = cert.get('notAfter')
                
                expiry_dt = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                remaining_days = (expiry_dt - datetime.datetime.utcnow()).days
                
                ssl_details = {
                    "common_name": subject.get("commonName"),
                    "issuer": issuer.get("organizationName") or issuer.get("commonName"),
                    "not_before": not_before,
                    "not_after": not_after,
                    "days_remaining": remaining_days,
                    "status": "valid" if remaining_days > 0 else "expired"
                }
            except Exception as ssl_err:
                ssl_details = {
                    "status": "error",
                    "error_message": f"SSL Handshake failed: {str(ssl_err)}"
                }
                
        audit_results = {
            "target_url": url,
            "target_domain": domain,
            "status_code": res.status_code,
            "security_headers_grade": f"{score}/{total} set",
            "security_headers_audit": header_evals,
            "ssl_certificate_details": ssl_details if ssl_details else "N/A (HTTP)"
        }
        return json.dumps(audit_results, indent=2)
    except Exception as e:
        return f"Error executing website security auditor: {str(e)}"

def dump_ui_layout():
    try:
        import re
        import os
        import xml.etree.ElementTree as ET
        
        # 1. Run uiautomator dump on the device
        dump_file_on_device = "/data/local/tmp/window_dump.xml"
        ok, out = run_adb_command(f"shell uiautomator dump {dump_file_on_device}")
        if not ok:
            return f"Error dumping UI layout: {out}"
            
        # 2. Cat/Read the XML content from the device
        ok, xml_content = run_adb_command(f"shell cat {dump_file_on_device}")
        if not ok or not xml_content.strip():
            return f"Error reading UI XML: {xml_content}"
            
        # Clean up the file on the device
        run_adb_command(f"shell rm {dump_file_on_device}")
        
        # 3. Parse the XML content
        try:
            # Android XML dumps sometimes contain null characters or bad encoding; let's sanitize
            cleaned_xml = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x80-\xFF]', '', xml_content)
            root = ET.fromstring(cleaned_xml)
        except Exception as parse_err:
            return f"Error parsing UI XML: {parse_err}\nRaw output length: {len(xml_content)}"
            
        interactable_elements = []
        
        def traverse(node):
            attrib = node.attrib
            # Extract attributes
            text = attrib.get("text", "").strip()
            content_desc = attrib.get("content-desc", "").strip()
            resource_id = attrib.get("resource-id", "").strip()
            class_name = attrib.get("class", "").split(".")[-1] # Short class name e.g. Button
            bounds = attrib.get("bounds", "")
            clickable = attrib.get("clickable", "false").lower() == "true"
            enabled = attrib.get("enabled", "true").lower() == "true"
            
            # Check if this node has useful text or is interactable
            if (text or content_desc or resource_id) and enabled:
                # Parse bounds [xmin,ymin][xmax,ymax]
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    x_center = (x1 + x2) // 2
                    y_center = (y1 + y2) // 2
                    
                    element_info = {
                        "class": class_name,
                        "center": (x_center, y_center),
                        "bounds": f"[{x1},{y1}][{x2},{y2}]"
                    }
                    if text:
                        element_info["text"] = text
                    if content_desc:
                        element_info["content-desc"] = content_desc
                    if resource_id:
                        # Clean resource id: remove package prefix if long
                        short_id = resource_id.split("/")[-1]
                        element_info["resource-id"] = short_id
                    if clickable:
                        element_info["clickable"] = True
                        
                    interactable_elements.append(element_info)
                    
            for child in node:
                traverse(child)
                
        traverse(root)
        
        # 4. Format output cleanly
        if not interactable_elements:
            return "No readable or interactable elements found on the current screen."
            
        output = ["=== ACTIVE SCREEN UI ELEMENTS ==="]
        for idx, el in enumerate(interactable_elements, 1):
            details = []
            if "text" in el:
                details.append(f"Text: \"{el['text']}\"")
            if "content-desc" in el:
                details.append(f"Desc: \"{el['content-desc']}\"")
            if "resource-id" in el:
                details.append(f"ID: \"{el['resource-id']}\"")
                
            details_str = ", ".join(details)
            clickable_badge = " [Clickable]" if el.get("clickable") else ""
            output.append(f"[{idx}] {el['class']}{clickable_badge} -> Center: {el['center']} | {details_str}")
            
        return "\n".join(output)
        
    except Exception as e:
        return f"Error executing UI layout dumper: {str(e)}"

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
        elif name == "execute_termux_command":
            command = kwargs.get("command")
            if not command:
                return "Error: Missing required argument 'command'."
            return execute_termux_command(command)
        elif name == "web_search":
            query = kwargs.get("query")
            if not query:
                return "Error: Missing required argument 'query'."
            return web_search(query)
        elif name == "fetch_url":
            url = kwargs.get("url")
            if not url:
                return "Error: Missing required argument 'url'."
            return fetch_url(url)
        elif name == "get_network_details":
            return get_network_details()
        elif name == "list_local_listeners":
            return list_local_listeners()
        elif name == "send_android_notification":
            title = kwargs.get("title")
            message = kwargs.get("message")
            if not title or not message:
                return "Error: Missing required arguments 'title' and/or 'message'."
            return send_android_notification(title, message)
        elif name == "vibrate_device":
            duration_ms = kwargs.get("duration_ms", 500)
            return vibrate_device(duration_ms)
        elif name == "search_files":
            pattern = kwargs.get("pattern")
            if not pattern:
                return "Error: Missing required argument 'pattern'."
            return search_files(pattern)
        elif name == "local_network_scan":
            return local_network_scan()
        elif name == "audit_android_security":
            return audit_android_security()
        elif name == "subnet_port_sweep":
            port_number = kwargs.get("port_number")
            if port_number is None:
                return "Error: Missing required argument 'port_number'."
            return subnet_port_sweep(port_number)
        elif name == "take_camera_photo":
            camera_id = kwargs.get("camera_id", "0")
            return take_camera_photo(camera_id)
        elif name == "get_phone_location":
            return get_phone_location()
        elif name == "make_phone_call":
            phone_number = kwargs.get("phone_number")
            if not phone_number:
                return "Error: Missing required argument 'phone_number'."
            return make_phone_call(phone_number)
        elif name == "send_sms":
            phone_number = kwargs.get("phone_number")
            message = kwargs.get("message")
            if not phone_number or not message:
                return "Error: Missing required arguments 'phone_number' and/or 'message'."
            return send_sms(phone_number, message)
        elif name == "set_brightness":
            level = kwargs.get("level")
            if level is None:
                return "Error: Missing required argument 'level'."
            return set_brightness(level)
        elif name == "set_volume":
            stream = kwargs.get("stream")
            level = kwargs.get("level")
            if not stream or level is None:
                return "Error: Missing required arguments 'stream' and/or 'level'."
            return set_volume(stream, level)
        elif name == "take_screenshot":
            return take_screenshot()
        elif name == "tap_screen":
            x = kwargs.get("x")
            y = kwargs.get("y")
            if x is None or y is None:
                return "Error: Missing required arguments 'x' and/or 'y'."
            return tap_screen(x, y)
        elif name == "swipe_screen":
            x1 = kwargs.get("x1")
            y1 = kwargs.get("y1")
            x2 = kwargs.get("x2")
            y2 = kwargs.get("y2")
            duration_ms = kwargs.get("duration_ms", 500)
            if x1 is None or y1 is None or x2 is None or y2 is None:
                return "Error: Missing required coordinate parameters."
            return swipe_screen(x1, y1, x2, y2, duration_ms)
        elif name == "press_key":
            key_code = kwargs.get("key_code")
            if key_code is None:
                return "Error: Missing required argument 'key_code'."
            return press_key(key_code)
        elif name == "launch_app":
            package_name = kwargs.get("package_name")
            if not package_name:
                return "Error: Missing required argument 'package_name'."
            return launch_app(package_name)
        elif name == "control_android_system":
            action = kwargs.get("action")
            target = kwargs.get("target", "")
            if not action:
                return "Error: Missing required argument 'action'."
            return control_android_system(action, target)
        elif name == "get_clipboard":
            return get_clipboard()
        elif name == "set_clipboard":
            text = kwargs.get("text")
            if text is None:
                return "Error: Missing required argument 'text'."
            return set_clipboard(text)
        elif name == "list_installed_apps":
            user_only = kwargs.get("user_only", True)
            return list_installed_apps(user_only)
        elif name == "scan_wifi_networks":
            return scan_wifi_networks()
        elif name == "speak_text":
            text = kwargs.get("text")
            if not text:
                return "Error: Missing required argument 'text'."
            return speak_text(text)
        elif name == "dns_lookup":
            domain = kwargs.get("domain")
            record_type = kwargs.get("record_type", "A")
            if not domain:
                return "Error: Missing required argument 'domain'."
            return dns_lookup(domain, record_type)
        elif name == "whois_lookup":
            domain = kwargs.get("domain")
            if not domain:
                return "Error: Missing required argument 'domain'."
            return whois_lookup(domain)
        elif name == "analyze_hash":
            hash_str = kwargs.get("hash_str")
            if not hash_str:
                return "Error: Missing required argument 'hash_str'."
            return analyze_hash(hash_str)
        elif name == "open_url_on_phone":
            url = kwargs.get("url")
            if not url:
                return "Error: Missing required argument 'url'."
            return open_url_on_phone(url)
        elif name == "execute_root_command":
            command = kwargs.get("command")
            if not command:
                return "Error: Missing required argument 'command'."
            return execute_root_command(command)
        elif name == "audit_sms_inbox":
            limit = kwargs.get("limit", 10)
            return audit_sms_inbox(limit)
        elif name == "ip_geolocation_lookup":
            ip_address = kwargs.get("ip_address")
            if not ip_address:
                return "Error: Missing required argument 'ip_address'."
            return ip_geolocation_lookup(ip_address)
        elif name == "read_phone_sensors":
            sensor_name = kwargs.get("sensor_name", "")
            return read_phone_sensors(sensor_name)
        elif name == "dump_ui_layout":
            return dump_ui_layout()
        elif name == "add_scheduled_task":
            task_type = kwargs.get("task_type")
            trigger = kwargs.get("trigger")
            description = kwargs.get("description")
            target = kwargs.get("target", "telegram")
            if not task_type or not trigger or not description:
                return "Error: Missing required arguments."
            return add_scheduled_task(task_type, trigger, description, target)
        elif name == "list_scheduled_tasks":
            return list_scheduled_tasks()
        elif name == "remove_scheduled_task":
            task_id = kwargs.get("task_id")
            if not task_id:
                return "Error: Missing required argument 'task_id'."
            return remove_scheduled_task(task_id)
        elif name == "detect_arp_spoofing":
            return detect_arp_spoofing()
        elif name == "audit_vpn_connection":
            return audit_vpn_connection()
        elif name == "audit_website_security":
            url = kwargs.get("url")
            if not url:
                return "Error: Missing required argument 'url'."
            return audit_website_security(url)
        else:
            return f"Error: Tool '{name}' is not recognized."
    except Exception as e:
        return f"Error executing tool: {str(e)}"

def get_ai_response_with_tools(messages):
    # Ensure the system prompt containing all 28 ReAct tools and capabilities is always active
    system_index = -1
    for idx, msg in enumerate(messages):
        if msg["role"] == "system":
            system_index = idx
            break
            
    full_prompt = get_system_prompt()
    if system_index >= 0:
        messages[system_index]["content"] = full_prompt
    else:
        messages.insert(0, {
            "role": "system",
            "content": full_prompt
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
    # Ensure the system prompt containing all 28 ReAct tools and capabilities is always active
    system_index = -1
    for idx, msg in enumerate(messages):
        if msg["role"] == "system":
            system_index = idx
            break
            
    full_prompt = get_system_prompt()
    if system_index >= 0:
        messages[system_index]["content"] = full_prompt
    else:
        messages.insert(0, {
            "role": "system",
            "content": full_prompt
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

def load_telegram_sessions():
    tg_file = os.path.join(WORKSPACE_DIR, "telegram_chats.json")
    if os.path.exists(tg_file):
        try:
            with open(tg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading telegram sessions: {e}")
    return {}

def save_telegram_sessions(sessions):
    tg_file = os.path.join(WORKSPACE_DIR, "telegram_chats.json")
    try:
        os.makedirs(os.path.dirname(tg_file), exist_ok=True)
        with open(tg_file, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in sessions.items()}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving telegram sessions: {e}")

# Telegram Bot Polling Thread
def telegram_bot_loop(token):
    offset = 0
    sessions = load_telegram_sessions()
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
                    save_telegram_sessions(sessions)
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
                save_telegram_sessions(sessions)
                
                # Check if camera photo was successfully captured in the chat session
                photo_path = os.path.join(WORKSPACE_DIR, "captured_photo.jpg")
                screenshot_path = os.path.join(WORKSPACE_DIR, "captured_screenshot.png")
                
                # Send back text response first
                send_telegram_msg(token, chat_id, ai_response)
                
                # Upload files to Telegram chat automatically if created/modified during execution
                if "captured_photo.jpg" in ai_response.lower() and os.path.exists(photo_path):
                    send_telegram_photo(token, chat_id, photo_path, caption="📸 PocketstrikeAI Camera Capture")
                    # Clean up file to prevent duplicate triggers
                    try: os.remove(photo_path)
                    except Exception: pass
                    
                if "captured_screenshot.png" in ai_response.lower() and os.path.exists(screenshot_path):
                    send_telegram_photo(token, chat_id, screenshot_path, caption="📱 PocketstrikeAI Screenshot Capture")
                    try: os.remove(screenshot_path)
                    except Exception: pass

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

def send_telegram_photo(token, chat_id, photo_path, caption=None):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        if not os.path.exists(photo_path):
            return False
        with open(photo_path, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            res = requests.post(url, data=data, files=files, timeout=30)
            return res.status_code == 200
    except Exception as e:
        print(f"Error sending photo to Telegram: {e}")
        return False

# Web Server Routes
@app.route('/api/history/load', methods=['GET'])
def load_history():
    history_file = os.path.join(WORKSPACE_DIR, "web_chats.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify([])

@app.route('/api/history/sync', methods=['POST'])
def sync_history():
    data = request.json or []
    history_file = os.path.join(WORKSPACE_DIR, "web_chats.json")
    try:
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        print("Starting anyway in fallback mode.")
        
    # Start Scheduler Thread
    scheduler_thread = threading.Thread(target=scheduler_worker_loop, daemon=True)
    scheduler_thread.start()
    # 2. Launch Telegram Bot if enabled
    telegram_status = "Disabled"
    if config.get("telegram_enabled") and config.get("telegram_token"):
        tg_token = config["telegram_token"]
        telegram_bot_thread = threading.Thread(target=telegram_bot_loop, args=(tg_token,), daemon=True)
        telegram_bot_thread.start()
        telegram_status = "Active"

    # 3. Check Shizuku status dynamically
    import shutil
    shizuku_provisioned = shutil.which("rish") is not None
    shizuku_status = "Not Connected"
    
    # Auto-provision on startup if not in PATH but files exist
    if not shizuku_provisioned:
        possible_srcs = [
            "/sdcard/Shizuku/rish",
            "/storage/emulated/0/Shizuku/rish",
            os.path.expanduser("~/storage/shared/Shizuku/rish"),
            os.path.expanduser("~/storage/downloads/rish"),
            os.path.expanduser("~/storage/downloads/Shizuku/rish"),
            "/sdcard/Download/rish",
            "/sdcard/Download/Shizuku/rish",
            "/storage/emulated/0/Download/rish",
            "/storage/emulated/0/Download/Shizuku/rish",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "rish")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace", "rish"))
        ]
        shizuku_src = None
        for path in possible_srcs:
            if os.path.exists(path):
                shizuku_src = path
                break
        if shizuku_src:
            try:
                prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
                termux_bin = os.path.join(prefix, "bin")
                if os.path.exists(termux_bin):
                    import glob
                    src_dir = os.path.dirname(shizuku_src)
                    for fpath in glob.glob(os.path.join(src_dir, "rish*")):
                        dest_file = os.path.join(termux_bin, os.path.basename(fpath))
                        shutil.copy(fpath, dest_file)
                    os.chmod(os.path.join(termux_bin, "rish"), 0o755)
                    dex_file = os.path.join(termux_bin, "rish_shizuku.dex")
                    if os.path.exists(dex_file):
                        os.chmod(dex_file, 0o444)
                    shizuku_provisioned = True
                    print(f"PocketstrikeAI: Auto-installed Shizuku rish binaries on startup from {shizuku_src}!")
            except Exception as e:
                print(f"PocketstrikeAI: Startup Shizuku auto-install failed: {e}")
        else:
            print("⚠️ Shizuku 'rish' not found in PATH or storage. Put 'rish' and 'rish_shizuku.dex' in your phone's main Downloads folder or in the project directory.")

    if shizuku_provisioned:
        try:
            import subprocess
            env = os.environ.copy()
            env["RISH_APPLICATION_ID"] = get_termux_package_id()
            env.pop("LD_LIBRARY_PATH", None)
            env.pop("LD_PRELOAD", None)
            shell_exe = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "sh"
            
            # Fast test call to rish to check if binder is active and approved
            # Use 2.0s timeout: if it hangs, it is likely waiting for authorization
            try:
                res = subprocess.run([shell_exe, shutil.which("rish"), "-c", "echo 1"], capture_output=True, timeout=2.0, env=env)
                is_ok = (res.returncode == 0)
                out = res.stdout.decode('utf-8', errors='ignore').strip() if res.stdout else ""
                err = res.stderr.decode('utf-8', errors='ignore').strip() if res.stderr else ""
                need_auth = (res.returncode == 1 or "permission" in err.lower() or "permission" in out.lower())
            except subprocess.TimeoutExpired:
                is_ok = False
                need_auth = True
                out, err = "", ""
            
            if is_ok:
                shizuku_status = "Active / Connected"
            elif need_auth:
                print("\n\033[1;33m📣 [Shizuku Authorization Required]\033[0m")
                print("\033[38;5;46m  Please check your phone screen now!\033[0m")
                print("\033[38;5;255m  A popup will request permission for Termux to access Shizuku.\033[0m")
                print("\033[1;32m  👉 Tap 'Always Allow' or 'Allow' to authorize the agent. 👈\033[0m\n")
                
                try:
                    import pty
                    master, slave = pty.openpty()
                    # Spawn rish in a pty so it thinks it is in an interactive terminal and triggers popup
                    p = subprocess.Popen(
                        [shutil.which("rish")],
                        stdin=slave,
                        stdout=slave,
                        stderr=slave,
                        env=env,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                    # Keep it open for 10 seconds to give user time to click Allow
                    time.sleep(10.0)
                    p.terminate()
                    p.wait(timeout=2.0)
                except Exception as pty_err:
                    print(f"  (Failed to start pty trigger: {pty_err})")
                    
                # Re-test connection state
                try:
                    res_retry = subprocess.run([shell_exe, shutil.which("rish"), "-c", "echo 1"], capture_output=True, timeout=3.5, env=env)
                    if res_retry.returncode == 0:
                        print("\033[38;5;46m[✓] Shizuku authorization successful!\033[0m\n")
                        shizuku_status = "Active / Connected"
                    else:
                        shizuku_status = "Unauthorized (Approve Termux in Shizuku)"
                except subprocess.TimeoutExpired:
                    shizuku_status = "Unauthorized (Authorization Timeout)"
            else:
                print(f"⚠️ Shizuku test failed (code {res.returncode}). stdout: '{out}', stderr: '{err}'")
                shizuku_status = "Daemon Stopped (Start Shizuku app)"
        except Exception as e:
            print(f"⚠️ Shizuku test error: {str(e)}")
            shizuku_status = f"Daemon Stopped ({type(e).__name__})"
    else:
        shizuku_status = "Not Configured (Export files via Shizuku)"

    # 4. Print access information
    local_ip = get_local_ip()
    green_color = "\033[38;5;46m"
    white_color = "\033[38;5;255m"
    blue_color = "\033[38;5;39m"
    reset_color = "\033[0m"
    banner_text = f"""{green_color}██████╗ ██╗  ██╗███████╗████████╗    █████╗ ██╗
██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝   ██╔══██╗██║
{white_color}██████╔╝█████╔╝ ███████╗   ██║      ███████║██║
██╔═══╝ ██╔═██╗ ╚════██║   ██║      ██╔══██║██║
{blue_color}██║     ██║  ██╗███████║   ██║      ██║  ██║██║
╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝      ╚═╝  ╚═╝╚═╝{reset_color}"""
    print(banner_text)
    print(f"{green_color}───────────────────────── Server is Starting ─────────────────────────{reset_color}")
    print(f"  Local URL:       {white_color}http://127.0.0.1:5000{reset_color}")
    print(f"  Network URL:     {white_color}http://{local_ip}:5000{reset_color}")
    print(f"  AI Provider:     {white_color}{config.get('provider_name', 'None')}{reset_color}")
    print(f"  Model:           {white_color}{config.get('model', 'None')}{reset_color}")
    print(f"  Telegram Bot:    {white_color}{telegram_status}{reset_color}")
    print(f"  Shizuku Status:  {white_color}{shizuku_status}{reset_color}")
    print(f"{green_color}──────────────────────────────────────────────────────────────────────{reset_color}\n")

    # Run Flask
    # Host is 0.0.0.0 so they can access it from their phone browser as well as external devices on local network
    app.run(host='0.0.0.0', port=5000, debug=False)
