import { request, API_BASE } from './apiClient';

export const assignmentService = {
  // Check backend health and active API keys
  async getHealth() {
    return request('/api/health');
  },

  // Save Groq & Gemini API keys to backend
  async saveKeys(groqKey, geminiKey) {
    return request('/api/config/keys', {
      method: 'POST',
      body: {
        groq_api_key: groqKey,
        gemini_api_key: geminiKey
      }
    });
  },

  async saveApiKeys(payload) {
    return request('/api/config/keys', {
      method: 'POST',
      body: payload
    });
  },

  // Validate Course & Student Metadata (Step 1)
  async validateMetadata(metadata) {
    return request('/api/validate/metadata', {
      method: 'POST',
      body: metadata
    });
  },

  // Scan Question Paper using Groq LPU
  async scanQuestions(file, rawText = '', modelName = 'llama-3.3-70b-versatile') {
    const formData = new FormData();
    if (file) formData.append('file', file);
    if (rawText) formData.append('raw_text', rawText);
    formData.append('model_name', modelName);

    return request('/api/scan', {
      method: 'POST',
      body: formData
    });
  },

  // Analyze Instructions & Extract Dynamic Specs
  async analyzeInstructions(file, rawText = '') {
    const formData = new FormData();
    if (file) formData.append('file', file);
    if (rawText) formData.append('raw_text', rawText);

    return request('/api/analyze-instructions', {
      method: 'POST',
      body: formData
    });
  },

  // Stream Assignment Generation via SSE (Server-Sent Events)
  generateAssignmentStream(payload, onMessage, onError, onComplete) {
    const url = `${API_BASE}/api/generate-stream`;

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
      .then(async (response) => {
        if (!response.ok) {
          const errText = await response.text();
          throw new Error(errText || 'Generation request failed');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              try {
                const data = JSON.parse(trimmed.replace(/^data:\s*/, ''));
                if (data.type === 'error') {
                  onError(new Error(data.message));
                  return;
                }
                onMessage(data);
                if (data.type === 'completed') {
                  onComplete(data);
                }
              } catch (e) {
                console.error('Failed to parse SSE payload:', e);
              }
            }
          }
        }
      })
      .catch((err) => {
        onError(err);
      });
  }
};
