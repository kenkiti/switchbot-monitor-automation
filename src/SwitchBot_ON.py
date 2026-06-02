import asyncio
import ctypes
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from bleak import BleakScanner


# ==========================================
# Settings
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "switchbot_config.json"
CONFIG_EXAMPLE_FILE = CONFIG_DIR / "switchbot_config.example.json"
SRC_DIR = PROJECT_ROOT / "src"
STATE_DIR = PROJECT_ROOT / "state"
LOG_DIR = PROJECT_ROOT / "logs"

STATE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

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
TARGET_MAC = CONFIG["target_mac"].upper()
LOG_FILE = LOG_DIR / "SwitchBot_ON.log"
CSV_FILE = LOG_DIR / "SwitchBot_ON.csv"
STATE_FILE = STATE_DIR / "switchbot_state.json"
wake_shortcut_raw = Path(CONFIG["wake_shortcut"])
if wake_shortcut_raw.is_absolute():
    ANTIGRAVITY_SHORTCUT = wake_shortcut_raw
else:
    ANTIGRAVITY_SHORTCUT = PROJECT_ROOT / wake_shortcut_raw

# CSV detailed logging is disabled for stable long-running operation.
ENABLE_CSV_LOG = bool(CONFIG["enable_csv_log"])

BIG_RESET_THRESHOLD = -500
WAKE_COOLDOWN_SECONDS = 30
SUMMARY_INTERVAL_SECONDS = 60
GAP_WARNING_SECONDS = 15

WAKE_REPEAT_COUNT = 3
WAKE_MOUSE_MOVE_PIXELS = 1
WAKE_BETWEEN_MOUSE_SECONDS = 0.05
WAKE_KEY_HOLD_SECONDS = 0.10
WAKE_BETWEEN_REPEAT_SECONDS = 0.20
WAKE_AFTER_INPUT_SECONDS = 1.00
# ==========================================


user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_SHIFT = 0x10
MAPVK_VK_TO_VSC = 0
SHIFT_SC = user32.MapVirtualKeyW(VK_SHIFT, MAPVK_VK_TO_VSC)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", _INPUTUNION),
    ]


last_seen_monotonic = None
last_counter = None
baseline_counter = None
last_payload_hex = None

away_mode = False
monitor_is_on = True
last_off_time = 0.0
last_wake_time = 0.0
wake_task_running = False

receive_count = 0
reset_count = 0
wake_count = 0
payload_change_count = 0
gap_warning_count = 0
summary_started_at = time.monotonic()


def ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_text_log(message: str):
    try:
        ensure_parent_dir(LOG_FILE)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def ensure_csv_header():
    ensure_parent_dir(CSV_FILE)
    if os.path.exists(CSV_FILE):
        return

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "mac",
            "rssi",
            "gap_seconds",
            "payload_len",
            "manufacturer_hex",
            "byte9",
            "byte10",
            "counter_be_9_10",
            "delta_from_previous",
            "delta_from_baseline",
            "reset_candidate",
            "payload_changed",
            "away_mode",
            "wake_triggered",
            "note",
        ])


def append_csv_row(row):
    try:
        ensure_csv_header()
        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        write_text_log(f"[{now_text()}] CSV WRITE ERROR: {repr(e)}")


def load_state():
    global away_mode, monitor_is_on, last_off_time, last_wake_time

    if not os.path.exists(STATE_FILE):
        save_state("SwitchBot_ON state init")
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        away_mode = bool(data.get("away_mode", False))
        monitor_is_on = bool(data.get("monitor_is_on", True))
        last_off_time = float(data.get("last_off_time", 0.0))
        last_wake_time = float(data.get("last_wake_time", 0.0))

    except Exception as e:
        write_text_log(f"[{now_text()}] STATE LOAD ERROR: {repr(e)}")
        save_state("SwitchBot_ON state reload fallback")


