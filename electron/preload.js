// OMEGA AI — preload (safe IPC bridge, contextIsolation on).
// The renderer never gets Node or Electron internals — only these calls.
'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('omega', {
  getStatus: () => ipcRenderer.invoke('omega-status'),
  getAgents: () => ipcRenderer.invoke('omega-agents'),
  getMemory: () => ipcRenderer.invoke('omega-memory'),
  gate: (action) => ipcRenderer.invoke('omega-gate', action),
});
