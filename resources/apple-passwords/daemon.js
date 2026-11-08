#!/usr/bin/env node
const http = require('http');
const net = require('net');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(process.env.HOME, '.local/share/xenon/apple-passwords');
const EXT_DIR = path.join(BASE_DIR, 'extension');
const PROFILE_DIR = path.join(BASE_DIR, 'chrome-profile');
const SOCKET_PATH = '/tmp/xenon_passwords.sock';
const HTTP_PORT = 9988;
const CDP_PORT = 9990;

let chromeProc = null;
let bridgeSockets = new Set();
let toHelperQueue = [];
let toHelperWaitingRes = null;
let isShuttingDown = false;
let cachedCapabilities = null;

// Ensure directories exist
fs.mkdirSync(PROFILE_DIR, { recursive: true });
const hostsDir = path.join(PROFILE_DIR, 'NativeMessagingHosts');
fs.mkdirSync(hostsDir, { recursive: true });
fs.copyFileSync(
  '/Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json',
  path.join(hostsDir, 'com.apple.passwordmanager.json')
);

// Inject relay script into extension background.js if not already present
const bgPath = path.join(EXT_DIR, 'background.js');
let bgCode = fs.readFileSync(bgPath, 'utf8');
const RELAY_MARKER = '/* XENON_RELAY_HOOK */';
if (!bgCode.includes(RELAY_MARKER)) {
  const hook = `
${RELAY_MARKER}
(function xenonRelayInit() {
  const DAEMON_PORT = ${HTTP_PORT};
  let active = false;

  function init() {
    if (!self.g_nativeAppPort) {
      setTimeout(init, 50);
      return;
    }
    if (active) return;
    active = true;

    self.g_nativeAppPort.onMessage.addListener((msg) => {
      fetch(\`http://127.0.0.1:\${DAEMON_PORT}/from_helper\`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(msg)
      }).catch(console.error);
    });

    self.g_nativeAppPort.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError ? chrome.runtime.lastError.message : 'disconnected';
      fetch(\`http://127.0.0.1:\${DAEMON_PORT}/helper_disconnected\`, {
        method: 'POST',
        body: String(err)
      }).catch(console.error);
    });

    async function poll() {
      try {
        const res = await fetch(\`http://127.0.0.1:\${DAEMON_PORT}/to_helper\`);
        if (res.ok) {
          const msg = await res.json();
          if (msg && msg !== 'heartbeat') {
            self.g_nativeAppPort.postMessage(msg);
          }
        }
      } catch (e) {
        await new Promise(r => setTimeout(r, 500));
      }
      poll();
    }
    poll();
  }
  init();
})();
`;
  fs.writeFileSync(bgPath, bgCode + '\n' + hook);
}

// HTTP Server for headless Chrome extension communication
const httpServer = http.createServer((req, res) => {
  if (req.url === '/to_helper') {
    if (toHelperQueue.length > 0) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(toHelperQueue.shift()));
    } else {
      toHelperWaitingRes = res;
    }
  } else if (req.url === '/from_helper' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      res.end('ok');
      try {
        const msg = JSON.parse(body);
        if (msg.cmd === 14) {
          cachedCapabilities = msg;
        }
        broadcastToBridges(msg);
      } catch (e) {
        console.error('Failed to parse from_helper msg:', e);
      }
    });
  } else if (req.url === '/helper_disconnected' && req.method === 'POST') {
    res.end('ok');
    console.warn('Apple Helper reported disconnected');
  } else {
    res.writeHead(404);
    res.end();
  }
});

function sendToHelper(msg) {
  if (toHelperWaitingRes) {
    const r = toHelperWaitingRes;
    toHelperWaitingRes = null;
    r.writeHead(200, { 'Content-Type': 'application/json' });
    r.end(JSON.stringify(msg));
  } else {
    toHelperQueue.push(msg);
  }
}

// Native Messaging packet framer: 4-byte LE unsigned int length + UTF-8 payload
function formatPacket(msg) {
  const jsonBuf = Buffer.from(JSON.stringify(msg), 'utf8');
  const headerBuf = Buffer.alloc(4);
  headerBuf.writeUInt32LE(jsonBuf.length, 0);
  return Buffer.concat([headerBuf, jsonBuf]);
}

