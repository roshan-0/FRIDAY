import express from 'express';
import http from 'http';
import { WebSocketServer } from 'ws';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

app.use(express.static(path.join(__dirname, 'public')));

let pythonProcess = null;

function spawnPythonAgent() {
  console.log("Initializing Ambient Python Agent (text-mode)...");
  const agentPath = path.join(__dirname, 'agent_2.py');
  const interpreter = process.platform === 'win32' ? 'python' : 'python3';
  trySpawn(interpreter, agentPath);
}

function trySpawn(interpreter, agentPath) {
  console.log(`Spawning: ${interpreter} ${agentPath}`);
  pythonProcess = spawn(interpreter, [agentPath], {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString();
    const lines = output.split(/\r?\n/);
    lines.forEach((line) => {
      if (!line.trim()) return;
      if (line.startsWith('__METRIC__:')) {
        try {
          const parsed = JSON.parse(line.replace('__METRIC__:', ''));
          broadcast({ type: 'metric', channel: parsed.channel, data: parsed.data });
        } catch (e) {
          console.error("Metric decode error:", e.message);
        }
      } else {
        console.log(`[PYTHON] ${line}`);
        broadcast({ type: 'stdout', message: line });
      }
    });
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Stderr]: ${data.toString().trim()}`);
    broadcast({ type: 'stderr', message: data.toString() });
  });

  pythonProcess.on('error', (err) => {
    console.error(`Spawn failed (${interpreter}):`, err.message);
    if (interpreter === 'python3') trySpawn('python', agentPath);
    else if (interpreter === 'python') trySpawn('py', agentPath);
    else broadcast({ type: 'error', message: 'Fatal: Ambient agent failed to launch.' });
  });

  pythonProcess.on('close', (code) => {
    console.log(`Ambient agent exited: ${code}`);
    if (code !== null) {
      broadcast({ type: 'system', message: `Ambient agent exited (${code}). Respawning in 5s...` });
      pythonProcess = null;
      setTimeout(spawnPythonAgent, 5000);
    }
  });
}

function broadcast(data) {
  const payload = JSON.stringify(data);
  wss.clients.forEach((client) => {
    if (client.readyState === 1) client.send(payload);
  });
}

wss.on('connection', (ws) => {
  console.log('Client connected to ambient gateway.');
  ws.send(JSON.stringify({ type: 'system', message: 'Ambient IPC gateway active. Hybrid voice engine armed.' }));

  ws.on('message', (message, isBinary) => {
    if (isBinary) {
      // Binary audio blobs from MediaRecorder — silently drop.
      // Transcription is handled browser-side by SpeechRecognition.
      // MediaRecorder is used ONLY for the privacy gate state tracking.
      return;
    }
    // Text frame: either a typed command or a SpeechRecognition transcript
    const command = message.toString().trim();
    if (!command) return;

    // Drop abnormally large payloads to prevent buffer issues
    if (command.length > 5000) {
      console.log(`[Dropped] Ignored abnormally large payload.`);
      return;
    }

    console.log(`[Ambient Command] > ${command}`);
    if (pythonProcess && pythonProcess.stdin.writable) {
      pythonProcess.stdin.write(command + '\n');
    } else {
      ws.send(JSON.stringify({ type: 'error', message: 'Ambient agent offline. Command dropped.' }));
    }
  });

  ws.on('close', () => console.log('Client disconnected from ambient gateway.'));
});

process.on('SIGINT', () => {
  console.log('\nDisposing ambient agent...');
  if (pythonProcess) pythonProcess.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  if (pythonProcess) pythonProcess.kill('SIGTERM');
  process.exit(0);
});

const PORT = 5001;
server.listen(PORT, () => {
  console.log(`=============================================================`);
  console.log(`   JARVIS AMBIENT GATEWAY (HYBRID MODE) — PORT ${PORT}`);
  console.log(`   Access Ambient Dashboard at: http://localhost:${PORT}`);
  console.log(`=============================================================`);
  spawnPythonAgent();
});
