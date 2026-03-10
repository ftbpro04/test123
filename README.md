# Story Studio (Electron + React + TypeScript)

Story Studio is a local-first fiction writing workbench designed around projects, generation controls, and non-destructive editing workflows.

## What you can do right now

- Create and switch writing projects.
- Write directly in a large editor canvas.
- Connect to model backends (LM Studio / OpenAI-compatible / Ollama).
- Generate story text (create/continue/rewrite).
- Rewrite selected text only.
- Track generation history in local SQLite storage.
- See live character, word, and rough token counts.

## Beginner Quick Start (No Coding Experience)

If this is your first time running an app from source, follow these exact steps.

### 1) Install required apps

- **Git**: https://git-scm.com/downloads
- **Node.js 20+ (LTS recommended)**: https://nodejs.org/

After installing, open Terminal (macOS/Linux) or PowerShell (Windows) and verify:

```bash
git --version
node --version
npm --version
```

### 2) Download this project

If you have a repo URL, run:

```bash
git clone <REPO_URL>
cd test123
```

If you already downloaded a ZIP, extract it and `cd` into the extracted folder.

### 3) Install project dependencies

```bash
npm install
```

### 4) Build the app

```bash
npm run build
```

### 5) Start Story Studio

```bash
npm run dev
```

This launches:
- the React UI (Vite)
- the Electron desktop window

## First-time app test flow (super simple)

1. Click **+ New Project**.
2. Type some text in the editor.
3. Confirm bottom bar updates chars/words/tokens.
4. In **Model + Backend**, pick your backend and model.
5. In **Generate**, click **Continue**.
6. Highlight a paragraph and click **Rewrite Selection**.

If those steps work, your setup is good.

## Connecting a local model (LM Studio example)

1. Open LM Studio.
2. Load your model (example: Qwen 3.5 9B).
3. Start LM Studio local server (OpenAI-compatible mode).
4. In Story Studio, add backend with your LM Studio URL (usually `http://127.0.0.1:1234`).
5. Set model name to the one shown by LM Studio.

## Common errors and fixes

### `npm install` fails

- Make sure your internet is working.
- Update Node.js to latest LTS.
- Try:
  ```bash
  npm cache clean --force
  npm install
  ```

### Electron window does not open

- Ensure `npm run build` completed before `npm run dev`.
- Close old processes and run dev again.

### Backend connection fails

- Confirm local server is running.
- Check URL and port.
- If using API key, verify it is correct.

## Architecture (for technical users)

- `electron/main.ts`: app lifecycle + IPC handlers.
- `electron/services/backendRegistry.ts`: backend abstraction and prompt compiler.
- `electron/persistence.ts`: SQLite schema and repository helpers.
- `src/App.tsx`: writer-focused UX and generation/edit flows.
- `src/store/useStudioStore.ts`: Zustand state management.

## Scripts

```bash
npm run dev        # run Vite + Electron
npm run build      # compile renderer + electron main/preload
npm run typecheck  # TypeScript checks
npm run lint       # ESLint checks
```

## Notes

This repository focuses on a strong V1 foundation and modular architecture so advanced systems (lore triggers, branching revisions, context inspector, diff tooling) can be added without redesigning core app flow.
