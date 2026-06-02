import ctypes
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ==========================================
# 設定
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "switchbot_config.json"
CONFIG_EXAMPLE_FILE = CONFIG_DIR / "switchbot_config.example.json"
STATE_DIR = PROJECT_ROOT / "state"
LOG_DIR = PROJECT_ROOT / "logs"

STATE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

STATE_FILE = STATE_DIR / "switchbot_state.json"
LOG_FILE = LOG_DIR / "SwitchBot_OFF.log"

REQUIRED_CONFIG_KEYS = [
    "target_mac",
    "idle_minutes",
    "enable_csv_log",
    "wake_shortcut",
    "daily_restart_time",
]


def load_config():
    if not CONFIG_FILE.exists():
        print(f"ERROR: config file not found: {CONFIG_FILE}")
        print(f"Copy {CONFIG_EXAMPLE_FILE} to {CONFIG_FILE} and edit it.")
        sys.exit(1)

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in config file: {CONFIG_FILE}")
        print(e)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: failed to read config file: {CONFIG_FILE}")
        print(e)
        sys.exit(1)

    if not isinstance(config, dict):
        print(f"ERROR: config root must be a JSON object: {CONFIG_FILE}")
        sys.exit(1)

    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        print(f"ERROR: missing config keys: {missing}")
        sys.exit(1)

    return config


CONFIG = load_config()
AWAY_IDLE_SECONDS = int(CONFIG["idle_minutes"]) * 60
CHECK_INTERVAL_SECONDS = 2
# ==========================================

user32 = ctypes.windll.user32

HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log(message: str):
    try:
        ensure_parent_dir(LOG_FILE)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def load_state() -> dict:
    default_state = {
        "away_mode": False,
        "monitor_is_on": True,
        "last_off_time": 0.0,
        "last_wake_time": 0.0,
        "updated_at": now_text(),
        "last_reason": "init",
    }
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_state.update(data)
    except Exception as e:
        write_log(f"[{now_text()}] STATE LOAD ERROR: {repr(e)}")
    return default_state


def save_state(**updates):
    state = load_state()
    state.update(updates)
    state["updated_at"] = now_text()
    try:
        ensure_parent_dir(STATE_FILE)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        write_log(f"[{now_text()}] STATE SAVE ERROR: {repr(e)}")


def get_windows_idle_seconds() -> int:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0

    tick_now = ctypes.windll.kernel32.GetTickCount()
    elapsed_ms = (tick_now - info.dwTime) & 0xFFFFFFFF
    return int(elapsed_ms / 1000)


def turn_off_monitor(idle_seconds: int):
    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
    save_state(
        away_mode=True,
        monitor_is_on=False,
        last_off_time=time.time(),
        last_reason=f"idle_off {idle_seconds}s",
    )
    write_log(f"[{now_text()}] MONITOR OFF (windows_idle={idle_seconds}s, away_mode=True)")


def main():
    print("SwitchBot_OFF started")
    print(f"Log file   : {LOG_FILE}")
    print(f"State file : {STATE_FILE}")
    print(f"OFF cond   : windows idle >= {AWAY_IDLE_SECONDS}s")
    print("Press Ctrl+C to stop.\n" + "-" * 70)
    write_log(f"--- START [{now_text()}] ---")
    save_state(last_reason="SwitchBot_OFF start")

    try:
        while True:
            idle_seconds = get_windows_idle_seconds()
            state = load_state()
            away_mode = bool(state.get("away_mode", False))

            if not away_mode and idle_seconds >= AWAY_IDLE_SECONDS:
                turn_off_monitor(idle_seconds)

            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n\nstopped")
        write_log(f"--- STOP [{now_text()}] KeyboardInterrupt ---")


if __name__ == "__main__":
    main()
