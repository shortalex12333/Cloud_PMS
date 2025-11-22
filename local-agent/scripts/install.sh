#!/bin/bash
# CelesteOS Local Agent Installation Script
# macOS 12.0+ required

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

INSTALL_DIR="$HOME/.celesteos"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   CelesteOS Local Agent Installer      ║${NC}"
echo -e "${CYAN}║   Yacht Document Sync Service          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This installer is for macOS only${NC}"
    exit 1
fi

echo -e "${CYAN}[1/7] Checking system requirements...${NC}"

# Check Python 3.9+
PYTHON_CMD=""
for cmd in python3.11 python3.10 python3.9 python3; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd --version 2>&1 | awk '{print $2}')
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python 3.9+ required but not found${NC}"
    echo "Install Python from: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}  ✓ Python: $PYTHON_CMD ($VERSION)${NC}"
echo ""

# Create directories
echo -e "${CYAN}[2/7] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/tmp"
mkdir -p "$INSTALL_DIR/bin"
echo -e "${GREEN}  ✓ $INSTALL_DIR created${NC}"
echo ""

# Copy agent files
echo -e "${CYAN}[3/7] Installing agent files...${NC}"
cp -r "$SCRIPT_DIR/celesteos_agent" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/celesteos_daemon.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/celesteos_cli.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/schema.sql" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/config.example.json" "$INSTALL_DIR/"
echo -e "${GREEN}  ✓ Agent files installed to $INSTALL_DIR${NC}"
echo ""

# Install Python dependencies
echo -e "${CYAN}[4/7] Installing Python dependencies...${NC}"
cd "$INSTALL_DIR"
$PYTHON_CMD -m pip install --user -q -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}  Note: Some dependencies may need Xcode Command Line Tools${NC}"
    $PYTHON_CMD -m pip install --user -r requirements.txt
}
echo -e "${GREEN}  ✓ Dependencies installed${NC}"
echo ""

# Make scripts executable and create wrapper scripts
echo -e "${CYAN}[5/7] Creating command-line tools...${NC}"
chmod +x "$INSTALL_DIR/celesteos_daemon.py"
chmod +x "$INSTALL_DIR/celesteos_cli.py"

# Create wrapper scripts in bin
cat > "$INSTALL_DIR/bin/celesteos-agent" << 'WRAPPER'
#!/bin/bash
cd ~/.celesteos
python3 celesteos_cli.py "$@"
WRAPPER
chmod +x "$INSTALL_DIR/bin/celesteos-agent"

cat > "$INSTALL_DIR/bin/celesteos-daemon" << 'WRAPPER'
#!/bin/bash
cd ~/.celesteos
python3 celesteos_daemon.py "$@"
WRAPPER
chmod +x "$INSTALL_DIR/bin/celesteos-daemon"

# Add to PATH if not already
if [[ ":$PATH:" != *":$INSTALL_DIR/bin:"* ]]; then
    echo ""
    echo -e "${YELLOW}  Add to your ~/.zshrc or ~/.bash_profile:${NC}"
    echo -e "  ${CYAN}export PATH=\"\$HOME/.celesteos/bin:\$PATH\"${NC}"
fi
echo -e "${GREEN}  ✓ Commands ready: celesteos-agent, celesteos-daemon${NC}"
echo ""

# Initialize database
echo -e "${CYAN}[6/7] Initializing database...${NC}"
cd "$INSTALL_DIR"
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from celesteos_agent.database import Database
from pathlib import Path
db = Database('$INSTALL_DIR/celesteos.db')
db.init(Path('$INSTALL_DIR/schema.sql'))
print('  Database initialized')
" 2>/dev/null || {
    echo -e "${YELLOW}  Database will be initialized on first run${NC}"
}
echo -e "${GREEN}  ✓ Database ready${NC}"
echo ""

# Install launchd service
echo -e "${CYAN}[7/7] Installing background service...${NC}"

# Create launchd plist with correct paths
PLIST_PATH="$HOME/Library/LaunchAgents/com.celesteos.agent.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.celesteos.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_CMD</string>
        <string>$INSTALL_DIR/celesteos_daemon.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/daemon-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/daemon-stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>Disabled</key>
    <false/>
</dict>
</plist>
PLIST
echo -e "${GREEN}  ✓ LaunchAgent installed${NC}"
echo ""

# Final summary
echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      Installation Complete!            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Files installed to: $INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "  1. Run the setup wizard:"
echo -e "     ${CYAN}cd ~/.celesteos && python3 celesteos_cli.py setup${NC}"
echo ""
echo "  2. Start the background agent:"
echo -e "     ${CYAN}launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist${NC}"
echo ""
echo "  3. Check status:"
echo -e "     ${CYAN}cd ~/.celesteos && python3 celesteos_cli.py status${NC}"
echo ""
echo -e "${YELLOW}Commands (add ~/.celesteos/bin to PATH):${NC}"
echo "  celesteos-agent setup   - Configure yacht & NAS"
echo "  celesteos-agent status  - Check sync status"
echo "  celesteos-agent logs    - View recent logs"
echo ""
