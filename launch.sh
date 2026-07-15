#!/usr/bin/env bash

# PocketstrikeAI Launcher Script for Termux
# Shows a menu to configure or start the server.

# Colors (UI-Matching Cyber Theme)
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PINK='\033[1;35m' # UI Matching Pink/Magenta
NC='\033[0m' # No Color

show_menu() {
    clear
    # Check if config.json exists
    if [ -f "config.json" ]; then
        SETUP_STATUS="${CYAN}[ Configured ]${NC}"
        CONFIG_EXISTS=true
    else
        SETUP_STATUS="${RED}[ Unconfigured ]${NC}"
        CONFIG_EXISTS=false
    fi

    echo -e "${PINK}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${NC}"
    echo -e "${CYAN}██░▄▄▄░██░▄▄░██░▄▄▄██░▀██░██░▄▄▀██░████░▄▄▀██░███░██${NC}"
    echo -e "${CYAN}██░███░██░▀▀░██░▄▄▄██░█░█░██░█████░████░▀▀░██░█░█░██${NC}"
    echo -e "${CYAN}██░▀▀▀░██░█████░▀▀▀██░██▄░██░▀▀▄██░▀▀░█░██░██▄▀▄▀▄██${NC}"
    echo -e "${PINK}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀${NC}"
    echo -e "🤳 ${CYAN}POCKETSTRIKE AI  ─  LAUNCHER DASHBOARD${NC} 🤳"
    echo -e "${PINK}───────────────────────────────────────────────────${NC}"
    echo -e " Status: $SETUP_STATUS"
    
    if [ "$CONFIG_EXISTS" = true ]; then
        INFO=$(python -c '
import json
try:
    with open("config.json") as f:
        cfg = json.load(f)
        print(f"{cfg.get(\"provider_name\", \"Unknown\").upper()} ({cfg.get(\"model\", \"Unknown\")})")
except Exception:
    print("Invalid Configuration")
' 2>/dev/null)
        echo -e " Active Model: ${CYAN}${INFO}${NC}"
    fi
    echo -e "${PINK}───────────────────────────────────────────────────${NC}"
    echo -e " Please choose an option:\n"
    echo -e "  [1] Run Interactive Setup Wizard"
    echo -e "  [2] Launch PocketstrikeAI Server & Bot"
    echo -e "  [3] Exit"
    echo -e "\n${PINK}───────────────────────────────────────────────────${NC}"
}

run_setup() {
    python setup.py
    echo -e "\nPress Enter to return to menu..."
    read -r
}

launch_server() {
    if [ ! -f "config.json" ]; then
        echo -e "\n${RED}Error: Setup is not completed yet!${NC}"
        echo -e "Please run the Setup Wizard (Option 1) first."
        echo -e "\nWould you like to run it now? (y/n): "
        read -r choice
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            run_setup
        fi
        return
    fi

    echo -e "\n${CYAN}Starting PocketstrikeAI Server...${NC}"
    python server.py
}

while true; do
    show_menu
    echo -n "Enter choice [1-3]: "
    read -r opt
    case $opt in
        1)
            run_setup
            ;;
        2)
            launch_server
            break
            ;;
        3)
            echo -e "\n${BLUE}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid option. Press Enter to try again.${NC}"
            read -r
            ;;
    esac
done
