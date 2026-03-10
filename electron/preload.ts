import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('storyStudio', {
  listProjects: () => ipcRenderer.invoke('projects:list'),
  createProject: (input: unknown) => ipcRenderer.invoke('projects:create', input),
  updateProjectText: (id: string, storyText: string) => ipcRenderer.invoke('projects:updateText', id, storyText),
  listBackends: () => ipcRenderer.invoke('models:listBackends'),
  addBackend: (payload: unknown) => ipcRenderer.invoke('models:addBackend', payload),
  testBackend: (id: string) => ipcRenderer.invoke('models:testBackend', id),
  generate: (payload: unknown) => ipcRenderer.invoke('inference:generate', payload),
  addHistory: (payload: unknown) => ipcRenderer.invoke('history:add', payload),
  listHistory: (projectId: string) => ipcRenderer.invoke('history:list', projectId)
});
