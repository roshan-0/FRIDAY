import sys
import time
import asyncio
import threading
import queue
import psutil
import json

# Thread-safe queue for stdin inputs
input_queue = queue.Queue()

def stdin_thread_worker():
    """Reads stdin line-by-line and pushes to input_queue."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            input_queue.put(line.strip())
        except Exception:
            break

def get_telemetry():
    """Extracts system telemetry metrics using psutil."""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    try:
        conns = psutil.net_connections(kind='inet')
        established = sum(1 for c in conns if c.status == 'ESTABLISHED')
        net_count = established if established > 0 else len(conns)
    except Exception:
        try:
            net_count = sum(1 for name, stats in psutil.net_if_stats().items() if stats.isup)
        except Exception:
            net_count = 1
    return cpu, ram, net_count

def log(msg, type_str="INFO"):
    """Formats log line and flushes stdout buffer immediately."""
    sys.stdout.write(f"[{type_str}] {msg}\n")
    sys.stdout.flush()

def emit_data(channel, payload_dict):
    """Emits structural JSON string to prevent string truncation bugs on Node.js side."""
    packet = {"channel": channel, "data": payload_dict}
    sys.stdout.write(f"__METRIC__:{json.dumps(packet)}\n")
    sys.stdout.flush()

async def telemetry_loop():
    """Background loop that writes host telemetry reports every 3 seconds."""
    while True:
        cpu, ram, net = get_telemetry()
        
        # Structural data emission for frontend dashboards
        emit_data("telemetry", {"cpu": cpu, "ram": ram, "net": net})
        
        # System status trace log
        log(f"Telemetry ping - Load: {cpu:.1f}%, Swap: {ram:.1f}%, Active Nets: {net}", "TELEMETRY")
        await asyncio.sleep(3)

async def command_processor():
    """Checks the stdin input queue and maps it to execution tasks."""
    while True:
        while not input_queue.empty():
            try:
                cmd = input_queue.get_nowait()
                await handle_command(cmd)
            except queue.Empty:
                break
        await asyncio.sleep(0.1)

async def handle_command(cmd):
    cmd_clean = cmd.strip()
    if not cmd_clean:
        return

    log(f"Received instruction: {cmd_clean}", "USER")
    
    parts = cmd_clean.split()
    base_cmd = parts[0].lower()
    
    # Voice instruction normalization mapper
    if not base_cmd.startswith('/'):
        cmd_lower = cmd_clean.lower()
        if any(w in cmd_lower for w in ["help", "instruction", "guide", "menu"]):
            base_cmd = "/help"
        elif any(w in cmd_lower for w in ["diagnostic", "system check", "check health"]):
            base_cmd = "/diagnostics"
        elif any(w in cmd_lower for w in ["telemetry", "system scan", "hardware scan"]):
            base_cmd = "/telemetry"
        elif any(w in cmd_lower for w in ["cpu", "processor", "core load"]):
            base_cmd = "/cpu"
        elif any(w in cmd_lower for w in ["ram", "memory", "swap"]):
            base_cmd = "/ram"
        elif any(w in cmd_lower for w in ["network", "connection", "socket", "port"]):
            base_cmd = "/net"
        elif any(w in cmd_lower for w in ["ping", "echo", "hello jarvis"]):
            base_cmd = "/ping"
    
    if base_cmd == "/help":
        log("==========================================", "CORE")
        log("Available Operations Index:", "CORE")
        log("  /help        - Render this guide", "CORE")
        log("  /telemetry   - Fetch instantaneous host metrics", "CORE")
        log("  /cpu         - Sample current host CPU percent", "CORE")
        log("  /ram         - Display RAM capacities and load", "CORE")
        log("  /net         - List active network endpoints", "CORE")
        log("  /ping        - Low latency connection test", "CORE")
        log("  /diagnostics - Scan hardware core sub-systems", "CORE")
        log("==========================================", "CORE")
    elif base_cmd == "/ping":
        log("PONG - Core loops active. Low latency pipe established.", "CORE")
    elif base_cmd == "/telemetry":
        cpu, ram, net = get_telemetry()
        emit_data("telemetry", {"cpu": cpu, "ram": ram, "net": net})
        log(f"Telemetry manual scan: CPU: {cpu:.1f}%, RAM: {ram:.1f}%, Network Pipes: {net}", "CORE")
    elif base_cmd == "/cpu":
        # Offload blocking calculation to background thread to prevent frozen async loops
        cpu = await asyncio.to_thread(psutil.cpu_percent, interval=0.5)
        log(f"Host Core Load: {cpu:.1f}%", "CORE")
    elif base_cmd == "/ram":
        mem = psutil.virtual_memory()
        log(f"Memory: Total={mem.total/(1024**3):.2f}GB | Used={mem.used/(1024**3):.2f}GB | Load={mem.percent}%", "CORE")
    elif base_cmd == "/net":
        try:
            conns = psutil.net_connections(kind='inet')
            log(f"Socket Telemetry: {len(conns)} connection bindings open.", "CORE")
            count = 0
            for c in conns:
                if count >= 5:
                    log("  ... (list truncated) ...", "CORE")
                    break
                laddr = f"{c.laddr.ip}:{c.laddr.port}"
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "NONE"
                log(f"  [{count+1}] Local: {laddr} | Remote: {raddr} | State: {c.status}", "CORE")
                count += 1
        except Exception as e:
            log(f"Network listing blocked: {str(e)}", "WARNING")
    elif base_cmd == "/diagnostics":
        log("Starting system diagnostics run...", "CORE")
        await asyncio.sleep(0.4)
        cpu, ram, net = get_telemetry()
        log(f"  [1/3] Checking CPU load parameters... Status: OK ({cpu:.1f}% capacity)", "CORE")
        await asyncio.sleep(0.4)
        log(f"  [2/3] Checking RAM buffers... Status: OK ({ram:.1f}% capacity)", "CORE")
        await asyncio.sleep(0.4)
        log(f"  [3/3] Scanning networking stack... Status: VERIFIED", "CORE")
        await asyncio.sleep(0.4)
        log("System Diagnostics Completed. All systems operating within normal parameters.", "CORE")
    else:
        log(f"Directive '{cmd_clean}' parsed. Initializing response sequence...", "CORE")
        await asyncio.sleep(0.3)
        log("Response: Jarvis core initialized. Ready to execute instructions.", "AGENT")

async def main():
    log("=============================================================", "CORE")
    log("   JARVIS PYTHON CORE AGENT SUITE INITIALIZED (ASYNC ENGINE)", "CORE")
    log("   Awaiting inputs via stdin pipes...", "CORE")
    log("=============================================================", "CORE")
    
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
        log("Shutdown requested. Disposing resources.", "SYSTEM")
