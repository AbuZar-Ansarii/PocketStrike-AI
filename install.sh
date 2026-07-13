#!/usr/bin/env bash

# PocketstrikeAI Installer Script for Termux
# Designed to set up the environment and dependencies.

# Exit immediately if a command exits with a non-zero status
set -e

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}==================================================${NC}"
echo -e "${GREEN}          PocketstrikeAI Installer                ${NC}"
echo -e "${CYAN}==================================================${NC}"
echo -e "Starting installation for Termux on Android...\n"

# 1. Update package lists
echo -e "${BLUE}[1/4] Updating package repositories...${NC}"
if [ -x "$(command -v pkg)" ]; then
    pkg update -y || echo -e "${YELLOW}Warning: pkg update failed, trying to proceed...${NC}"
else
    echo -e "${RED}Error: This installer is designed for Termux (pkg package manager not found).${NC}"
    exit 1
fi

# 2. Install Python and Git
echo -e "\n${BLUE}[2/4] Installing Python and Git...${NC}"
pkg install -y python git || {
    echo -e "${RED}Error: Failed to install python and git. Please check your internet connection or Termux repositories.${NC}"
    exit 1
}

# 3. Upgrade pip and install Flask and Requests
echo -e "\n${BLUE}[3/4] Installing Python dependencies (Flask, Requests)...${NC}"
python -m pip install --upgrade pip
pip install flask requests

# 4. Make scripts executable
echo -e "\n${BLUE}[4/4] Setting execution permissions...${NC}"
if [ -f "launch.sh" ]; then
    chmod +x launch.sh
    echo -e "${GREEN}launch.sh is now executable.${NC}"
else
    echo -e "${YELLOW}Warning: launch.sh not found in the current directory.${NC}"
fi

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}      Installation Completed Successfully!        ${NC}"
echo -e "${CYAN}==================================================${NC}"
echo -e "You can now start the setup wizard and launch the AI."
echo -e "To start, run: ${YELLOW}./launch.sh${NC}"
echo -e "${CYAN}==================================================${NC}"