def save_state(reason: str):
    data = {
        "away_mode": away_mode,
        "monitor_is_on": monitor_is_on,
        "last_off_time": last_off_time,
        "last_wake_time": last_wake_time,
        "updated_at": now_text(),
        "last_reason": reason,
    }

    try:
        ensure_parent_dir(STATE_FILE)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        write_text_log(f"[{now_text()}] STATE SAVE ERROR: {repr(e)}")


def send_mouse_move(dx: int, dy: int):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_shift_down():
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki = KEYBDINPUT(0, SHIFT_SC, KEYEVENTF_SCANCODE, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_shift_up():
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki = KEYBDINPUT(0, SHIFT_SC, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


async def wake_monitor(trigger_reason: str):
    global away_mode, monitor_is_on, last_wake_time, wake_task_running, wake_count

    if wake_task_running:
        write_text_log(f"[{now_text()}] WAKE SKIP already running")
        return

    now = time.time()
    if now - last_wake_time < WAKE_COOLDOWN_SECONDS:
        write_text_log(
            f"[{now_text()}] WAKE SKIP cooldown active {now - last_wake_time:.1f}s"
        )
        return

    wake_task_running = True

    try:
        write_text_log(f"[{now_text()}] WAKE START {trigger_reason}")

        for i in range(WAKE_REPEAT_COUNT):
            send_mouse_move(WAKE_MOUSE_MOVE_PIXELS, 0)
            await asyncio.sleep(WAKE_BETWEEN_MOUSE_SECONDS)

            send_mouse_move(-WAKE_MOUSE_MOVE_PIXELS, 0)
            await asyncio.sleep(WAKE_BETWEEN_MOUSE_SECONDS)

            send_shift_down()
            await asyncio.sleep(WAKE_KEY_HOLD_SECONDS)
            send_shift_up()
            await asyncio.sleep(WAKE_BETWEEN_REPEAT_SECONDS)

            write_text_log(f"[{now_text()}] WAKE INPUT SENT {i + 1}/{WAKE_REPEAT_COUNT}")

        await asyncio.sleep(WAKE_AFTER_INPUT_SECONDS)

        if os.path.exists(ANTIGRAVITY_SHORTCUT):
            try:
                os.startfile(ANTIGRAVITY_SHORTCUT)
                write_text_log(f"[{now_text()}] ANTIGRAVITY STARTED {ANTIGRAVITY_SHORTCUT}")
            except Exception as e:
                write_text_log(f"[{now_text()}] ANTIGRAVITY ERROR {repr(e)}")
        else:
            write_text_log(f"[{now_text()}] ANTIGRAVITY NOT FOUND {ANTIGRAVITY_SHORTCUT}")

        away_mode = False
        monitor_is_on = True
        last_wake_time = time.time()
        wake_count += 1

        save_state("SwitchBot_ON wake")

        write_text_log(f"[{now_text()}] WAKE DONE away_mode=False")

    except Exception as e:
        write_text_log(f"[{now_text()}] WAKE ERROR {repr(e)}")

    finally:
        wake_task_running = False


def extract_counter(advertisement_data):
    man_data = advertisement_data.manufacturer_data.get(2409)

    if not man_data or len(man_data) < 10:
        return None, None, None, None

    payload_hex = man_data.hex()
    byte9 = man_data[8]
    byte10 = man_data[9]
    counter = (byte9 << 8) + byte10

    return payload_hex, byte9, byte10, counter


def maybe_write_summary():
    global summary_started_at

    now_mono = time.monotonic()
    if now_mono - summary_started_at < SUMMARY_INTERVAL_SECONDS:
        return

    write_text_log(
        f"[{now_text()}] SUMMARY "
        f"recv={receive_count} "
        f"resets={reset_count} "
        f"wakes={wake_count} "
        f"payload_changes={payload_change_count} "
        f"gap_warnings={gap_warning_count} "
        f"away_mode={away_mode}"
    )

    summary_started_at = now_mono


def detection_callback(device, advertisement_data):
    global last_seen_monotonic
    global last_counter
    global baseline_counter
    global last_payload_hex
    global receive_count
    global reset_count
    global payload_change_count
    global gap_warning_count

    if device.address.upper() != TARGET_MAC:
        return

    load_state()

    timestamp = now_text()
    receive_count += 1

    payload_hex, byte9, byte10, counter = extract_counter(advertisement_data)

    if counter is None:
        note = "manufacturer_data_missing_or_short"

        if ENABLE_CSV_LOG:
            append_csv_row([
                timestamp,
                device.address,
                advertisement_data.rssi,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                0,
                0,
                int(away_mode),
                0,
                note,
            ])

        return

    now_mono = time.monotonic()
    gap_seconds = ""

    if last_seen_monotonic is not None:
        gap = now_mono - last_seen_monotonic
        gap_seconds = round(gap, 3)

        if gap >= GAP_WARNING_SECONDS:
            gap_warning_count += 1
            write_text_log(f"[{timestamp}] GAP WARNING {gap:.3f}s")

    last_seen_monotonic = now_mono

    if baseline_counter is None:
        baseline_counter = counter

    delta_from_previous = ""
    reset_candidate = 0
    wake_triggered = 0
    note = ""

    if last_counter is not None:
        delta = counter - last_counter
        delta_from_previous = delta

        if delta <= BIG_RESET_THRESHOLD:
            reset_candidate = 1
            reset_count += 1
            note = f"big_reset delta={delta}"

            write_text_log(
                f"[{timestamp}] BIG RESET "
                f"prev={last_counter} "
                f"current={counter} "
                f"delta={delta} "
                f"away_mode={away_mode}"
            )

            if away_mode:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(wake_monitor("ble_reset"))
                    wake_triggered = 1
                    note += " wake_requested"
                except RuntimeError:
                    note += " wake_schedule_failed"
                    write_text_log(f"[{timestamp}] WAKE SCHEDULE ERROR no running loop")

    delta_from_baseline = counter - baseline_counter

    payload_changed = 0

    if last_payload_hex is not None and payload_hex != last_payload_hex:
        payload_changed = 1
        payload_change_count += 1

    last_payload_hex = payload_hex
    last_counter = counter

    try:
        sys.stdout.write(
            f"\r[{time.strftime('%X')}] "
            f"counter={counter} "
            f"delta={delta_from_previous} "
            f"away={1 if away_mode else 0} "
            f"rssi={advertisement_data.rssi}     "
        )
        sys.stdout.flush()
    except Exception:
        pass

    if ENABLE_CSV_LOG:
        append_csv_row([
            timestamp,
            device.address,
            advertisement_data.rssi,
            gap_seconds,
            len(payload_hex) // 2,
            payload_hex,
            byte9,
            byte10,
            counter,
            delta_from_previous,
            delta_from_baseline,
            reset_candidate,
            payload_changed,
            int(away_mode),
            wake_triggered,
            note,
        ])

    maybe_write_summary()


async def main():
    ensure_parent_dir(LOG_FILE)
    ensure_parent_dir(CSV_FILE)
    ensure_parent_dir(STATE_FILE)

    write_text_log(f"--- START [{now_text()}] TARGET={TARGET_MAC} CSV={ENABLE_CSV_LOG} ---")

    load_state()
    save_state("SwitchBot_ON start")

    if ENABLE_CSV_LOG:
        ensure_csv_header()

    scanner = BleakScanner(detection_callback)

    await scanner.start()
    write_text_log(f"[{now_text()}] BLE SCANNER STARTED")

    try:
        while True:
            await asyncio.sleep(1)

    finally:
        await scanner.stop()
        write_text_log(f"--- STOP [{now_text()}] ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        write_text_log(f"--- STOP [{now_text()}] KeyboardInterrupt ---")

    except Exception as e:
        write_text_log(f"--- FATAL ERROR [{now_text()}] {repr(e)} ---")
        raise
