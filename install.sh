#!/bin/bash

# TunnelFlare v2.0 Global Installer
# Installs TunnelFlare to ~/.tunnelflare and creates a binary in ~/.local/bin
# Supports Modern TUI, Hybrid Web Mesh Control Plane, and Remote Enrollment.

set -e

INSTALL_DIR="$HOME/.tunnelflare"
BIN_DIR="$HOME/.local/bin"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse optional arguments for headless mesh joining
JOIN_MESH=false
SITE_NAME=""
ACCOUNT_TOKEN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --join-mesh|--mesh)
            JOIN_MESH=true
            shift
            ;;
        --site)
            SITE_NAME="$2"
            shift 2
            ;;
        --token)
            ACCOUNT_TOKEN="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${ORANGE}Installing TunnelFlare v2.0 (Zero Trust Hybrid Mesh & TUI)...${NC}"

# Check if running as root via sudo (drop privileges to real user)
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo -e "${ORANGE}Detected sudo usage. Dropping privileges to install for user '$SUDO_USER'...${NC}"
    exec sudo -u "$SUDO_USER" bash -c "export HOME=/home/$SUDO_USER; $0 $*"
    exit 0
fi

# Check if running as real root
if [ "$EUID" -eq 0 ] && [ -z "$SUDO_USER" ]; then
    echo -e "${ORANGE}Warning: You are running this script as root.${NC}"
    echo -e "TunnelFlare will be installed to /root/.tunnelflare."
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. Preserve Existing Config and State
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${ORANGE}Updating existing installation at $INSTALL_DIR...${NC}"
    if [ -f "$INSTALL_DIR/config.yml" ]; then
        cp "$INSTALL_DIR/config.yml" /tmp/tunnelflare_config_backup.yml
    fi
    if [ -f "$INSTALL_DIR/account.json" ]; then
        cp "$INSTALL_DIR/account.json" /tmp/tunnelflare_account_backup.json
    fi
    if [ -f "$INSTALL_DIR/tunnel.pid" ]; then
        cp "$INSTALL_DIR/tunnel.pid" /tmp/tunnelflare_pid_backup
    fi
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# 2. Copy Code & Web Assets
echo -e "Copying application files..."
cp "$REPO_DIR"/main.py "$INSTALL_DIR/"
cp "$REPO_DIR"/tui.py "$INSTALL_DIR/"
cp "$REPO_DIR"/utils.py "$INSTALL_DIR/"
cp "$REPO_DIR"/cloudflare_api.py "$INSTALL_DIR/"
cp "$REPO_DIR"/web_server.py "$INSTALL_DIR/"
cp "$REPO_DIR"/requirements.txt "$INSTALL_DIR/"

if [ -d "$REPO_DIR/resources" ]; then
    cp -r "$REPO_DIR/resources" "$INSTALL_DIR/"
fi

# Copy or compile Web Mesh frontend assets
mkdir -p "$INSTALL_DIR/web"
if [ -d "$REPO_DIR/web/dist" ]; then
    echo -e "${GREEN}Copying pre-built Web Mesh dashboard assets...${NC}"
    cp -r "$REPO_DIR/web/dist" "$INSTALL_DIR/web/"
elif [ -d "$REPO_DIR/web" ] && command -v npm &> /dev/null; then
    echo -e "${CYAN}Building Web Mesh dashboard frontend (npm run build)...${NC}"
    npm --prefix "$REPO_DIR/web" install
    npm --prefix "$REPO_DIR/web" run build
    cp -r "$REPO_DIR/web/dist" "$INSTALL_DIR/web/"
fi

# Restore configurations and credentials
if [ -f /tmp/tunnelflare_config_backup.yml ]; then
    echo -e "Restoring configuration..."
    mv /tmp/tunnelflare_config_backup.yml "$INSTALL_DIR/config.yml"
    chmod 600 "$INSTALL_DIR/config.yml"
fi
if [ -f /tmp/tunnelflare_account_backup.json ]; then
    echo -e "Restoring Zero Trust account credentials..."
    mv /tmp/tunnelflare_account_backup.json "$INSTALL_DIR/account.json"
    chmod 600 "$INSTALL_DIR/account.json"
fi
if [ -f /tmp/tunnelflare_pid_backup ]; then
    mv /tmp/tunnelflare_pid_backup "$INSTALL_DIR/tunnel.pid"
fi

