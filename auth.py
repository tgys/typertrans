"""Authentication utilities for Claude API and Z-Library."""

import os
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .config import CLAUDE_CACHE, ZLIB_AUTH_CACHE, CACHE_DAYS, ui


# Claude Key Caching
def get_cached_key():
    try:
        with open(CLAUDE_CACHE) as f:
            data = json.load(f)
            ts = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - ts < timedelta(days=CACHE_DAYS):
                return data["api_key"]
    except:
        pass
    return None


def cache_key(key):
    with open(CLAUDE_CACHE, "w") as f:
        json.dump({"api_key": key, "timestamp": datetime.now().isoformat()}, f)


def get_bearer():
    token = get_cached_key()
    if token:
        ui.log_to_file_only("🔑 Using cached Claude API key")
        return token

    token = ui.get_input("🔑 Claude API key:", password=True)
    if not token:
        ui.log("❌ No API key provided")
        return None
    cache_key(token)
    return token


# Z-Library Authentication
def get_cached_zlib_auth():
    try:
        with open(ZLIB_AUTH_CACHE) as f:
            data = json.load(f)
        return data["email"], data["password"]
    except:
        return None


def cache_zlib_auth(email, password):
    os.makedirs(os.path.dirname(ZLIB_AUTH_CACHE), exist_ok=True)
    with open(ZLIB_AUTH_CACHE, "w") as f:
        json.dump({"email": email, "password": password}, f)
    os.chmod(ZLIB_AUTH_CACHE, 0o600)


def zlib_login(session: requests.Session) -> bool:
    BASE = "https://z-library.sk"
    ui.log("🔑 Logging into Z‑Library.sk…")

    try:
        # Get home page and find sign in link
        home = session.get(BASE + "/", verify=False, timeout=30)
        home.raise_for_status()
        soup = BeautifulSoup(home.text, "html.parser")
        sign_in = soup.find("a", href=re.compile(r"^/login"))
        if not sign_in:
            ui.log("⚠️ Could not find Sign in link on home page.")
            return False

        login_url = urljoin(BASE, sign_in["href"])
        ui.log(f"🔑 Found login URL: {login_url}")

        page = session.get(login_url, verify=False, timeout=30)
        page.raise_for_status()
        soup2 = BeautifulSoup(page.text, "html.parser")

        # Find login form
        login_form = None
        for form in soup2.find_all("form"):
            has_email = form.find("input", {"name": "email"})
            has_pass = form.find("input", {"name": "password"})
            if has_email and has_pass:
                login_form = form
                break

        if not login_form:
            ui.log("⚠️ Login form not found.")
            return False

        # Get POST URL
        action = login_form.get("action") or "/"
        post_url = urljoin(login_url, action)
        ui.log(f"📝 Submitting credentials to: {post_url}")

        # Get credentials
        creds = get_cached_zlib_auth()
        if creds:
            email, password = creds
            ui.log("🔐 Using cached credentials")
        else:
            email = ui.get_input("👤 Z‑Library email:")
            if not email:
                return False
            password = ui.get_input("🔒 Z‑Library password:", password=True)
            if not password:
                return False
            cache_zlib_auth(email, password)

        # Build form payload
        payload = {}
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            if name.lower() == "email":
                payload[name] = email
            elif name.lower() == "password":
                payload[name] = password
            else:
                payload[name] = inp.get("value", "")

        # Submit login
        resp = session.post(post_url, data=payload, verify=False, timeout=30)
        if resp.status_code == 200 and "logout" in resp.text.lower():
            ui.log("✅ Z‑Library login successful")
            return True

        ui.log(f"❌ Z‑Library login failed (status {resp.status_code})")
        try:
            os.remove(ZLIB_AUTH_CACHE)
        except OSError:
            pass
        return False

    except Exception as e:
        ui.log(f"❌ Z-Library login error: {e}")
        return False