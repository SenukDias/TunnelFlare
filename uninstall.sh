#!/bin/bash

# TunnelFlare Uninstaller

INSTALL_DIR="$HOME/.tunnelflare"
BIN_FILE="$HOME/.local/bin/tunnelflare"

# Colors
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${ORANGE}Uninstalling TunnelFlare...${NC}"

# 1. Remove Installation Directory
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "Removed installation directory: $INSTALL_DIR"
else
    echo -e "${ORANGE}Installation directory not found: $INSTALL_DIR${NC}"
fi

# 2. Remove Binary Symlink
if [ -f "$BIN_FILE" ] || [ -L "$BIN_FILE" ]; then
    rm "$BIN_FILE"
    echo -e "Removed executable: $BIN_FILE"
else
    echo -e "${ORANGE}Executable not found: $BIN_FILE${NC}"
fi

echo -e "${GREEN}Uninstall Complete!${NC}"
echo -e "TunnelFlare has been removed from your system."