function broadcastToBridges(msg) {
  const packet = formatPacket(msg);
  for (const socket of bridgeSockets) {
    try {
      socket.write(packet);
    } catch (e) {
      console.error('Error writing to bridge socket:', e);
    }
  }
}

// Start headless Chrome with unpacked extension
async function launchChrome() {
  if (chromeProc && !chromeProc.killed) return;

  const chromeBin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  chromeProc = cp.spawn(chromeBin, [
    '--headless=new',
    `--user-data-dir=${PROFILE_DIR}`,
    `--remote-debugging-port=${CDP_PORT}`,
    '--remote-allow-origins=*',
    '--enable-unsafe-extension-debugging',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    'about:blank'
  ], { stdio: 'ignore' });

  chromeProc.on('exit', (code) => {
    console.info(`Headless Chrome exited with code ${code}`);
    chromeProc = null;
  });

  // Connect via CDP WebSocket and load extension
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`);
      const data = await res.json();
      if (data.webSocketDebuggerUrl) {
        const ws = new WebSocket(data.webSocketDebuggerUrl);
        ws.onopen = () => {
          ws.send(JSON.stringify({
            id: 1,
            method: 'Extensions.loadUnpacked',
            params: { path: EXT_DIR }
          }));
        };
        ws.onmessage = (event) => {
          const resp = JSON.parse(event.data);
          if (resp.id === 1) {
            console.info('Apple Passwords extension successfully loaded in Chrome');
            ws.close();
          }
        };
        break;
      }
    } catch (e) {
      await new Promise(r => setTimeout(r, 200));
    }
  }
}

// UNIX Domain Socket Server for Xenon Bridge instances
try {
  if (fs.existsSync(SOCKET_PATH)) fs.unlinkSync(SOCKET_PATH);
} catch (e) {}

const unixServer = net.createServer((socket) => {
  console.info('Bridge connected to daemon');
  bridgeSockets.add(socket);

  if (cachedCapabilities) {
    try {
      socket.write(formatPacket(cachedCapabilities));
    } catch (e) {}
  }

  let buffer = Buffer.alloc(0);

  socket.on('data', (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length >= 4) {
      const msgLen = buffer.readUInt32LE(0);
      if (buffer.length < 4 + msgLen) {
        break;
      }
      const msgBuf = buffer.subarray(4, 4 + msgLen);
      buffer = buffer.subarray(4 + msgLen);
      try {
        const msg = JSON.parse(msgBuf.toString('utf8'));
        if (msg.cmd === 14 && cachedCapabilities) {
          socket.write(formatPacket(cachedCapabilities));
        } else {
          sendToHelper(msg);
        }
      } catch (e) {
        console.error('Error parsing packet from bridge:', e);
      }
    }
  });

  socket.on('close', () => {
    bridgeSockets.delete(socket);
    console.info('Bridge disconnected');
  });

  socket.on('error', (err) => {
    console.error('Bridge socket error:', err);
    bridgeSockets.delete(socket);
  });
});

async function start() {
  httpServer.listen(HTTP_PORT, '127.0.0.1', () => {
    console.info(`HTTP relay listening on 127.0.0.1:${HTTP_PORT}`);
  });

  unixServer.listen(SOCKET_PATH, () => {
    fs.chmodSync(SOCKET_PATH, 0o666);
    console.info(`UNIX socket listening on ${SOCKET_PATH}`);
  });

  await launchChrome();
}

function shutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.info('Shutting down daemon...');
  if (chromeProc) {
    try { chromeProc.kill('SIGTERM'); } catch (e) {}
  }
  try { httpServer.close(); } catch (e) {}
  try { unixServer.close(); } catch (e) {}
  try { if (fs.existsSync(SOCKET_PATH)) fs.unlinkSync(SOCKET_PATH); } catch (e) {}
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

start().catch(err => {
  console.error('Failed to start daemon:', err);
  shutdown();
});
