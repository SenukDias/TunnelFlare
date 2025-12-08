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
    echo -e "${ORANGE}Removing existing installation at $INSTALL_DIR...${NC}"
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# 2. Copy Files
echo -e "Copying files..."
cp -r "$REPO_DIR"/* "$INSTALL_DIR/"

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
