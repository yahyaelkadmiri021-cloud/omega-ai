// OMEGA AI — Electron main process (shell scaffold v0.1.0)
// Loads the dependency-free dashboard; React + TypeScript replaces it
// when `npm install` lands (Phase 3/11). No build step needed for this file.
'use strict';

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const http = require('http');

const BRIDGE_URL = 'http://127.0.0.1:8471';
const DASHBOARD = path.join(__dirname, '..', 'dashboard', 'index.html');

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    backgroundColor: '#0b0f14',
    title: 'OMEGA AI',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.loadFile(DASHBOARD);
  mainWindow.on('closed', () => { mainWindow = null; });
}

// --- bridge proxy (read-only; execution goes through the permission gate) ---
function bridgeGet(pathname) {
  return new Promise((resolve) => {
    http.get(BRIDGE_URL + pathname, (res) => {
      let body = '';
      res.on('data', (c) => { body += c; });
      res.on('end', () => {
        try { resolve({ ok: res.statusCode < 300, data: JSON.parse(body) }); }
        catch (e) { resolve({ ok: false, data: null, error: 'bad-json: ' + e.message }); }
      });
    }).on('error', (e) => resolve({ ok: false, data: null, error: 'bridge-unreachable: ' + e.message }));
  });
}

// Permission gate (mirrors core/permissions.py GREEN/YELLOW/RED).
// GREEN: allowed. YELLOW: returns needs_approval (dashboard shows the request).
// RED: refused outright — explicit approval in the app is a Phase 4 feature.
function gate(action) {
  const RED = ['delete', 'pay', 'purchase', 'install', 'publish', 'send-external'];
  const YELLOW = ['run-objective', 'upload', 'write-outside-workspace'];
  if (RED.includes(action)) return { allowed: false, reason: 'RED action — explicit approval required (Phase 4)' };
  if (YELLOW.includes(action)) return { allowed: false, needsApproval: true, reason: 'YELLOW action — needs your confirmation' };
  return { allowed: true };
}

ipcMain.handle('omega-status', async () => bridgeGet('/status'));
ipcMain.handle('omega-agents', async () => bridgeGet('/agents'));
ipcMain.handle('omega-memory', async () => bridgeGet('/memory'));
ipcMain.handle('omega-gate', async (_event, action) => gate(action));

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
