import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'node:path';
import { initDatabase, repo } from './persistence.js';
import { backendRegistry } from './services/backendRegistry.js';

const isDev = !app.isPackaged;

const createWindow = async () => {
  const win = new BrowserWindow({
    width: 1520,
    height: 940,
    backgroundColor: '#0b1020',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (isDev) {
    await win.loadURL('http://localhost:5173');
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    await win.loadFile(path.join(__dirname, '../dist/index.html'));
  }
};

app.whenReady().then(() => {
  initDatabase(path.join(app.getPath('userData'), 'story-studio.db'));

  ipcMain.handle('projects:list', () => repo.listProjects());
  ipcMain.handle('projects:create', (_e, input) => repo.createProject(input));
  ipcMain.handle('projects:updateText', (_e, id: string, storyText: string) => repo.updateProjectText(id, storyText));
  ipcMain.handle('models:listBackends', () => repo.listBackends());
  ipcMain.handle('models:addBackend', (_e, payload) => repo.addBackend(payload));
  ipcMain.handle('models:testBackend', async (_e, id: string) => {
    const backend = repo.getBackend(id);
    if (!backend) {
      return { ok: false, message: 'Backend not found.' };
    }
    return backendRegistry.testConnection(backend);
  });
  ipcMain.handle('inference:generate', async (_e, payload) => backendRegistry.generate(payload));
  ipcMain.handle('history:add', (_e, payload) => repo.addHistory(payload));
  ipcMain.handle('history:list', (_e, projectId: string) => repo.listHistory(projectId));

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
