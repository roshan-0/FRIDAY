import sys
import os
import webbrowser
import asyncio
import threading
import queue
import json
import psutil
import re
import time
import urllib.parse
import datetime

# ─── THREAD-SAFE INPUT QUEUE ───────────────────────────────────────────────
input_queue = queue.Queue()

# ─── VOICE NORMALIZATION MAP (F.R.I.D.A.Y. Matrix) ─────────────────────────
VOICE_MAP = {
    "cpu": "/cpu", "processor": "/cpu", "core load": "/cpu",
    "ram": "/ram", "memory": "/ram", "swap": "/ram",
    "disk": "/disk_usage", "storage": "/disk_usage",
    "battery": "/battery_status", "power": "/battery_status",
    "uptime": "/uptime", "how long": "/uptime",
    "network": "/net", "connection": "/net", "socket": "/net",
    "ping dns": "/ping_dns", "internet speed": "/bandwidth_test",
    "telemetry": "/telemetry", "system scan": "/telemetry",
    "diagnostic": "/diagnostics", "check health": "/diagnostics",
    
    "list processes": "/list_processes", "top processes": "/list_processes",
    "sleep": "/system_sleep", "hibernate": "/system_sleep",
    "lock pc": "/system_lock_station", "lock screen": "/system_lock_station", "secure station": "/system_lock_station",
    "minimize": "/minimize_all", "show desktop": "/minimize_all",
    "screenshot": "/screenshot", "capture screen": "/screenshot",
    
    "turn it up": "/volume_up", "volume up": "/volume_up", "louder": "/volume_up",
    "turn it down": "/volume_down", "volume down": "/volume_down", "quieter": "/volume_down",
    "mute": "/mute_audio", "silence": "/mute_audio",
    "pause": "/play_pause", "resume": "/play_pause", "play song": "/play_pause",
    "next track": "/next_track", "skip track": "/next_track",
    "previous track": "/prev_track", "go back": "/prev_track",
    
    "notepad": "/open_notepad", "editor": "/open_notepad",
    "calculator": "/open_calculator", "calc": "/open_calculator",
    "terminal": "/open_terminal", "command prompt": "/open_terminal",
    "close chrome": "/close_browser", "kill browser": "/close_browser", "exit web": "/close_browser",
    "help": "/help", "instruction": "/help", "commands": "/help",
    "news": "/news_update", "world update": "/news_update",
    
    "what can you do": "/who_are_you", "who are you": "/who_are_you",
    "hello friday": "/say_hello", "do you copy": "/say_hello", "are you there": "/say_hello", "do you read": "/say_hello"
}

def find_best_intent(phrase):
    # 1. Exact map match
    if phrase in VOICE_MAP:
        return VOICE_MAP[phrase]
    
    # 2. Fuzzy Keyword Scoring
    phrase_words = set(re.findall(r'\w+', phrase))
    best_match = None
    best_score = 0
    
    for key, val in VOICE_MAP.items():
        key_words = set(re.findall(r'\w+', key))
        if not key_words: continue
        overlap = len(phrase_words.intersection(key_words))
        score = overlap / len(key_words)
        if score > best_score:
            best_score = score
            best_match = val
            
    if best_score >= 0.5: # 50% keyword match minimum
        return best_match
        
    return None

