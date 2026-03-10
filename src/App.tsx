import { useEffect, useMemo, useState } from 'react';
import { tokenEstimate, wordCount } from './lib/stats';
import { useStudioStore } from './store/useStudioStore';

const nav = ['Projects', 'Editor', 'Generate', 'Edit / Rewrite', 'Lorebook / Context', 'Characters / World Info', 'Presets', 'Models', 'History / Versions', 'Exports / Backups', 'Settings'];

export const App = () => {
  const store = useStudioStore();
  const [instruction, setInstruction] = useState('Continue with rising tension and sensory detail.');
  const [selectionInstruction, setSelectionInstruction] = useState('Make this section more atmospheric and tense.');
  const [selection, setSelection] = useState('');

  useEffect(() => {
    store.loadAll();
  }, []);

  const activeProject = useMemo(
    () => store.projects.find((p) => p.id === store.activeProjectId) ?? null,
    [store.projects, store.activeProjectId]
  );

  const runGeneration = async (actionType: 'create' | 'continue' | 'rewrite' | 'edit-selection') => {
    const backend = store.backends.find((b) => b.id === store.selectedBackendId);
    if (!activeProject || !backend) return;

    const prompt = actionType === 'edit-selection' ? selectionInstruction : instruction;
    const response = await window.storyStudio.generate({
      backend,
      model: store.model,
      prompt: `${prompt}\n\nChunk target: ~${store.chunkWords} words. Guidance: ${store.nextChunkGuidance}`,
      maxTokens: store.maxTokens,
      temperature: store.temperature,
      actionType,
      selection,
      contextBefore: activeProject.storyText.slice(0, 500),
      contextAfter: activeProject.storyText.slice(-500)
    });
    store.setCompiledPromptPreview(response.compiledPrompt);
    const newText = actionType === 'edit-selection'
      ? activeProject.storyText.replace(selection, response.output)
      : `${activeProject.storyText}\n\n${response.output}`.trim();

    await store.updateStoryText(newText);
    await window.storyStudio.addHistory({
      projectId: activeProject.id,
      actionType,
      prompt,
      outputText: response.output,
      modelUsed: store.model,
      parametersJson: JSON.stringify({ temperature: store.temperature, maxTokens: store.maxTokens, chunkWords: store.chunkWords })
    });
  };

  const onSelectionCapture = (value: string, start: number, end: number) => {
    setSelection(value.substring(start, end));
  };

  return (
    <div className="app-shell">
      <aside className="left-rail">
        <h1>Story Studio</h1>
        <button onClick={() => store.createProject(`New Project ${store.projects.length + 1}`)}>+ New Project</button>
        <div className="project-list">
          {store.projects.map((p) => (
            <button key={p.id} className={store.activeProjectId === p.id ? 'active' : ''} onClick={() => store.setActiveProject(p.id)}>
              {p.title}
            </button>
          ))}
        </div>
        <nav>
          {nav.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </nav>
      </aside>

      <main className="editor-pane">
        <header>
          <h2>{activeProject?.title ?? 'No project selected'}</h2>
        </header>
        <textarea
          value={activeProject?.storyText ?? ''}
          onChange={(event) => store.updateStoryText(event.target.value)}
          onSelect={(event) =>
            onSelectionCapture(
              event.currentTarget.value,
              event.currentTarget.selectionStart,
              event.currentTarget.selectionEnd
            )
          }
          placeholder="Write your story here, or generate with AI..."
        />
        <footer>
          <span>Chars: {activeProject?.storyText.length ?? 0}</span>
          <span>Words: {wordCount(activeProject?.storyText ?? '')}</span>
          <span>Tokens (est): {tokenEstimate(activeProject?.storyText ?? '')}</span>
          <span>Selection: {selection.length} chars</span>
        </footer>
      </main>

      <aside className="right-panel">
        <section>
          <h3>Model + Backend</h3>
          <select value={store.selectedBackendId ?? ''} onChange={(event) => store.setSelectedBackend(event.target.value)}>
            {store.backends.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.type})</option>
            ))}
          </select>
          <input value={store.model} onChange={(event) => store.setModel(event.target.value)} placeholder="Model name" />
        </section>

        <section>
          <h3>Chunked Guided Generation</h3>
          <label>Chunk size (words): {store.chunkWords}</label>
          <input type="range" min={40} max={500} value={store.chunkWords} onChange={(e) => store.setSetting('chunkWords', Number(e.target.value))} />
          <input value={store.nextChunkGuidance} onChange={(event) => store.setNextChunkGuidance(event.target.value)} placeholder="Guidance for next chunk" />
        </section>

        <section>
          <h3>Advanced Inference</h3>
          <label>Temperature</label>
          <input type="number" step="0.1" value={store.temperature} onChange={(e) => store.setSetting('temperature', Number(e.target.value))} />
          <label>Max tokens</label>
          <input type="number" value={store.maxTokens} onChange={(e) => store.setSetting('maxTokens', Number(e.target.value))} />
        </section>

        <section>
          <h3>Generate</h3>
          <textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} />
          <div className="button-row">
            <button onClick={() => runGeneration('create')}>Create</button>
            <button onClick={() => runGeneration('continue')}>Continue</button>
            <button onClick={() => runGeneration('rewrite')}>Rewrite Story</button>
          </div>
        </section>

        <section>
          <h3>Edit Selection</h3>
          <textarea value={selectionInstruction} onChange={(event) => setSelectionInstruction(event.target.value)} />
          <button onClick={() => runGeneration('edit-selection')} disabled={!selection}>Rewrite Selection</button>
        </section>

        <section>
          <h3>Prompt Transparency</h3>
          <pre>{store.compiledPromptPreview || 'Compiled prompt appears here after generation.'}</pre>
        </section>
      </aside>
    </div>
  );
};
