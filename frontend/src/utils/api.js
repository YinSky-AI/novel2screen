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
    let msg = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        msg = Array.isArray(errData.detail)
          ? errData.detail.map((d) => {
              const loc = d.loc ? d.loc.join('.') : '';
              return `${loc}: ${d.msg}`;
            }).join('; ')
          : String(errData.detail);
      }
    } catch {}
    throw new Error(msg);
  }

  if (response.status === 204) return null;
  return response.json();
}

function convertNovelText(text, pipeline = 'fast', language = 'auto') {
  return request('/convert', {
    method: 'POST',
    body: { novel_text: text, pipeline, language },
  });
}

function uploadNovelFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/novels/upload', {
    method: 'POST',
    body: formData,
  });
}

function generateScreenplay(taskId, mode = 'auto', pipeline = 'fast') {
  return request(`/generate/${taskId}?mode=${mode}&pipeline=${pipeline}`, {
    method: 'POST',
  });
}

function getTaskStatus(taskId) {
  return request(`/tasks/${taskId}`);
}

function exportYaml(taskId) {
  return request(`/export/yaml/${taskId}`);
}

function importEdits(taskId, yamlContent) {
  return request(`/import-edits/${taskId}`, {
    method: 'POST',
    body: { yaml_content: yamlContent },
  });
}

function getAlignment(taskId) {
  return request(`/alignment/${taskId}`);
}

function validateYaml(yamlContent) {
  return request('/validate', {
    method: 'POST',
    body: { yaml_content: yamlContent },
  });
}

function assessYaml(yamlContent) {
  return request('/yaml/assess', {
    method: 'POST',
    body: { yaml_content: yamlContent },
  });
}

function getUsage() {
  return request('/usage');
}

function healthCheck() {
  return request('/health');
}

function detectLanguage(text) {
  return request('/detect-language', {
    method: 'POST',
    body: { text },
  });
}

export {
  API_BASE,
  convertNovelText,
  uploadNovelFile,
  generateScreenplay,
  getTaskStatus,
  exportYaml,
  importEdits,
  getAlignment,
  validateYaml,
  assessYaml,
  getUsage,
  healthCheck,
  detectLanguage,
};