def stdin_thread_worker():
    """Reads stdin line-by-line and pushes to input_queue securely."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line: 
                break
            line = line.strip()
            if line: 
                input_queue.put(line)
        except Exception: 
            break

# ─── TELEMETRY & LOGGING UTILS ─────────────────────────────────────────────
def get_telemetry():
    """Extracts system telemetry metrics using psutil safely."""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    try:
        conns = psutil.net_connections(kind='inet')
        established = sum(1 for c in conns if c.status == 'ESTABLISHED')
        net_count = established if established > 0 else len(conns)
    except Exception:
        try:
            net_count = sum(1 for _, s in psutil.net_if_stats().items() if s.isup)
        except Exception:
            net_count = 1
    return cpu, ram, net_count

def log(msg, type_str="INFO"):
    sys.stdout.write(f"[{type_str}] {msg}\n")
    sys.stdout.flush()

def emit_data(channel, payload_dict):
    packet = {"channel": channel, "data": payload_dict}
    sys.stdout.write(f"__METRIC__:{json.dumps(packet)}\n")
    sys.stdout.flush()

# ─── EXTENDED COMMAND ROUTER INTERFACE ─────────────────────────────────────
async def handle_command(cmd):
    cmd_clean = cmd.strip()
    if not cmd_clean: 
        return
    if cmd_clean.startswith('AUDIO_CHUNK:') or len(cmd_clean) > 2000: 
        return

    parts = cmd_clean.split()
    base_cmd = parts[0].lower()

    # If it's pure raw speech or missing the token prefix, normalize it
    if not base_cmd.startswith('/'):
        cmd_lower = cmd_clean.lower()
        
        # Invoke FRIDAY Advanced Fuzzy Intent Matching
        intent = find_best_intent(cmd_lower)
        if intent:
            base_cmd = intent
            parts = [base_cmd] + parts[1:]
        
        # Regex/Context Gated Pattern Matching For Argument Extraction
        if any(w in cmd_lower for w in ["privacy", "shield", "mute mic"]):
            log("Privacy shield state acknowledged by FRIDAY.", "SYSTEM")
            return
            
        elif "youtube" in cmd_lower and "play" in cmd_lower:
            base_cmd = "/play_on_youtube"
            song_match = re.search(r"play\s+(.+)", cmd_lower)
            song_name = song_match.group(1).replace("on youtube", "").replace("youtube", "").strip() if song_match else ""
            parts = ["/play_on_youtube", song_name]
            
        elif cmd_lower.startswith("play ") or ("play" in cmd_lower and "song" in cmd_lower) or "spotify" in cmd_lower:
            base_cmd = "/open_spotify"
            song_match = re.search(r"play\s+(.+)", cmd_lower)
            song_name = song_match.group(1).replace("on spotify", "").replace("spotify", "").strip() if song_match else ""
            parts = ["/open_spotify", song_name]
            
        elif "weather" in cmd_lower or "whether" in cmd_lower:
            base_cmd = "/weather_report"
            loc_match = re.search(r"(?:in|for|at)\s+([a-z0-9\s]+)", cmd_lower)
            loc = loc_match.group(1).strip() if loc_match else ""
            parts = ["/weather_report", loc]
            
        elif any(w in cmd_lower for w in ["open browser to", "go to", "navigate to"]):
            base_cmd = "/open_browser_to"
            if "github" in cmd_lower or "git" in cmd_lower: parts = ["/open_browser_to", "github"]
            elif "stack" in cmd_lower or "overflow" in cmd_lower: parts = ["/open_browser_to", "stack"]
            elif "youtube" in cmd_lower: parts = ["/open_browser_to", "youtube"]
            else: parts = ["/open_browser_to", "google"]
            
        elif "run task" in cmd_lower or "execute script" in cmd_lower:
            base_cmd = "/run_automation_script"
            if "test" in cmd_lower: parts = ["/run_automation_script", "test"]
            elif "backup" in cmd_lower: parts = ["/run_automation_script", "backup"]
            elif "clean" in cmd_lower: parts = ["/run_automation_script", "clean"]
            else: parts = ["/run_automation_script", "none"]

    # Import the modular command registry layout dynamically
    try:
        import friday_commands
        log(f"Received instruction routing token: {base_cmd}", "USER")
        # Route processing task safely out to the master command execution loops
        await friday_commands.execute(base_cmd, parts)
    except ImportError:
        log("friday_commands subsystem mapping missing in local folder hierarchy.", "ERROR")
    except Exception as e:
        log(f"Asynchronous pipeline breakdown on {base_cmd}: {str(e)}", "WARNING")

# ─── CORE ASYNC LOOPS ──────────────────────────────────────────────────────
async def telemetry_loop():
    while True:
        cpu, ram, net = get_telemetry()
        emit_data("telemetry", {"cpu": cpu, "ram": ram, "net": net})
        await asyncio.sleep(3)

async def command_processor():
    while True:
        while not input_queue.empty():
            try:
                cmd = input_queue.get_nowait()
                await handle_command(cmd)
            except queue.Empty:
                break
        await asyncio.sleep(0.05)

async def main():
    hr = datetime.datetime.now().hour
    if hr < 12: greeting = "Good morning Boss."
    elif hr < 17: greeting = "Good afternoon Boss."
    else: greeting = "Good evening Boss."
    
    log("=============================================================", "CORE")
    log("   FRIDAY AMBIENT ENGINE v3 — HYBRID VOICE CORE ACTIVE", "CORE")
    log("   SpeechRecognition: browser-side | Privacy Shield: armed", "CORE")
    log("=============================================================", "CORE")
    log(f"{greeting} FRIDAY ambient engine is online.", "AGENT")
    
    await asyncio.gather(
        telemetry_loop(),
        command_processor()
    )

if __name__ == "__main__":
    t = threading.Thread(target=stdin_thread_worker, daemon=True)
    t.start()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("FRIDAY core offline.", "SYSTEM")
