#!/bin/bash

echo "=================================="
echo "Tor Bot Setup Script"
echo "=================================="

# Update package list
echo -e "\n[1/7] Updating package list..."
sudo apt-get update -qq

# Install Tor
echo -e "\n[2/7] Installing Tor..."
sudo apt-get install -y tor

# Install Firefox and geckodriver
echo -e "\n[3/7] Installing Firefox..."
sudo apt-get install -y firefox-esr

echo -e "\n[4/7] Installing geckodriver..."
wget -q https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xzf geckodriver-v0.33.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver
rm geckodriver-v0.33.0-linux64.tar.gz

# Install Python dependencies
echo -e "\n[5/7] Installing Python dependencies..."
pip3 install -r requirements.txt

# Configure Tor
echo -e "\n[6/7] Configuring Tor..."
sudo tee /etc/tor/torrc > /dev/null <<EOF
# Tor configuration for bot
ControlPort 9051
SocksPort 9050
CookieAuthentication 0
EOF

# Start Tor service
echo -e "\n[7/7] Starting Tor service..."

# Try systemctl first, if not available use service or direct command
if command -v systemctl &> /dev/null; then
    sudo systemctl restart tor
    sleep 3
    if sudo systemctl is-active --quiet tor; then
        echo -e "\n✓ Tor service is running (systemctl)"
    else
        echo "systemctl failed, trying alternative method..."
        sudo pkill -9 tor 2>/dev/null
        sleep 1
        sudo tor &
        sleep 3
        echo -e "\n✓ Tor service started (direct)"
    fi
elif command -v service &> /dev/null; then
    sudo service tor restart 2>/dev/null || (sudo pkill -9 tor 2>/dev/null; sleep 1; sudo tor &)
    sleep 3
    echo -e "\n✓ Tor service started (service)"
else
    # Direct start
    sudo pkill -9 tor 2>/dev/null
    sleep 1
    sudo tor &
    sleep 3
    echo -e "\n✓ Tor service started (direct)"
fi

# Check if Tor is actually running
if pgrep -x tor > /dev/null; then
    echo -e "\n✓ Tor process confirmed running"
    echo "✓ Setup completed successfully!"
else
    echo -e "\n⚠ Warning: Could not confirm Tor is running"
    echo "You may need to start it manually with: sudo tor &"
fi

echo -e "\n=================================="
echo "Setup Complete!"
echo "=================================="
echo -e "\nRun the bot with: python3 tor_bot.py"
