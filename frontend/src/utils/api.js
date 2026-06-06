const API_BASE = 'http://localhost:8000';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Accept': 'application/json' },
    ...options,
  };

  if (config.body && !(config.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    config.body = JSON.stringify(config.body);
  }

  let response;
  try {
    response = await fetch(url, config);
  } catch (err) {
    throw new Error(`Network error: ${err.message}`);
  }

  if (!response.ok) {
    if (response.status === 422) {
      const errData = await response.json().catch(() => null);
      if (errData && errData.detail) {
        const messages = Array.isArray(errData.detail)
          ? errData.detail.map((d) => {
              const loc = d.loc ? d.loc.join('.') : '';
              return `${loc}: ${d.msg}`;
            }).join('; ')
          : String(errData.detail);
        throw new Error(messages);
      }
    }
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

function convertNovelText(text, mode, pipeline, language) {
  return request('/api/v1/convert', {
    method: 'POST',
    body: { text, mode, pipeline, language },
  });
}

function uploadNovelFile(file, mode, pipeline, language) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);
  formData.append('pipeline', pipeline);
  if (language) formData.append('language', language);
  return request('/api/v1/convert/upload', {
    method: 'POST',
    body: formData,
  });
}

function generateScreenplay(taskId, mode, pipeline) {
  return request('/api/v1/generate', {
    method: 'POST',
    body: { task_id: taskId, mode, pipeline },
  });
}

function getTaskStatus(taskId) {
  return request(`/api/v1/tasks/${taskId}`);
}

function exportYaml(taskId, format) {
  return request(`/api/v1/tasks/${taskId}/export?format=${format || 'yaml'}`);
}

function importEdits(taskId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return request(`/api/v1/tasks/${taskId}/import`, {
    method: 'POST',
    body: formData,
  });
}

function getAlignment(taskId) {
  return request(`/api/v1/tasks/${taskId}/alignment`);
}

function validateYaml(taskId) {
  return request(`/api/v1/tasks/${taskId}/validate`, { method: 'POST' });
}

function getUsage() {
  return request('/api/v1/usage');
}

function healthCheck() {
  return request('/api/v1/health');
}

function detectLanguage(text) {
  return request('/api/v1/detect-language', {
    method: 'POST',
    body: { text },
  });
}

export {
  API_BASE,
  request,
  convertNovelText,
  uploadNovelFile,
  generateScreenplay,
  getTaskStatus,
  exportYaml,
  importEdits,
  getAlignment,
  validateYaml,
  getUsage,
  healthCheck,
  detectLanguage,
};
