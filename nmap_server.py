#!/usr/bin/env python3
"""
Nmap MCP Server (Advanced / Red Team Mode)

WARNING:
This server can perform aggressive scans, NSE execution,
and internet-wide scanning.

Use ONLY with explicit authorization.
All dangerous actions require explicit acknowledgement
in the MCP request.

RECOMMENDED:
- Run in isolated VM
- Use VPN / lab ISP
- Enable logging
"""

import os
import sys
import uuid
import signal
import subprocess
from typing import Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NMAP_BIN = "/usr/bin/nmap"
SCAN_DIR  = os.path.join(os.path.dirname(__file__), "scans")
TIMEOUT   = 600

os.makedirs(SCAN_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Scan profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "quick": {
        "description": "Fast TCP connect scan of top 100 ports, no NSE",
        "args": ["-sT", "--top-ports", "100", "-T4"],
        "needs_root": False,
    },
    "standard": {
        "description": "TCP connect scan + service/version detection, top 1000 ports",
        "args": ["-sT", "-sV", "--top-ports", "1000", "-T3"],
        "needs_root": False,
    },
    "syn": {
        "description": "SYN stealth scan + service detection (requires root/caps)",
        "args": ["-sS", "-sV", "-T4"],
        "needs_root": True,
    },
    "vuln": {
        "description": "SYN scan + vulnerability NSE scripts (requires root/caps)",
        "args": ["-sS", "-sV", "--script", "vuln", "-T4"],
        "needs_root": True,
    },
    "full": {
        "description": "Aggressive scan: OS detect, version, scripts, traceroute (requires root/caps)",
        "args": ["-A", "-T4"],
        "needs_root": True,
    },
}

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("nmap-mcp")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
def list_profiles() -> dict:
    """
    List all available nmap scan profiles.
    Returns profile names with descriptions and whether root/caps are needed.
    """
    return {
        name: {
            "description": p["description"],
            "needs_root_or_caps": p["needs_root"],
        }
        for name, p in PROFILES.items()
    }


@mcp.tool
def run_scan(
    target: str,
    profile: str = "standard",
    extra_args: str = "",
    confirmed: bool = False,
) -> dict:
    """
    Run an nmap scan against a target and return the scan ID.

    Args:
        target:     IP address, hostname, or CIDR range to scan.
        profile:    Scan profile name. Use list_profiles() to see options. Default: standard.
        extra_args: Optional extra nmap flags appended verbatim (e.g. "-p 80,443").
        confirmed:  Must be set to true to confirm you are authorized to scan this target.

    Returns a dict with scan_id on success, or an error key on failure.
    """
    if not confirmed:
        return {
            "error": "You must set confirmed=true to acknowledge you are authorized to scan this target."
        }

    if profile not in PROFILES:
        names = ", ".join(PROFILES.keys())
        return {"error": f"Unknown profile '{profile}'. Valid profiles: {names}"}

    if not target or not target.strip():
        return {"error": "target must not be empty"}

    scan_id     = str(uuid.uuid4())
    output_file = os.path.join(SCAN_DIR, f"{scan_id}.xml")

    cmd = [NMAP_BIN] + PROFILES[profile]["args"]

    if extra_args.strip():
        cmd += extra_args.strip().split()

    cmd += ["-oX", output_file, target.strip()]

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        return {"error": f"nmap exited with code {e.returncode}", "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {"error": f"Scan timed out after {TIMEOUT}s"}
    except FileNotFoundError:
        return {"error": f"nmap binary not found at {NMAP_BIN}"}
    except Exception as e:
        return {"error": str(e)}

    return {
        "scan_id": scan_id,
        "target":  target,
        "profile": profile,
    }


@mcp.tool
def get_scan_result(scan_id: str) -> dict:
    """
    Retrieve the XML output of a completed scan.

    Args:
        scan_id: The scan ID returned by run_scan.

    Returns a dict with an 'xml' key containing the full nmap XML output.
    """
    safe_id = os.path.basename(scan_id)  # path traversal guard
    path = os.path.join(SCAN_DIR, f"{safe_id}.xml")

    if not os.path.exists(path):
        return {"error": f"No scan found with id '{scan_id}'"}

    with open(path, "r", encoding="utf-8") as f:
        return {"xml": f.read()}


@mcp.tool
def list_scans() -> dict:
    """
    List all scan IDs that have completed results stored on disk.
    """
    try:
        files = [
            f.removesuffix(".xml")
            for f in os.listdir(SCAN_DIR)
            if f.endswith(".xml")
        ]
        return {"scan_ids": sorted(files)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def delete_scan(scan_id: str) -> dict:
    """
    Delete a stored scan result from disk.

    Args:
        scan_id: The scan ID to delete.
    """
    safe_id = os.path.basename(scan_id)
    path = os.path.join(SCAN_DIR, f"{safe_id}.xml")

    if not os.path.exists(path):
        return {"error": f"No scan found with id '{scan_id}'"}

    os.remove(path)
    return {"deleted": scan_id}


# ---------------------------------------------------------------------------
# Clean shutdown
# ---------------------------------------------------------------------------

def _shutdown(signum, frame):
    print("\n[nmap-mcp] shutting down", file=sys.stderr)
    os._exit(0)

signal.signal(signal.SIGINT,  _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
