#!/usr/bin/env bash

# PocketstrikeAI Installer Script for Termux
# Designed to set up the environment and dependencies.

# Exit immediately if a command exits with a non-zero status
set -e

# Define colors for output
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PINK='\033[1;35m' # UI Matching Pink/Magenta
NC='\033[0m' # No Color

clear
echo -e "${PINK}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${NC}"
echo -e "${CYAN}█▀▄ █▀█ █▀▀ █▄▀ █▀▀ ▀█▀ █▀▀ ▀█▀ █▀▄ █ █▄▀ █▀▀   ${NC}"
echo -e "${CYAN}█▀▀ █▄█ █▄▄ █ ▀ ██▄  █  ▄██  █  █▀▄ █ █ ▀ ██▄   ${NC}"
echo -e "${PINK}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀${NC}"
echo -e "${CYAN}             🤳 POCKETSTRIKE AI INITIALIZER 🤳          ${NC}"
echo -e "${PINK}-------------------------------------------------------${NC}"
echo -e "🚀 Starting high-performance on-device deployment..."
echo -e "📱 Environment: Termux on Android"
echo -e "${PINK}-------------------------------------------------------${NC}\n"

# 1. Update package lists
echo -e "${BLUE}⚡ [1/4] Syncing Termux package mirrors...${NC}"
if [ -x "$(command -v pkg)" ]; then
    pkg update -y || echo -e "${YELLOW}Warning: pkg update failed, trying to proceed...${NC}"
else
    echo -e "${RED}Error: This installer is designed for Termux (pkg package manager not found).${NC}"
    exit 1
fi

# 2. Install required system and network tools
echo -e "\n${BLUE}⚡ [2/4] Deploying mobile audit toolchain & dependencies...${NC}"
pkg install -y python git termux-api android-tools nmap dnsutils curl net-tools iproute2 traceroute || {
    echo -e "${RED}Error: Failed to install required system packages. Please check your internet connection or Termux repositories.${NC}"
    exit 1
}

# Setup storage access and create workspace directory
echo -e "\n${BLUE}🔐 Granting local storage permissions...${NC}"
termux-setup-storage || echo -e "${YELLOW}Warning: termux-setup-storage failed (not running on Termux?), proceeding anyway...${NC}"
mkdir -p ~/storage/shared/PocketStrike-AI || echo -e "${YELLOW}Warning: Could not create shared storage folder, proceeding...${NC}"

# 3. Clone repository if launch.sh doesn't exist (e.g. running via curl download)
CLONED=false
if [ ! -f "launch.sh" ]; then
    echo -e "\n${BLUE}Cloning PocketstrikeAI repository from GitHub...${NC}"
    git clone https://github.com/AbuZar-Ansarii/PocketStrike-AI.git
    cd PocketStrike-AI || exit 1
    CLONED=true
fi

# 4. Install Flask and Requests
echo -e "\n${BLUE}⚡ [3/4] Installing Python dependency layers...${NC}"
pip install flask requests

# 5. Make scripts executable
echo -e "\n${BLUE}⚡ [4/4] Setting execution system permissions...${NC}"
if [ -f "launch.sh" ]; then
    chmod +x launch.sh
    chmod +x setup.py
    echo -e "${PINK}Scripts are now executable.${NC}"
else
    echo -e "${RED}Error: launch.sh still not found after download!${NC}"
    exit 1
fi

echo -e "\n${PINK}=======================================================${NC}"
echo -e "${CYAN}      ✨ POCKETSTRIKE AI DEPLOYED SUCCESSFULLY! ✨      ${NC}"
echo -e "${PINK}=======================================================${NC}"
echo -e "You can now initialize the setup wizard and launch the AI."
if [ "$CLONED" = true ]; then
    echo -e "To launch, run: ${YELLOW}cd PocketStrike-AI && ./launch.sh${NC}"
else
    echo -e "To launch, run: ${YELLOW}./launch.sh${NC}"
fi
echo -e "${PINK}=======================================================${NC}"
