import Database from 'better-sqlite3';
import crypto from 'node:crypto';

export type BackendRow = {
  id: string;
  type: 'lmstudio' | 'ollama' | 'openai';
  name: string;
  baseUrl: string;
  apiKey: string | null;
  defaultModel: string;
  status: string;
};

let db: Database.Database;

export const initDatabase = (filePath: string) => {
  db = new Database(filePath);
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS projects (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      tags TEXT DEFAULT '',
      activeModelId TEXT DEFAULT '',
      activePresetId TEXT DEFAULT '',
      storyText TEXT DEFAULT '',
      createdAt TEXT NOT NULL,
      updatedAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS backends (
      id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      name TEXT NOT NULL,
      baseUrl TEXT NOT NULL,
      apiKey TEXT,
      defaultModel TEXT NOT NULL,
      status TEXT NOT NULL,
      createdAt TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS generation_history (
      id TEXT PRIMARY KEY,
      projectId TEXT NOT NULL,
      actionType TEXT NOT NULL,
      prompt TEXT NOT NULL,
      outputText TEXT NOT NULL,
      modelUsed TEXT NOT NULL,
      parametersJson TEXT NOT NULL,
      accepted INTEGER NOT NULL DEFAULT 0,
      createdAt TEXT NOT NULL
    );
  `);
};

const id = () => crypto.randomUUID();
const now = () => new Date().toISOString();

export const repo = {
  listProjects: () => db.prepare('SELECT * FROM projects ORDER BY updatedAt DESC').all(),
  createProject: (input: { title: string; description?: string }) => {
    const row = {
      id: id(),
      title: input.title,
      description: input.description ?? '',
      tags: '',
      activeModelId: '',
      activePresetId: '',
      storyText: '',
      createdAt: now(),
      updatedAt: now()
    };
    db.prepare(
      `INSERT INTO projects (id, title, description, tags, activeModelId, activePresetId, storyText, createdAt, updatedAt)
       VALUES (@id, @title, @description, @tags, @activeModelId, @activePresetId, @storyText, @createdAt, @updatedAt)`
    ).run(row);
    return row;
  },
  updateProjectText: (id: string, storyText: string) =>
    db.prepare('UPDATE projects SET storyText = ?, updatedAt = ? WHERE id = ?').run(storyText, now(), id),
  listBackends: () => db.prepare('SELECT * FROM backends ORDER BY createdAt DESC').all() as BackendRow[],
  addBackend: (input: Omit<BackendRow, 'id' | 'status'>) => {
    const row = { ...input, id: id(), status: 'unknown', createdAt: now() };
    db.prepare(
      `INSERT INTO backends (id, type, name, baseUrl, apiKey, defaultModel, status, createdAt)
       VALUES (@id, @type, @name, @baseUrl, @apiKey, @defaultModel, @status, @createdAt)`
    ).run(row);
    return row;
  },
  getBackend: (id: string) => db.prepare('SELECT * FROM backends WHERE id = ?').get(id) as BackendRow | undefined,
  addHistory: (input: {
    projectId: string;
    actionType: string;
    prompt: string;
    outputText: string;
    modelUsed: string;
    parametersJson: string;
    accepted?: number;
  }) => {
    db.prepare(
      `INSERT INTO generation_history (id, projectId, actionType, prompt, outputText, modelUsed, parametersJson, accepted, createdAt)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(id(), input.projectId, input.actionType, input.prompt, input.outputText, input.modelUsed, input.parametersJson, input.accepted ?? 0, now());
  },
  listHistory: (projectId: string) =>
    db.prepare('SELECT * FROM generation_history WHERE projectId = ? ORDER BY createdAt DESC LIMIT 100').all(projectId)
};
