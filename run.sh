#!/usr/bin/env bash
# run.sh — Nmap MCP server launcher
# Grants nmap network capabilities for the duration of the session,
# then removes them on exit (Ctrl+C, crash, or SIGTERM).

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SERVER="$PROJECT_DIR/nmap_server.py"
NMAP_BIN="/usr/bin/nmap"

# ---------- sanity checks ----------
[[ -f "$SERVER" ]]  || { echo "[!] nmap_server.py not found in $PROJECT_DIR"; exit 1; }
[[ -x "$NMAP_BIN" ]] || { echo "[!] nmap not found at $NMAP_BIN"; exit 1; }

echo "[*] Starting nmap-mcp server..."

# ---------- sudo keepalive ----------
sudo -v
while true; do sudo -n true; sleep 30; done 2>/dev/null &
KEEPALIVE_PID=$!

# ---------- cleanup on exit ----------
cleanup() {
    echo "[*] Removing nmap capabilities..."
    sudo setcap -r "$NMAP_BIN" 2>/dev/null || true
    kill "$KEEPALIVE_PID" 2>/dev/null || true
    echo "[*] Done."
}
trap cleanup EXIT

# ---------- venv ----------
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [[ ! -f "$VENV_DIR/.installed" ]]; then
    echo "[*] Installing dependencies..."
    pip install --upgrade pip -q
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    touch "$VENV_DIR/.installed"
fi

# ---------- nmap capabilities ----------
sudo setcap -r "$NMAP_BIN" 2>/dev/null || true
sudo setcap cap_net_raw,cap_net_admin+eip "$NMAP_BIN"

if ! getcap "$NMAP_BIN" | grep -q cap_net_raw; then
    echo "[!] Failed to set nmap capabilities — SYN/full scans won't work"
fi

echo "[+] Ready. Ctrl+C to stop."

# ---------- launch ----------
exec python "$SERVER"
