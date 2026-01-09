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
import subprocess
import ipaddress
import signal
from typing import List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# -------------------------------------------------------------------
# Hardening / Constants
# -------------------------------------------------------------------

NMAP_BIN = "/usr/bin/nmap"
SCAN_DIR = "scans"
SCAN_TIMEOUT = 600  # Longer timeout for NSE
os.makedirs(SCAN_DIR, exist_ok=True)

# -------------------------------------------------------------------
# NSE Controls
# -------------------------------------------------------------------

ALLOWED_NSE_CATEGORIES = {
    "default",
    "safe",
    "discovery",
    "auth",
    "vuln",
    "intrusive"  # allowed, but requires dangerous flag
}

BLOCKED_NSE_KEYWORDS = {
    "dos",
    "brute",
    "exploit"
}

# -------------------------------------------------------------------
# Scan Profiles
# -------------------------------------------------------------------

SCAN_PROFILES = {
    "safe": {
        "description": "Low-noise scan (no NSE, internal only)",
        "args": ["-sT", "-sV", "--top-ports", "1000", "-T3"],
        "internet": False,
        "nse": False
    },
    "syn": {
        "description": "SYN scan with service detection",
        "args": ["-sS", "-sV", "-T4"],
        "internet": True,
        "nse": False
    },
    "nse-vuln": {
        "description": "Vulnerability NSE scan (authorized targets only)",
        "args": ["-sS", "-sV", "-T4"],
        "internet": True,
        "nse": True
    },
    "aggressive": {
        "description": "Aggressive scan (-A) with NSE",
        "args": ["-A", "-T4"],
        "internet": True,
        "nse": True
    }
}

# -------------------------------------------------------------------
# MCP Setup
# -------------------------------------------------------------------

mcp = FastMCP(
    name="nmap-mcp"
)

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class NmapScanRequest(BaseModel):
    target: str = Field(description="IP or domain name")
    profile: str = Field(description="Scan profile")
    nse_category: Optional[str] = Field(
        default=None,
        description="NSE category (e.g. vuln, discovery)"
    )
    dangerous: bool = Field(
        default=False,
        description="Explicitly allow dangerous scans"
    )
    user_acknowledged: bool = Field(
        default=False,
        description="User confirms authorization and legality"
    )

class ScanResultRequest(BaseModel):
    scan_id: str

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def is_private_ip(target: str) -> bool:
    try:
        ip = ipaddress.ip_address(target)
        return ip.is_private
    except ValueError:
        return False

def validate_nse(category: str, dangerous: bool):
    if category not in ALLOWED_NSE_CATEGORIES:
        raise ValueError("NSE category not allowed")

    for blocked in BLOCKED_NSE_KEYWORDS:
        if blocked in category:
            raise ValueError("Blocked NSE category")

    if category in {"intrusive", "vuln"} and not dangerous:
        raise ValueError("Dangerous NSE requires dangerous=true")

def build_command(req: NmapScanRequest, output_file: str) -> List[str]:
    profile = SCAN_PROFILES[req.profile]

    cmd = [NMAP_BIN, *profile["args"]]

    # NSE handling
    if profile["nse"]:
        if not req.nse_category:
            raise ValueError("NSE category required for this profile")

        validate_nse(req.nse_category, req.dangerous)
        cmd += ["--script", req.nse_category]

    cmd += ["-oX", output_file, req.target]
    return cmd

# -------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------

@mcp.tool()
def list_scan_profiles() -> dict:
    return {
        name: {
            "description": p["description"],
            "internet": p["internet"],
            "nse": p["nse"]
        }
        for name, p in SCAN_PROFILES.items()
    }

@mcp.tool()
def run_nmap_scan(req: NmapScanRequest) -> dict:
    if req.profile not in SCAN_PROFILES:
        return {"error": "Invalid scan profile"}

    profile = SCAN_PROFILES[req.profile]

    # Internet scanning requires explicit acknowledgement
    if profile["internet"]:
        if not (req.dangerous and req.user_acknowledged):
            return {
                "error": "Internet scanning requires dangerous=true and user_acknowledged=true"
            }

    # Internal-only enforcement
    if not profile["internet"] and not is_private_ip(req.target):
        return {"error": "This profile is restricted to private targets"}

    scan_id = str(uuid.uuid4())
    output_file = os.path.join(SCAN_DIR, f"{scan_id}.xml")

    try:
        cmd = build_command(req, output_file)

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SCAN_TIMEOUT,
            check=True,
            env={}
        )

    except Exception as e:
        return {"error": str(e)}

    return {
        "scan_id": scan_id,
        "target": req.target,
        "profile": req.profile,
        "nse_category": req.nse_category
    }

@mcp.tool()
def get_scan_xml(req: ScanResultRequest) -> dict:
    path = os.path.join(SCAN_DIR, f"{req.scan_id}.xml")
    if not os.path.exists(path):
        return {"error": "Scan not found"}

    with open(path, "r") as f:
        return {"xml": f.read()}

# -------------------------------------------------------------------
# Signal Handling (CLEAN SHUTDOWN)
# -------------------------------------------------------------------


def _handle_signal(signum, frame):
    print("\n[*] SIGINT received, forcing MCP server shutdown...", file=sys.stderr)

    # Immediately terminate process (no asyncio, no threads, no stdio waits)
    os._exit(0)

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# -------------------------------------------------------------------
# Entry
# -------------------------------------------------------------------

if __name__ == "__main__":
	try:
	    mcp.run()
	except KeyboardInterrupt:
	    print("[*] MCP server interrupted, shutting down cleanly...", file=sys.stderr)
