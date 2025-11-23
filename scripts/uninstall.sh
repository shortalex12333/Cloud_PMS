#!/bin/bash
# CelesteOS Local Agent Uninstall Script

set -e

echo "======================================"
echo "CelesteOS Local Agent Uninstaller"
echo "======================================"
echo ""

# Stop and unload service
echo "Stopping daemon..."
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist 2>/dev/null || true
echo "✓ Daemon stopped"
echo ""

# Remove launchd plist
echo "Removing service..."
rm -f ~/Library/LaunchAgents/com.celesteos.agent.plist
echo "✓ Service removed"
echo ""

# Remove symlinks
echo "Removing commands..."
sudo rm -f /usr/local/bin/celesteos-daemon
sudo rm -f /usr/local/bin/celesteos-agent
echo "✓ Commands removed"
echo ""

# Ask about data
read -p "Remove all data and configuration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing data..."
    rm -rf ~/.celesteos
    rm -rf /Users/Shared/.celesteos
    echo "✓ Data removed"
else
    echo "Data preserved at ~/.celesteos"
fi

echo ""
echo "======================================"
echo "Uninstallation Complete"
echo "======================================"
echo ""
