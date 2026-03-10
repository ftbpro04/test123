# Story Studio (Electron + React + TypeScript)

Story Studio is a local-first fiction writing workbench designed around projects, generation controls, and non-destructive editing workflows.

## Implemented V1 foundation

- Electron desktop shell with secure preload bridge IPC.
- React workspace with three-pane writer UI (projects, editor, action panel).
- SQLite persistence for projects, backends, and generation history.
- Backend adapter architecture with support for:
  - LM Studio / OpenAI-compatible servers (`/v1/chat/completions`)
  - Ollama (`/api/generate`)
- Story-first editing flow with:
  - Full story generation / continuation / rewrite actions
  - Selection rewrite action using scoped context
  - Chunk-size control and next-chunk guidance
  - Live character/word/token estimates
- Prompt transparency panel (compiled prompt preview).

## Architecture

- `electron/main.ts`: app lifecycle + IPC handlers.
- `electron/services/backendRegistry.ts`: backend abstraction and prompt compiler.
- `electron/persistence.ts`: schema and repository helpers.
- `src/App.tsx`: studio UX implementing core writing flows.
- `src/store/useStudioStore.ts`: project/model/generation state via Zustand.

## Run

```bash
npm install
npm run build
npm run dev
```

> `npm run dev` expects the Electron main process to be built first (`npm run build`).

## Notes

This repository focuses on a solid V1 foundation and modular architecture so more advanced subsystems (lorebook triggers, branching revisions, diff/compare, style cards, memory dashboard) can be layered without redesigning core data flow.
