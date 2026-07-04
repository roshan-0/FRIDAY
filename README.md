# F.R.I.D.A.Y. Ambient AI Core

F.R.I.D.A.Y. is an advanced, hybrid voice-activated AI engine featuring a Node.js interprocess gateway and a robust Python-based background agent network. It is designed around a multi-agent orchestrated architecture, operating seamlessly as a background ambient assistant with a modern, sci-fi inspired dashboard.

## 🚀 Key Features

* **Hybrid Engine Architecture:** 
  * A **Node.js (Express/Socket.io)** frontend acts as the WebSocket IPC conduit, handling browser-side Speech Recognition seamlessly.
  * A **Python (Asyncio)** backend acts as the core brain, processing natural language through fuzzy intent matching algorithms.
* **ADK Multi-Agent Orchestration:** Specialized, decoupled persona sub-agents (`TelemetryAgent`, `AutomationAgent`) independently handle diagnostic tasks and environment scripts.
* **MCP Schema Integration:** Utilizes Model Context Protocol (MCP) packet structuring for standardized, JSON-RPC communication between the voice client and the backend subsystems.
* **Advanced Ambient Capabilities:**
  * **Global Intel:** Fetches top Google News RSS headlines and local weather API data (based automatically on your IP) and reads them dynamically via TTS.
  * **OS Media Hooking:** Intercepts system-level media keys (Play, Pause, Next, Previous) using `ctypes` global keyboard hooks to natively control Spotify, VLC, YouTube, or any active media.
  * **Deep Integrations:** Directly launches local applications (Spotify desktop) and browser URLs reliably.
* **Strict Security Sandboxing:** The `AutomationAgent` runs scripts through an immutable whitelist, enforcing a strict `shell=False` execution layer to prevent arbitrary code injection.

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript (Web Speech API for STT and TTS)
* **Gateway Layer:** Node.js, Express, Socket.io
* **Agent Core:** Python 3, Asyncio, Psutil, Ctypes

## ⚙️ Installation & Setup

1. **Install Node Dependencies:**
   ```bash
   npm install
   ```

2. **Install Python Dependencies:**
   Ensure Python is installed, then install the required telemetry library:
   ```bash
   pip install psutil
   ```

3. **Start the System:**
   You can boot the entire F.R.I.D.A.Y. engine with a single command:
   ```bash
   npm start
   ```
   *This automatically starts the Node gateway and spawns the Python agent in the background.*

4. **Access the Dashboard:**
   Open your browser and navigate to `http://localhost:5001`. Allow microphone permissions to activate the ambient listening core.

## 🎙️ Command Matrix

F.R.I.D.A.Y. supports fluid, natural language commands. Example phrases include:

* *"Hello"* / *"Who are you?"*
* *"What's the weather in London?"* / *"World update"*
* *"Open Spotify"* / *"Play Shape of You on Spotify"*
* *"Play [Video Name] on YouTube"*
* *"Pause"* / *"Next track"* / *"Previous track"*
* *"System scan"* / *"Telemetry"* (Requires `run task test` integration)
* *"Run task test"* (Triggers the sandboxed automation engine)

## 🛡️ Architecture & Security

The system employs **Concept 3 Security Features**, meaning raw string inputs from the voice processor are never passed directly to the shell. The `AutomationAgent` enforces an absolute whitelist mechanism, securely passing defined arguments via Python's `subprocess` module to eliminate command injection vectors.
