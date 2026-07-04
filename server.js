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
  console.log("Initializing Python Agent subprocess...");
  const agentPath = path.join(__dirname, 'agent.py');
  
  let interpreter = process.platform === 'win32' ? 'python' : 'python3';
  trySpawn(interpreter, agentPath);
}

function trySpawn(interpreter, agentPath) {
  console.log(`Spawning python process: ${interpreter} ${agentPath}`);
  pythonProcess = spawn(interpreter, [agentPath], {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString();
    const lines = output.split(/\r?\n/);
    
    lines.forEach((line) => {
      if (!line.trim()) return;

      // Intercept structural metric updates
      if (line.startsWith('__METRIC__:')) {
        try {
          const rawJson = line.replace('__METRIC__:', '');
          const parsed = JSON.parse(rawJson);
          broadcast({ type: 'metric', channel: parsed.channel, data: parsed.data });
        } catch (e) {
          console.error("Metric decoding collision:", e.message);
        }
      } else {
        // Standard structural terminal logging strings
        broadcast({ type: 'stdout', message: line });
      }
    });
  });

  pythonProcess.stderr.on('data', (data) => {
    const errorStr = data.toString();
    console.error(`[Python Stderr]: ${errorStr.trim()}`);
    broadcast({ type: 'stderr', message: errorStr });
  });

  pythonProcess.on('error', (err) => {
    console.error(`Failed to start python subprocess via ${interpreter}:`, err.message);
    if (interpreter === 'python3') {
      trySpawn('python', agentPath);
    } else if (interpreter === 'python') {
      trySpawn('py', agentPath);
    } else {
      console.error("Fatal: Unable to spawn Python execution runtime.");
      broadcast({ type: 'error', message: 'Fatal: Python subprocess failed to launch.' });
    }
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python subprocess terminated with exit code ${code}`);
    if (code !== null) {
      broadcast({ type: 'system', message: `Python subprocess exited with code ${code}. Respawning...` });
      pythonProcess = null;
      setTimeout(spawnPythonAgent, 5000);
    }
  });
}

function broadcast(data) {
  const payload = JSON.stringify(data);
  wss.clients.forEach((client) => {
    if (client.readyState === 1) {
      client.send(payload);
    }
  });
}

wss.on('connection', (ws) => {
  console.log('Dashboard web client connected.');
  ws.send(JSON.stringify({ type: 'system', message: 'IPC gateway connection active. Core link initialized.' }));

  ws.on('message', (message) => {
    const command = message.toString();
    if (pythonProcess && pythonProcess.stdin.writable) {
      pythonProcess.stdin.write(command + '\n');
    } else {
      ws.send(JSON.stringify({ type: 'error', message: 'Python agent interface offline.' }));
    }
  });
});

// Avoid dangling zombie processes on forced exit
process.on('SIGINT', () => {
  console.log("\nTearing down system environments. Safely disposing sub-processes...");
  if (pythonProcess) {
    pythonProcess.kill('SIGINT');
  }
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log("\nSIGTERM received. Disposing sub-processes...");
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
  }
  process.exit(0);
});

const PORT = 5000;
server.listen(PORT, () => {
  console.log(`=============================================================`);
  console.log(`   JARVIS CORE INTERPROCESS GATEWAY ACTIVE ON PORT ${PORT}`);
  console.log(`=============================================================`);
  spawnPythonAgent();
});
