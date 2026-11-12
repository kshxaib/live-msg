const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const { WebSocketServer } = require('ws');

const PORT = 3000;
let messages = [];

// Helper to get local Wi-Fi / LAN IP
function getLocalIp() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }
    return '127.0.0.1';
}

// 1. HTTP Server
const server = http.createServer((req, res) => {
    const filePath = path.join(__dirname, 'index.html');
    fs.readFile(filePath, (err, content) => {
        if (err) {
            res.writeHead(500);
            res.end('Error loading index.html');
            return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(content);
    });
});

// 2. WebSocket Server
const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
    // Send message history to newcomer
    ws.send(JSON.stringify({
        type: 'INIT_HISTORY',
        messages: messages
    }));

    ws.on('message', (data) => {
        try {
            const parsed = JSON.parse(data.toString());
            if (parsed.type === 'NEW_MESSAGE') {
                messages.push(parsed.payload);
                wss.clients.forEach((client) => {
                    if (client.readyState === 1) {
                        client.send(JSON.stringify({
                            type: 'NEW_MESSAGE',
                            payload: parsed.payload
                        }));
                    }
                });
            } else if (parsed.type === 'CLEAR') {
                messages = [];
                wss.clients.forEach((client) => {
                    if (client.readyState === 1) {
                        client.send(JSON.stringify({ type: 'CLEAR' }));
                    }
                });
            }
        } catch (e) {
            console.error('Error handling message:', e);
        }
    });
});

// Start Server and Public Tunnel
server.listen(PORT, () => {
    const localIp = getLocalIp();

    console.log(`Server is running!`);
    console.log(``);
    console.log(`Local:        http://localhost:${PORT}`);
    console.log(`Same Wi-Fi:   http://${localIp}:${PORT}`);
    console.log(``);
    console.log(`Generating public link for friends on mobile data...`);

    // Start public tunnel via Pinggy SSH (zero password, works on mobile data globally)
    const tunnel = spawn('ssh', [
        '-p', '443',
        '-o', 'StrictHostKeyChecking=no',
        '-R0:localhost:3000',
        'a.pinggy.io'
    ]);

    let linkPrinted = false;

    function parseOutput(data) {
        if (linkPrinted) return;
        const text = data.toString();
        const match = text.match(/https:\/\/[a-zA-Z0-9-]+\.(free\.pinggy\.net|run\.pinggy-free\.link)/);
        if (match) {
            linkPrinted = true;
            console.log(``);
            console.log(`--------------------------------------------------`);
            console.log(`Share this link with your friend (Mobile Data / Internet):`);
            console.log(match[0]);
            console.log(`--------------------------------------------------`);
            console.log(``);
        }
    }

    tunnel.stdout.on('data', parseOutput);
    tunnel.stderr.on('data', parseOutput);

    tunnel.on('error', (err) => {
        console.log(`(Public tunnel could not start automatically: ${err.message})`);
    });

    // Cleanup on Ctrl+C
    process.on('SIGINT', () => {
        tunnel.kill();
        process.exit();
    });
});
