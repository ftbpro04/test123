import axios from 'axios';
import type { BackendRow } from '../persistence.js';

type GenerateInput = {
  backend: BackendRow;
  model: string;
  prompt: string;
  maxTokens: number;
  temperature: number;
  actionType: 'create' | 'continue' | 'rewrite' | 'edit-selection';
  selection?: string;
  contextBefore?: string;
  contextAfter?: string;
};

const compilePrompt = (payload: GenerateInput) => {
  if (payload.actionType === 'edit-selection') {
    return [
      'Rewrite only the selected passage. Return only replacement text.',
      `CONTEXT BEFORE:\n${payload.contextBefore ?? ''}`,
      `SELECTED:\n${payload.selection ?? ''}`,
      `CONTEXT AFTER:\n${payload.contextAfter ?? ''}`,
      `INSTRUCTION:\n${payload.prompt}`
    ].join('\n\n');
  }
  return payload.prompt;
};

const sendOpenAIStyle = async (url: string, apiKey: string | null, body: unknown) => {
  const res = await axios.post(`${url.replace(/\/$/, '')}/v1/chat/completions`, body, {
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
    },
    timeout: 60_000
  });
  return res.data?.choices?.[0]?.message?.content ?? '';
};

export const backendRegistry = {
  async testConnection(backend: BackendRow) {
    try {
      if (backend.type === 'ollama') {
        await axios.get(`${backend.baseUrl.replace(/\/$/, '')}/api/tags`, { timeout: 5000 });
      } else {
        await axios.get(`${backend.baseUrl.replace(/\/$/, '')}/v1/models`, {
          timeout: 5000,
          headers: backend.apiKey ? { Authorization: `Bearer ${backend.apiKey}` } : undefined
        });
      }
      return { ok: true, message: 'Connection successful' };
    } catch (error) {
      return { ok: false, message: `Connection failed: ${(error as Error).message}` };
    }
  },
  async generate(input: GenerateInput) {
    const prompt = compilePrompt(input);
    if (input.backend.type === 'ollama') {
      const res = await axios.post(`${input.backend.baseUrl.replace(/\/$/, '')}/api/generate`, {
        model: input.model,
        prompt,
        options: {
          num_predict: input.maxTokens,
          temperature: input.temperature
        }
      });
      return { output: res.data.response ?? '', compiledPrompt: prompt };
    }

    const output = await sendOpenAIStyle(input.backend.baseUrl, input.backend.apiKey, {
      model: input.model,
      messages: [{ role: 'user', content: prompt }],
      temperature: input.temperature,
      max_tokens: input.maxTokens,
      stream: false
    });

    return { output, compiledPrompt: prompt };
  }
};
