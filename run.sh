#!/usr/bin/env bash
#
# run.sh — Nmap MCP launcher (SAFE CAPABILITY LIFECYCLE)
#
# Guarantees:
# - sudo requested once
# - sudo kept alive
# - Nmap caps exist only while this script runs
# - caps removed on ANY exit (Ctrl+C, crash, SIGTERM)
#

set -Eeuo pipefail

# --------------------------------------------------
# Paths / config
# --------------------------------------------------

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SERVER_SCRIPT="$PROJECT_DIR/nmap_server.py"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
NMAP_BIN="/usr/bin/nmap"
DEPS_MARKER="$VENV_DIR/.deps_installed"

# --------------------------------------------------
# Banner
# --------------------------------------------------

echo "[*] Starting Nmap MCP server..."

# --------------------------------------------------
# Sanity checks
# --------------------------------------------------

[[ -f "$SERVER_SCRIPT" ]] || { echo "[!] nmap_server.py not found"; exit 1; }
[[ -f "$REQUIREMENTS" ]]  || { echo "[!] requirements.txt not found"; exit 1; }
[[ -x "$NMAP_BIN" ]]      || { echo "[!] nmap binary not found"; exit 1; }

# --------------------------------------------------
# Ask for sudo ONCE
# --------------------------------------------------

echo "[*] Requesting sudo access..."
sudo -v

# Keep sudo alive while script runs
while true; do
    sudo -n true
    sleep 30
done 2>/dev/null &
SUDO_KEEPALIVE_PID=$!

# --------------------------------------------------
# Cleanup handler (runs ONCE)
# --------------------------------------------------

cleanup() {
    echo
    echo "[*] Shutting down MCP server..."
    echo "[*] Removing Nmap capabilities..."

    sudo setcap -r "$NMAP_BIN" 2>/dev/null || true

    if getcap "$NMAP_BIN" | grep -q cap_net_raw; then
        echo "[!] WARNING: Nmap capabilities still present"
    else
        echo "[+] Nmap capabilities removed"
    fi

    kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    echo "[*] Cleanup complete"
}

trap cleanup EXIT

# --------------------------------------------------
# Create venv if missing
# --------------------------------------------------

if [[ ! -d "$VENV_DIR" ]]; then
    echo "[*] Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# --------------------------------------------------
# Activate venv
# --------------------------------------------------

echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# --------------------------------------------------
# Install dependencies (once)
# --------------------------------------------------

if [[ ! -f "$DEPS_MARKER" ]]; then
    echo "[*] Installing Python dependencies..."
    pip install --upgrade pip >/dev/null
    pip install -r "$REQUIREMENTS" --quiet
    touch "$DEPS_MARKER"
else
    echo "[*] Python dependencies already installed"
fi

# --------------------------------------------------
# Ensure clean capability state
# --------------------------------------------------

sudo setcap -r "$NMAP_BIN" 2>/dev/null || true

echo "[*] Enabling Nmap capabilities..."
sudo setcap cap_net_raw,cap_net_admin+eip "$NMAP_BIN"

if ! getcap "$NMAP_BIN" | grep -q cap_net_raw; then
    echo "[!] Failed to apply Nmap capabilities"
    exit 1
fi

echo "[+] Nmap capabilities enabled"

# --------------------------------------------------
# Run MCP server (foreground)
# --------------------------------------------------

echo "[*] Launching MCP server..."
exec python "$SERVER_SCRIPT"
