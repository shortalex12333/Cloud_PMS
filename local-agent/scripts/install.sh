#!/bin/bash
# CelesteOS Local Agent Installation Script
# macOS 12.0+ required

set -e

echo "======================================"
echo "CelesteOS Local Agent Installer"
echo "======================================"
echo ""

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This installer is for macOS only"
    exit 1
fi

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
    echo "Error: Python 3.9+ required but not found"
    echo "Install Python from: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Found Python: $PYTHON_CMD ($VERSION)"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p ~/.celesteos/logs
mkdir -p ~/.celesteos/tmp
mkdir -p /Users/Shared/.celesteos/logs
echo "✓ Directories created"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install --user -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Initialize database
echo "Initializing database..."
$PYTHON_CMD -c "from celesteos_agent.database import Database; db = Database(); db.init()"
echo "✓ Database initialized"
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x celesteos_daemon.py
chmod +x celesteos_cli.py
echo "✓ Scripts ready"
echo ""

# Create symlinks
echo "Creating command-line shortcuts..."
sudo ln -sf "$(pwd)/celesteos_daemon.py" /usr/local/bin/celesteos-daemon
sudo ln -sf "$(pwd)/celesteos_cli.py" /usr/local/bin/celesteos-agent
echo "✓ Commands installed: celesteos-daemon, celesteos-agent"
echo ""

# Install launchd service
echo "Installing launchd service..."
cp launchd/com.celesteos.agent.plist ~/Library/LaunchAgents/
echo "✓ Service installed"
echo ""

# Run setup wizard
echo "======================================"
echo "Running Setup Wizard"
echo "======================================"
echo ""

$PYTHON_CMD celesteos_cli.py setup

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the agent:"
echo "   launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist"
echo ""
echo "2. Check status:"
echo "   celesteos-agent status"
echo ""
echo "3. View logs:"
echo "   celesteos-agent logs"
echo ""
echo "4. For help:"
echo "   celesteos-agent --help"
echo ""
