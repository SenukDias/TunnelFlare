#!/bin/bash

# TunnelFlare Global Installer
# Installs TunnelFlare to ~/.tunnelflare and creates a binary in ~/.local/bin

INSTALL_DIR="$HOME/.tunnelflare"
BIN_DIR="$HOME/.local/bin"
REPO_DIR="$(pwd)"

# Colors
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${ORANGE}Installing TunnelFlare...${NC}"

# 1. Create Installation Directory
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${ORANGE}Updating existing installation at $INSTALL_DIR...${NC}"
    # Preserve config and state
    if [ -f "$INSTALL_DIR/config.yml" ]; then
        cp "$INSTALL_DIR/config.yml" /tmp/tunnelflare_config_backup.yml
    fi
    if [ -f "$INSTALL_DIR/tunnel.pid" ]; then
        cp "$INSTALL_DIR/tunnel.pid" /tmp/tunnelflare_pid_backup
    fi
    
    # Remove code files but keep venv if possible? 
    # Actually, safer to wipe and restore config to ensure clean code update.
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# Restore backups after copy (will be done after step 2)

# 2. Copy Files
echo -e "Copying files..."
cp -r "$REPO_DIR"/* "$INSTALL_DIR/"

# Restore config and state
if [ -f /tmp/tunnelflare_config_backup.yml ]; then
    echo -e "Restoring configuration..."
    mv /tmp/tunnelflare_config_backup.yml "$INSTALL_DIR/config.yml"
fi
if [ -f /tmp/tunnelflare_pid_backup ]; then
    mv /tmp/tunnelflare_pid_backup "$INSTALL_DIR/tunnel.pid"
fi

# 3. Create Virtual Environment
echo -e "Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"

# 4. Install Dependencies
echo -e "Installing dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --default-timeout=300 --upgrade pip
if ! "$INSTALL_DIR/venv/bin/pip" install -v --default-timeout=300 -r "$INSTALL_DIR/requirements.txt"; then
    echo -e "${RED}Failed to install dependencies. Please check your internet connection and try again.${NC}"
    exit 1
fi

# 5. Check & Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${ORANGE}cloudflared not found. Installing...${NC}"
    
    ARCH=$(dpkg --print-architecture)
    URL=""
    if [ "$ARCH" = "amd64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    elif [ "$ARCH" = "arm64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
    elif [ "$ARCH" = "armhf" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-armhf.deb"
    elif [ "$ARCH" = "386" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386.deb"
    else
        echo -e "${RED}Unsupported architecture: $ARCH. Please install cloudflared manually.${NC}"
    fi

    if [ -n "$URL" ]; then
        echo -e "Downloading cloudflared for $ARCH..."
        wget -q -O /tmp/cloudflared.deb "$URL"
        echo -e "Installing cloudflared (requires sudo)..."
        sudo dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
        
        if command -v cloudflared &> /dev/null; then
            echo -e "${GREEN}cloudflared installed successfully!${NC}"
        else
            echo -e "${RED}Failed to install cloudflared.${NC}"
        fi
    fi
else
    echo -e "${GREEN}cloudflared is already installed.${NC}"
fi

# 5. Create Wrapper Script
echo -e "Creating executable..."
cat << EOF > "$INSTALL_DIR/tunnelflare"
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
python3 "$INSTALL_DIR/main.py" "\$@"
EOF

chmod +x "$INSTALL_DIR/tunnelflare"

# 6. Link to PATH
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/tunnelflare" "$BIN_DIR/tunnelflare"

# 7. Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${ORANGE}Warning: $BIN_DIR is not in your PATH.${NC}"
    echo "Add the following line to your shell configuration file (.bashrc, .zshrc, etc.):"
    echo "export PATH=\"\$PATH:$BIN_DIR\""
fi

echo -e "${GREEN}Installation Complete!${NC}"
echo -e "You can now run TunnelFlare using the command: ${GREEN}tunnelflare${NC}"
