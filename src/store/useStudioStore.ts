import { create } from 'zustand';

type Project = { id: string; title: string; description: string; storyText: string };
type Backend = { id: string; name: string; type: string; baseUrl: string; defaultModel: string };

type StudioState = {
  projects: Project[];
  activeProjectId: string | null;
  backends: Backend[];
  selectedBackendId: string | null;
  model: string;
  temperature: number;
  maxTokens: number;
  chunkWords: number;
  nextChunkGuidance: string;
  compiledPromptPreview: string;
  loadAll: () => Promise<void>;
  createProject: (title: string) => Promise<void>;
  setActiveProject: (id: string) => void;
  updateStoryText: (text: string) => Promise<void>;
  addBackend: (payload: Omit<Backend, 'id'> & { apiKey?: string }) => Promise<void>;
  setSelectedBackend: (id: string) => void;
  setSetting: (key: 'temperature' | 'maxTokens' | 'chunkWords', value: number) => void;
  setNextChunkGuidance: (value: string) => void;
  setModel: (value: string) => void;
  setCompiledPromptPreview: (value: string) => void;
};

export const useStudioStore = create<StudioState>((set, get) => ({
  projects: [],
  activeProjectId: null,
  backends: [],
  selectedBackendId: null,
  model: '',
  temperature: 0.9,
  maxTokens: 500,
  chunkWords: 120,
  nextChunkGuidance: '',
  compiledPromptPreview: '',
  async loadAll() {
    const [projects, backends] = await Promise.all([window.storyStudio.listProjects(), window.storyStudio.listBackends()]);
    set({
      projects,
      activeProjectId: projects[0]?.id ?? null,
      backends,
      selectedBackendId: backends[0]?.id ?? null,
      model: backends[0]?.defaultModel ?? ''
    });
  },
  async createProject(title) {
    await window.storyStudio.createProject({ title });
    await get().loadAll();
  },
  setActiveProject(id) {
    set({ activeProjectId: id });
  },
  async updateStoryText(text) {
    const projectId = get().activeProjectId;
    if (!projectId) return;
    await window.storyStudio.updateProjectText(projectId, text);
    set({ projects: get().projects.map((p) => (p.id === projectId ? { ...p, storyText: text } : p)) });
  },
  async addBackend(payload) {
    await window.storyStudio.addBackend(payload);
    await get().loadAll();
  },
  setSelectedBackend(id) {
    const backend = get().backends.find((x) => x.id === id);
    set({ selectedBackendId: id, model: backend?.defaultModel ?? get().model });
  },
  setSetting(key, value) {
    set({ [key]: value } as Pick<StudioState, 'temperature' | 'maxTokens' | 'chunkWords'>);
  },
  setNextChunkGuidance(nextChunkGuidance) {
    set({ nextChunkGuidance });
  },
  setModel(model) {
    set({ model });
  },
  setCompiledPromptPreview(compiledPromptPreview) {
    set({ compiledPromptPreview });
  }
}));
