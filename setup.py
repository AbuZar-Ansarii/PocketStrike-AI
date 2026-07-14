#!/usr/bin/env python3
import json
import os
import sys

# Define colors for CLI terminal (matching green/white UI theme)
GREEN = "\033[38;5;46m"
WHITE = "\033[38;5;255m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

BANNER = f"""{GREEN}██████╗ ██╗  ██╗███████╗████████╗    █████╗ ██╗
██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝   ██╔══██╗██║
{WHITE}██████╔╝█████╔╝ ███████╗   ██║      ███████║██║
██╔═══╝ ██╔═██╗ ╚════██║   ██║      ██╔══██║██║
██║     ██║  ██╗███████║   ██║      ██║  ██║██║
╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝      ╚═╝  ╚═╝╚═╝{NC}"""

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def print_header():
    clear_screen()
    print(BANNER)
    print(f"{GREEN}──────────────────────────────────────────────────────────────────────────{NC}\n")

def get_input(prompt, default=None, is_password=False):
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{prompt}{suffix}: ").strip()
        if not val and default:
            return default
        return val
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}Setup cancelled.{NC}")
        sys.exit(0)

def main():
    print_header()
    
    # 1. AI Providers List
    providers = [
        {"name": "Google Gemini", "id": "gemini"},
        {"name": "OpenAI", "id": "openai"},
        {"name": "Anthropic Claude", "id": "anthropic"},
        {"name": "Ollama (Local AI)", "id": "ollama"},
        {"name": "OpenRouter", "id": "openrouter"},
        {"name": "OpenCode", "id": "opencode"},
        {"name": "OpenCode Zen", "id": "opencode_zen"},
        {"name": "Custom API (OpenAI Compatible)", "id": "custom"}
    ]

    print(f"{YELLOW}Select your AI Provider:{NC}")
    for idx, p in enumerate(providers, 1):
        print(f"  [{idx}] {p['name']}")
    print("")

    while True:
        choice = get_input("Enter choice (1-8)", "1")
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(providers):
                selected_provider = providers[choice_idx]
                break
        except ValueError:
            pass
        print(f"{RED}Invalid selection. Please enter a number between 1 and 8.{NC}")

    provider_id = selected_provider["id"]
    provider_name = selected_provider["name"]
    print(f"\n{GREEN}Selected Provider: {provider_name}{NC}\n")

    # 2. Base URL & API Key configuration
    api_key = ""
    base_url = ""

    if provider_id == "gemini":
        print(f"{BLUE}Gemini API setup requires a Google AI Studio API key.{NC}")
        api_key = get_input("Enter Google Gemini API Key")
    elif provider_id == "openai":
        api_key = get_input("Enter OpenAI API Key")
        base_url = "https://api.openai.com/v1"
    elif provider_id == "anthropic":
        api_key = get_input("Enter Anthropic API Key")
        base_url = "https://api.anthropic.com/v1"
    elif provider_id == "ollama":
        print(f"{BLUE}Ollama configured automatically for local models (http://localhost:11434).{NC}")
        base_url = "http://localhost:11434"
    elif provider_id == "openrouter":
        api_key = get_input("Enter OpenRouter API Key")
        base_url = "https://openrouter.ai/api/v1"
    elif provider_id == "opencode":
        print(f"{BLUE}OpenCode Go API uses OpenAI-compatible format.{NC}")
        api_key = get_input("Enter OpenCode API Key")
        base_url = "https://opencode.ai/zen/go/v1"
    elif provider_id == "opencode_zen":
        print(f"{BLUE}OpenCode Zen API uses OpenAI-compatible format.{NC}")
        api_key = get_input("Enter OpenCode Zen API Key")
        base_url = "https://opencode.ai/zen/v1"
    elif provider_id == "custom":
        base_url = get_input("Enter Custom API Base URL (e.g. https://api.myllm.com/v1)")
        api_key = get_input("Enter API Key (press Enter if none)")

    # 3. Model selection based on provider
    models_dict = {
        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "ollama": ["llama3", "phi3", "mistral", "gemma", "gemma4:31b-cloud", "gemini-3-flash-preview:cloud"],
        "openrouter": ["meta-llama/llama-3-8b-instruct:free", "mistralai/mistral-7b-instruct:free", "google/gemma-2-9b-it:free"],
        "opencode": ["gpt-5.2", "gpt-5.1-codex", "claude-opus-4.5", "claude-sonnet-4.5", "gemini-3-pro"],
        "opencode_zen": ["big-pickle", "mimo", "deepseek-v3", "deepseek-v4-flash-free"],
        "custom": []
    }

    selected_model = ""
    provider_models = models_dict.get(provider_id, [])

    if provider_models:
        print(f"\n{YELLOW}Select AI Model for {provider_name}:{NC}")
        for idx, m in enumerate(provider_models, 1):
            print(f"  [{idx}] {m}")
        print(f"  [{len(provider_models) + 1}] Custom Model (Enter manually)")
        print("")
        
        while True:
            choice = get_input("Enter choice", "1")
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(provider_models):
                    selected_model = provider_models[choice_idx]
                    break
                elif choice_idx == len(provider_models):
                    selected_model = get_input("Enter Custom Model Name")
                    break
            except ValueError:
                pass
            print(f"{RED}Invalid selection.{NC}")
    else:
        # Custom API has no predefined models
        selected_model = get_input("Enter Model Name (e.g. my-custom-model)")

    print(f"\n{GREEN}Selected Model: {selected_model}{NC}\n")

    # 4. Telegram Integration
    telegram_enabled = False
    telegram_token = ""
    
    print(f"{YELLOW}Telegram Bot Integration:{NC}")
    tg_choice = get_input("Do you want to enable Telegram Bot support? (y/n)", "n").lower()
    if tg_choice in ["y", "yes"]:
        telegram_enabled = True
        telegram_token = get_input("Enter Telegram Bot Token (from @BotFather)")
        if not telegram_token:
            print(f"{YELLOW}Warning: Telegram token was empty, disabling Telegram support.{NC}")
            telegram_enabled = False

    # 5. Shizuku Phone Control Setup
    shizuku_enabled = False
    print(f"\n{YELLOW}Shizuku Phone Remote Control Setup:{NC}")
    sz_choice = get_input("Do you want to enable Shizuku phone remote control? (y/n)", "y").lower()
    
    if sz_choice in ["y", "yes"]:
        import shutil
        rish_path = shutil.which("rish")
        
        if rish_path:
            print(f"{GREEN}[✓] Shizuku 'rish' client is already installed in your Termux PATH.{NC}")
            shizuku_enabled = True
        else:
            print(f"{BLUE}Checking for Shizuku exported files in phone storage and downloads...{NC}")
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
                            
                        print(f"{GREEN}[✓] Shizuku 'rish' successfully auto-installed to your Termux bin path: {termux_bin}!{NC}")
                        print(f"{BLUE}Note: When you run the server and send the first command, tap 'Always Allow' on the Shizuku popup.{NC}")
                        shizuku_enabled = True
                except Exception as e:
                    print(f"{RED}Failed to auto-install Shizuku rish files: {e}{NC}")
            else:
                print(f"{RED}[!] Could not find exported Shizuku files in downloads or storage.{NC}")
                print(f"{YELLOW}To set up Shizuku phone control, please:{NC}")
                print(f"  1. Open the Shizuku App on your phone.")
                print(f"  2. Tap 'Use Shizuku in terminal apps' -> 'Export files'.")
                print(f"  3. Save the files to your phone's main storage, Downloads folder, or directly into the project directory ({os.path.dirname(__file__)}).")
                print(f"  4. Grant Termux storage access by running 'termux-setup-storage' in Termux.")
                print(f"  5. Run this setup wizard again or let the server auto-detect it later.")
                get_input("Press Enter to continue with setup", "")

    # 6. Build and save the config object
    config = {
        "provider": provider_id,
        "provider_name": provider_name,
        "api_key": api_key,
        "base_url": base_url,
        "model": selected_model,
        "telegram_enabled": telegram_enabled,
        "telegram_token": telegram_token,
        "shizuku_enabled": shizuku_enabled
    }

    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        print_header()
        print(f"{GREEN}Success! Configuration saved to config.json.{NC}\n")
        print(f"{CYAN}Configuration Summary:{NC}")
        print(f"  AI Provider:     {provider_name}")
        print(f"  Model:           {selected_model}")
        if api_key:
            print(f"  API Key:         {'*' * 8}{api_key[-4:] if len(api_key) > 4 else ''}")
        else:
            print(f"  API Key:         None (or Local)")
        if base_url:
            print(f"  Base URL:        {base_url}")
        print(f"  Telegram Bot:    {'Enabled' if telegram_enabled else 'Disabled'}")
        if telegram_enabled:
            print(f"  TG Token:        {'*' * 8}{telegram_token[-4:] if len(telegram_token) > 4 else ''}")
        print(f"  Shizuku Control: {'Enabled/Configured' if shizuku_enabled else 'Disabled/Not Configured'}")
        print(f"\n{GREEN}PocketstrikeAI is ready to be launched!{NC}")
        print(f"Run {YELLOW}./launch.sh{NC} and choose option 2 to launch.")
        print(f"{CYAN}=================================================={NC}")
    except Exception as e:
        print(f"\n{RED}Error saving configuration: {e}{NC}")

if __name__ == "__main__":
    main()
