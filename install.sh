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

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${ORANGE}Warning: You are running this script as root.${NC}"
    echo -e "TunnelFlare will be installed to /root/.tunnelflare."
    echo -e "If you want to install it for your user, run without sudo (you will be prompted for sudo password only when needed)."
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 3. Create Virtual Environment
echo -e "Creating virtual environment..."
if ! python3 -m venv "$INSTALL_DIR/venv"; then
    echo -e "${ORANGE}Failed to create virtual environment. Attempting to fix...${NC}"
    
    if command -v apt &> /dev/null; then
        # Detect Python version (e.g., 3.11, 3.12)
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "Detected Python $PY_VERSION"
        
        echo -e "Installing python3-venv and python$PY_VERSION-venv (requires sudo)..."
        # Try installing generic and specific version
        if sudo apt update && sudo apt install -y "python3-venv" "python$PY_VERSION-venv"; then
            echo -e "${GREEN}Dependencies installed.${NC}"
        else
            echo -e "${RED}Failed to install python3-venv packages via apt.${NC}"
        fi
        
        # Retry venv creation
        echo -e "Retrying virtual environment creation..."
        if ! python3 -m venv "$INSTALL_DIR/venv"; then
             echo -e "${RED}Still unable to create virtual environment.${NC}"
             echo -e "Please try running the following command manually:"
             echo -e "  sudo apt install python3-venv python$PY_VERSION-venv"
             exit 1
        fi
    else
        echo -e "${RED}python3-venv is missing and 'apt' is not available.${NC}"
        echo -e "Please install python3-venv manually using your package manager."
        exit 1
    fi
fi

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
