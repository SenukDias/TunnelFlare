#!/bin/bash

# Build Script for TunnelFlare v2.0 .deb Package
# Requires: pyinstaller, dpkg-deb, node/npm (for web dashboard)

set -e

APP_NAME="tunnelflare"
VERSION="2.0.0"
ARCH=$(dpkg --print-architecture)
BUILD_DIR="build_deb"
PACKAGE_DIR="${APP_NAME}_${VERSION}_${ARCH}"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
ORANGE='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Build Process for $APP_NAME v$VERSION ($ARCH)...${NC}"

# 1. Build React Web Mesh Frontend
if [ -d "web" ]; then
    echo -e "${CYAN}Building production Web Mesh frontend assets...${NC}"
    if command -v npm &> /dev/null; then
        npm --prefix web install
        npm --prefix web run build
    else
        echo -e "${ORANGE}Warning: npm not found. Using existing web/dist if available.${NC}"
    fi
fi

# 2. Setup Build Environment (Venv)
echo -e "${GREEN}Setting up build environment...${NC}"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt httpx pyinstaller

# 3. Build Executable with PyInstaller
echo -e "${GREEN}Building binary with PyInstaller...${NC}"
ADD_DATA_ARGS=(
    --add-data "tui.py:."
    --add-data "utils.py:."
    --add-data "cloudflare_api.py:."
    --add-data "web_server.py:."
)

if [ -d "web/dist" ]; then
    ADD_DATA_ARGS+=(--add-data "web/dist:web/dist")
fi
if [ -d "resources" ]; then
    ADD_DATA_ARGS+=(--add-data "resources:resources")
fi

pyinstaller --onefile --name "$APP_NAME" \
    "${ADD_DATA_ARGS[@]}" \
    --collect-all "rich" \
    --collect-all "textual" \
    --collect-all "typer" \
    --collect-all "fastapi" \
    --collect-all "uvicorn" \
    --collect-all "pydantic" \
    --collect-all "starlette" \
    --collect-all "requests" \
    --hidden-import "yaml" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan.on" \
    main.py

if [ ! -f "dist/$APP_NAME" ]; then
    echo "Build failed! Executable not found in dist/"
    exit 1
fi

# 4. Create Debian Package Structure
echo -e "${GREEN}Creating Debian package structure...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/$PACKAGE_DIR/usr/share/doc/$APP_NAME"

# Copy Binary
cp "dist/$APP_NAME" "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin/"
chmod 755 "$BUILD_DIR/$PACKAGE_DIR/usr/local/bin/$APP_NAME"

# Copy README
if [ -f "README.md" ]; then
    cp README.md "$BUILD_DIR/$PACKAGE_DIR/usr/share/doc/$APP_NAME/"
fi

# 5. Create Control File
echo -e "${GREEN}Creating control file...${NC}"
cat << EOF > "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Section: net
Priority: optional
Architecture: $ARCH
Maintainer: TunnelFlare Team <support@tunnelflare.io>
Description: Cloudflare Zero Trust Hybrid Web Mesh & Modern TUI Orchestrator
 TunnelFlare v2.0 automates Cloudflare Tunnel setup and site-to-site Zero Trust
 mesh routing. Features an interactive React Flow topology canvas, Leaflet dark
 world map, and high-fidelity retro terminal HUD.
EOF

# 6. Create Post-Install Script
echo -e "${GREEN}Creating postinst script...${NC}"
cat << 'EOF' > "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/postinst"
#!/bin/bash
set -e

# Check & Install cloudflared if missing
if ! command -v cloudflared &> /dev/null; then
    echo "TunnelFlare: cloudflared not found. Installing..."
    ARCH=$(dpkg --print-architecture)
    URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
    if wget -q -O /tmp/cloudflared.deb "$URL" 2>/dev/null; then
        dpkg -i /tmp/cloudflared.deb || true
        rm -f /tmp/cloudflared.deb
        echo "TunnelFlare: cloudflared installed successfully."
    else
        echo "TunnelFlare: Could not download cloudflared deb for $ARCH. Please install manually."
    fi
fi

# Ensure user config directory exists with 700 permissions
if [ -n "$SUDO_USER" ]; then
    mkdir -p "/home/$SUDO_USER/.tunnelflare"
    chown "$SUDO_USER:$SUDO_USER" "/home/$SUDO_USER/.tunnelflare"
    chmod 700 "/home/$SUDO_USER/.tunnelflare"
fi

echo "TunnelFlare v2.0 installed successfully!"
echo "Run 'tunnelflare status' for TUI or 'tunnelflare web' for Web Mesh Dashboard."
EOF

chmod 755 "$BUILD_DIR/$PACKAGE_DIR/DEBIAN/postinst"

# 7. Build .deb Package
echo -e "${GREEN}Building .deb package with dpkg-deb...${NC}"
dpkg-deb --build "$BUILD_DIR/$PACKAGE_DIR"

# Move deb package to root
mv "$BUILD_DIR/$PACKAGE_DIR.deb" .
echo -e "${GREEN}Package created: $PACKAGE_DIR.deb${NC}"

# Cleanup temporary build dirs
rm -rf "$BUILD_DIR"
rm -rf "build"
rm -rf "dist"
rm -rf "$APP_NAME.spec"

echo -e "\n${GREEN}Build Complete! Package: $PACKAGE_DIR.deb${NC}"
