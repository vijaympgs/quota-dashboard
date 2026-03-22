"""
fetch_quota.py - AI Coding Tools Quota Utility
----------------------------------------------
Used as a module by app.py.
Can also be run standalone:
    python fetch_quota.py
    python fetch_quota.py --no-push
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "quota_data.json"

AG_COLORS = {
    "claude-opus": "#7F77DD",
    "claude-sonnet": "#BA7517",
    "gemini-2.5-flash": "#1D9E75",
    "gemini-2.5-pro": "#378ADD",
    "gemini-3-flash": "#0F6E56",
    "gemini-3-pro": "#185FA5",
    "gemini-3.1-pro": "#3B6D11",
    "gpt-oss": "#D85A30",
}

ANT_COLORS = {
    "claude-opus": "#7F77DD",
    "claude-sonnet": "#BA7517",
    "claude-haiku": "#1D9E75",
}


def ag_color(model_id):
    for key, color in AG_COLORS.items():
        if key in model_id:
            return color
    return "#888780"


def ant_color(model_name):
    lowered = model_name.lower()
    for key, color in ANT_COLORS.items():
        if key in lowered:
            return color
    return "#888780"

def runtime_config():
    load_dotenv(BASE_DIR / ".env", override=True)
    return {
        "anthropic_admin_key": os.environ.get("ANTHROPIC_ADMIN_KEY", "").strip(),
    }


def read_existing_cards():
    if not OUTPUT_FILE.exists():
        return []
    try:
        payload = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        return payload.get("accounts", [])
    except Exception as exc:
        print(f"[CACHE] Failed to read existing quota_data.json: {exc}")
        return []


def preserve_tool_cards(existing_cards, tool_name):
    kept = [card for card in existing_cards if card.get("tool") == tool_name]
    if kept:
        print(f"[CACHE] Reusing {len(kept)} cached {tool_name} row(s)")
    return kept


def find_ag_cli():
    import shutil

    direct = shutil.which("antigravity-usage") or shutil.which("antigravity-usage.cmd")
    if direct:
        return direct

    appdata = os.environ.get("APPDATA", "")
    candidates = [
        os.path.join(appdata, "npm", "antigravity-usage.cmd"),
        os.path.join(appdata, "npm", "antigravity-usage"),
    ]

    try:
        npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
        if npm_cmd:
            result = subprocess.run(
                [npm_cmd, "root", "-g"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(str(Path(result.stdout.strip()).parent / "antigravity-usage.cmd"))
    except Exception:
        pass

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def fetch_antigravity(cli):
    print("[AG]  Fetching Antigravity...")
    try:
        command = [cli, "--all", "--json"]
        if sys.platform == "win32" and cli.lower().endswith(".cmd"):
            command = ["cmd", "/c", cli, "--all", "--json"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[AG]  CLI exited with {result.returncode}: {result.stderr.strip()[:200]}")
            return []
        raw = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout.strip())
        if not raw:
            print("[AG]  CLI returned no output")
            return []
        data = json.loads(raw)
    except Exception as exc:
        print(f"[AG]  Error: {exc}")
        return []

    cards = []
    for account in data:
        if account.get("status") != "success":
            continue
        email = account.get("email", "unknown")
        is_active = account.get("isActive", False)
        seen = set()
        for model in account.get("snapshot", {}).get("models", []):
            label = model.get("label", model.get("modelId", "?"))
            model_id = model.get("modelId", "")
            if label in seen:
                continue
            seen.add(label)
            remaining = model.get("remainingPercentage")
            exhausted = model.get("isExhausted", False)
            used_pct = 100 if exhausted else (None if remaining is None else round((1 - remaining) * 100))
            cards.append({
                "id": f"ag__{email}__{model_id}",
                "tool": "Antigravity",
                "category": "AI Coding Tools",
                "account": email.split("@")[0],
                "email": email,
                "isActive": is_active,
                "model": label,
                "modelId": model_id,
                "used_pct": used_pct,
                "isExhausted": exhausted,
                "autocompleteOnly": model.get("isAutocompleteOnly", False),
                "resetTime": model.get("resetTime"),
                "resetMs": model.get("timeUntilResetMs", 0),
                "color": ag_color(model_id),
                "used": None,
                "quota": None,
                "fetch_method": "antigravity-usage CLI",
            })

    print(f"[AG]  {len(cards)} model slots across {len(set(card['email'] for card in cards))} accounts")
    return cards


def fetch_claude_code(admin_key=None):
    key = admin_key or runtime_config()["anthropic_admin_key"]
    if not key:
        print("[CC]  ANTHROPIC_ADMIN_KEY not set - skipping")
        return []

    print("[CC]  Fetching Claude Code/Anthropic usage...")
    today = datetime.now(timezone.utc)
    start = f"{today.year}-{today.month:02d}-{today.day:02d}"
    url = f"https://api.anthropic.com/v1/usage?start_date={start}"
    req = urllib.request.Request(
        url,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"[CC]  Error: {exc}")
        return []

    cards = []
    for entry in data.get("data", []):
        model = entry.get("model", "unknown")
        input_tokens = entry.get("input_tokens", 0) or 0
        output_tokens = entry.get("output_tokens", 0) or 0
        cards.append({
            "id": f"cc__{model}",
            "tool": "Claude Code",
            "category": "AI Coding Tools",
            "account": "anthropic-org",
            "email": "Anthropic org",
            "isActive": True,
            "model": model,
            "modelId": model,
            "used_pct": None,
            "isExhausted": False,
            "autocompleteOnly": False,
            "resetTime": None,
            "resetMs": 0,
            "color": ant_color(model),
            "used": input_tokens + output_tokens,
            "quota": None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "fetch_method": "Anthropic Admin API",
        })

    print(f"[CC]  {len(cards)} models")
    return cards


def write_json(cards):
    tools = {}
    for card in cards:
        tools.setdefault(card["tool"], 0)
        tools[card["tool"]] += 1

    payload = {
        "fetched_at": datetime.now().isoformat(),
        "category": "AI Coding Tools",
        "tools": list(tools.keys()),
        "accounts": cards,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary = ", ".join(f"{count} {tool}" for tool, count in tools.items())
    print(f"[OK]  {summary} -> quota_data.json")
    return payload


def git_push():
    repo = str(BASE_DIR)

    def run(cmd):
        return subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32"),
        )

    run(["git", "add", "quota_data.json"])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run(["git", "commit", "-m", f"quota update {timestamp}"])
    if "nothing to commit" in result.stdout + result.stderr:
        print("[GIT] No changes")
        return
    push = run(["git", "push"])
    if push.returncode == 0:
        print("[GIT] Pushed")
    else:
        print(f"[GIT] Push failed: {push.stderr[:100]}")


def fetch_all(push=False):
    cards = []
    existing_cards = read_existing_cards()

    ag_cli = find_ag_cli()
    if ag_cli:
        print(f"[AG]  CLI: {ag_cli}")
        ag_cards = fetch_antigravity(ag_cli)
        if ag_cards:
            cards += ag_cards
        else:
            cards += preserve_tool_cards(existing_cards, "Antigravity")
    else:
        print("[AG]  antigravity-usage not found - reusing cached data if available")
        cards += preserve_tool_cards(existing_cards, "Antigravity")

    cards += fetch_claude_code()
    cards = [card for card in cards if "propertism.tamil" not in card.get("email", "")]

    payload = write_json(cards)
    if push:
        git_push()
    return payload


if __name__ == "__main__":
    load_dotenv()
    fetch_all(push=False)
