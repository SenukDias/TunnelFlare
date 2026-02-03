#!/bin/bash

# Build Script for TunnelFlare .deb Package
# Requires: pyinstaller, dpkg-deb

APP_NAME="tunnelflare"
VERSION="1.0.0"
ARCH=$(dpkg --print-architecture)
BUILD_DIR="build_deb"
PACKAGE_DIR="${APP_NAME}_${VERSION}_${ARCH}"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting Build Process for $APP_NAME v$VERSION...${NC}"

# 1. Setup Build Environment (Venv)
echo -e "${GREEN}Setting up build environment...${NC}"

# Ensure we have a venv with dependencies
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# 2. Build Single File Executable
echo -e "${GREEN}Building binary with PyInstaller...${NC}"
pyinstaller --onefile --name "$APP_NAME" \
    --add-data "tui.py:." \
    --add-data "utils.py:." \
    --collect-all "rich" \
    --collect-all "textual" \
    --collect-all "typer" \
    --hidden-import "yaml" \
    main.py

if [ ! -f "dist/$APP_NAME" ]; then
    echo "Build failed!"
    exit 1
fi

# 3. Create Debian Package Structure
echo -e "${GREEN}Creating package structure...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/usr/share/doc/$APP_NAME"

# Copy Binary
cp "dist/$APP_NAME" "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin/"
chmod 755 "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin/$APP_NAME"

# Copy README
cp README.md "$BUILD_DIR/$PACKAGE_DIR/usr/share/doc/$APP_NAME/"

# 4. Create Control File
echo -e "${GREEN}Creating control file...${NC}"
cat << EOF > "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Senuk Dias <senuk@example.com>
Description: Secure Highway to your Private Server
 TunnelFlare is a CLI tool to automate Cloudflare Tunnel setup.
 It features a retro-style TUI, real-time diagnostics, and easy management.
EOF

# 5. Create Post-Install Script (Dependency Check)
echo -e "${GREEN}Creating postinst script...${NC}"
cat << EOF > "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/postinst"
#!/bin/bash
set -e

# Check & Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "TunnelFlare: cloudflared not found. Installing..."
    
    ARCH=\$(dpkg --print-architecture)
    URL=""
    if [ "\$ARCH" = "amd64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    elif [ "\$ARCH" = "arm64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
    elif [ "\$ARCH" = "armhf" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-armhf.deb"
    elif [ "\$ARCH" = "386" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386.deb"
    fi

    if [ -n "\$URL" ]; then
        wget -q -O /tmp/cloudflared.deb "\$URL"
        dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
        echo "TunnelFlare: cloudflared installed successfully."
    else
        echo "TunnelFlare: Could not auto-install cloudflared for \$ARCH. Please install manually."
    fi
fi

# Create config directory with correct permissions
mkdir -p /home/\$SUDO_USER/.tunnelflare
chown \$SUDO_USER:\$SUDO_USER /home/\$SUDO_USER/.tunnelflare
chmod 700 /home/\$SUDO_USER/.tunnelflare

echo "TunnelFlare installed successfully!"
EOF

chmod 755 "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/postinst"

# 6. Build .deb
echo -e "${GREEN}Building .deb package...${NC}"
dpkg-deb --build "$BUILD_DIR/$PACKAGE_DIR"

# Move to root
mv "$BUILD_DIR/$PACKAGE_DIR.deb" .
echo -e "${GREEN}Package created: $PACKAGE_DIR.deb${NC}"

# Cleanup
rm -rf "$BUILD_DIR"
rm -rf "build"
rm -rf "dist"
rm -rf "$APP_NAME.spec"

echo -e "${GREEN}Done! You can now upload $PACKAGE_DIR.deb to GitHub Releases.${NC}"