# 3. Create Virtual Environment
echo -e "Creating virtual environment..."
if ! python3 -m venv "$INSTALL_DIR/venv"; then
    echo -e "${ORANGE}Failed to create virtual environment. Attempting to fix...${NC}"
    if command -v apt &> /dev/null; then
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "Detected Python $PY_VERSION. Installing python3-venv..."
        sudo apt update && sudo apt install -y "python3-venv" "python$PY_VERSION-venv"
        python3 -m venv "$INSTALL_DIR/venv"
    else
        echo -e "${RED}python3-venv is missing. Please install python3-venv manually.${NC}"
        exit 1
    fi
fi

# 4. Install Python Dependencies
echo -e "Installing Python dependencies (FastAPI, Uvicorn, Rich, Textual, Requests)..."
"$INSTALL_DIR/venv/bin/pip" install --default-timeout=300 --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --default-timeout=300 -r "$INSTALL_DIR/requirements.txt" httpx

# 5. Check & Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${ORANGE}cloudflared not found. Installing...${NC}"
    
    ARCH=$(python3 -c "import platform; m=platform.machine().lower(); print('amd64' if m in ('x86_64','amd64') else ('arm64' if m in ('aarch64','arm64') else ('armhf' if 'arm' in m else '386')))")
    mkdir -p "$BIN_DIR"
    BIN_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}"
    echo -e "Downloading cloudflared for ${ARCH} into $BIN_DIR..."
    if wget -q -O "$BIN_DIR/cloudflared" "$BIN_URL" && chmod +x "$BIN_DIR/cloudflared"; then
        echo -e "${GREEN}cloudflared installed successfully to $BIN_DIR/cloudflared!${NC}"
    else
        DEB_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
        wget -q -O /tmp/cloudflared.deb "$DEB_URL" || true
        if [ -f /tmp/cloudflared.deb ]; then
            sudo dpkg -i /tmp/cloudflared.deb || true
            rm -f /tmp/cloudflared.deb
        fi
    fi
else
    echo -e "${GREEN}cloudflared is already installed.${NC}"
fi

# 6. Create Wrapper Script
echo -e "Creating executable wrapper..."
cat << 'EOF' > "$INSTALL_DIR/tunnelflare"
#!/bin/bash
INSTALL_DIR="$HOME/.tunnelflare"
source "$INSTALL_DIR/venv/bin/activate"
python3 "$INSTALL_DIR/main.py" "$@"
EOF

chmod +x "$INSTALL_DIR/tunnelflare"

# 7. Link to PATH
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/tunnelflare" "$BIN_DIR/tunnelflare"

# 8. Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${ORANGE}Warning: $BIN_DIR is not in your PATH.${NC}"
    SHELL_RC=""
    if [ -n "$BASH_VERSION" ] || [ -n "$BASH" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ] || [ -n "$ZSH_NAME" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo "# TunnelFlare PATH" >> "$SHELL_RC"
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
        echo -e "${GREEN}Added to $SHELL_RC.${NC}"
        echo -e "${ORANGE}Please restart your terminal or run: source $SHELL_RC${NC}"
    fi
fi

# 9. Handle Remote Enrollment if Flags Provided
if [ "$JOIN_MESH" = true ]; then
    echo -e "\n${CYAN}Configuring mesh enrollment...${NC}"
    LOGIN_ARGS=()
    if [ -n "$ACCOUNT_TOKEN" ]; then
        LOGIN_ARGS+=(--token "$ACCOUNT_TOKEN")
    fi
    if [ -n "$SITE_NAME" ]; then
        LOGIN_ARGS+=(--site "$SITE_NAME")
    fi
    "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/main.py" account login "${LOGIN_ARGS[@]}" || true
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}   TunnelFlare v2.0 Installation Complete! 🎉        ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Available Commands:"
echo -e "  ${CYAN}tunnelflare status${NC}      Open Interactive Terminal HUD"
echo -e "  ${CYAN}tunnelflare web${NC}         Launch Web Mesh Topology & Map (http://localhost:8080)"
echo -e "  ${CYAN}tunnelflare account login${NC} Link Cloudflare Zero Trust Account"
echo -e "  ${CYAN}tunnelflare mesh list${NC}    View discovered tunnels & CIDR routes"
echo -e "  ${CYAN}tunnelflare setup${NC}        Standard Tunnel Setup Wizard"
echo -e "  ${CYAN}tunnelflare start${NC}        Start tunnel in background"
echo -e "  ${CYAN}tunnelflare stop${NC}         Stop background tunnel"
echo ""
