#!/usr/bin/env bash

# PocketstrikeAI Launcher Script for Termux
# Shows a menu to configure or start the server.

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
TERM_GREEN='\033[38;5;46m'
TERM_WHITE='\033[38;5;255m'
NC='\033[0m' # No Color

show_menu() {
    clear
    # Check if config.json exists
    if [ -f "config.json" ]; then
        SETUP_CHECK="${GREEN}[✓]${NC}"
        CONFIG_EXISTS=true
    else
        SETUP_CHECK="${RED}[ ]${NC}"
        CONFIG_EXISTS=false
    fi

    echo -e "${TERM_GREEN}██████╗ ██╗  ██╗███████╗████████╗    █████╗ ██╗${NC}"
    echo -e "${TERM_GREEN}██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝   ██╔══██╗██║${NC}"
    echo -e "${TERM_WHITE}██████╔╝█████╔╝ ███████╗   ██║      ███████║██║${NC}"
    echo -e "${TERM_WHITE}██╔═══╝ ██╔═██╗ ╚════██║   ██║      ██╔══██║██║${NC}"
    echo -e "${TERM_WHITE}██║     ██║  ██╗███████║   ██║      ██║  ██║██║${NC}"
    echo -e "${TERM_WHITE}╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝      ╚═╝  ╚═╝╚═╝${NC}"
    echo -e "${TERM_GREEN}─────────────────────────────── Dashboard ────────────────────────────────${NC}"
    echo -e " Please choose an option:\n"
    echo -e "  ${SETUP_CHECK} 1. Run Setup Wizard"
    echo -e "      2. Launch PocketstrikeAI Server & Bot"
    echo -e "      3. Exit"
    echo -e "${TERM_GREEN}──────────────────────────────────────────────────────────────────────────${NC}"
    
    if [ "$CONFIG_EXISTS" = true ]; then
        # Read provider and model from config.json (using simple python command to avoid installing jq)
        INFO=$(python -c '
import json, sys
try:
    with open("config.json") as f:
        cfg = json.load(f)
        print(f"{cfg.get(\"provider_name\", \"Unknown\")} ({cfg.get(\"model\", \"Unknown\")})")
except Exception:
    print("Invalid Config")
' 2>/dev/null)
        echo -e "Current Config: ${GREEN}${INFO}${NC}"
        echo -e "${CYAN}--------------------------------------------------${NC}"
    fi
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

    echo -e "\n${GREEN}Starting PocketstrikeAI...${NC}"
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
