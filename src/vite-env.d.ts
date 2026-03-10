/// <reference types="vite/client" />

declare global {
  interface Window {
    storyStudio: {
      listProjects: () => Promise<any[]>;
      createProject: (input: { title: string; description?: string }) => Promise<any>;
      updateProjectText: (id: string, storyText: string) => Promise<void>;
      listBackends: () => Promise<any[]>;
      addBackend: (payload: any) => Promise<any>;
      testBackend: (id: string) => Promise<{ ok: boolean; message: string }>;
      generate: (payload: any) => Promise<{ output: string; compiledPrompt: string }>;
      addHistory: (payload: any) => Promise<void>;
      listHistory: (projectId: string) => Promise<any[]>;
    };
  }
}

export {};
