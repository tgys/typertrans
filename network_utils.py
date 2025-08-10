"""Network and VPN management utilities."""

import os
import json
import time
import tempfile
import subprocess
import requests
from .config import OVPN_CACHE, ui


def get_cached_ovpn():
    try:
        with open(OVPN_CACHE) as f:
            return json.load(f).get("path")
    except:
        return None


def cache_ovpn(path):
    os.makedirs(os.path.dirname(OVPN_CACHE), exist_ok=True)
    with open(OVPN_CACHE, "w") as f:
        json.dump({"path": path}, f)


def is_vpn_connected():
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
        return not ip.startswith(("10.", "192.", "172.", "127."))
    except:
        return False


def start_vpn():
    ui.log("🔐 Checking VPN...")
    ui.set_status("Checking VPN connection")

    if is_vpn_connected():
        ui.log("🟢 VPN already up")
        return

    ovpn = get_cached_ovpn()
    while not ovpn or not os.path.isfile(ovpn):
        ovpn = ui.get_input("🔍 Path to your .ovpn file:", default=ovpn or "")
        if not ovpn:
            ui.log("❌ No VPN file provided")
            return
        if not os.path.isfile(ovpn):
            ui.log("❌ File not found.")
        else:
            cache_ovpn(ovpn)

    user = ui.get_input("👤 VPN username:")
    if not user:
        ui.log("❌ No username provided")
        return

    pwd = ui.get_input("🔒 VPN password:", password=True)
    if not pwd:
        ui.log("❌ No password provided")
        return

    auth = os.path.join(tempfile.gettempdir(), "vpn_auth.txt")
    with open(auth, "w") as f:
        f.write(f"{user}\n{pwd}\n")

    ui.log("🌐 Connecting VPN...")
    ui.set_status("Connecting to VPN...")

    subprocess.Popen(
        ["sudo", "openvpn", "--config", ovpn, "--auth-user-pass", auth],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    for i in range(30):
        ui.set_status(f"Waiting for VPN connection... ({i+1}/30)")
        if is_vpn_connected():
            ui.log("✅ VPN connected")
            ui.set_status("VPN connected")
            return
        time.sleep(1)

    ui.log("❌ VPN connection failed")
    ui.set_status("VPN connection failed")