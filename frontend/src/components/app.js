import {
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
  healthCheck,
  detectLanguage,
} from '../utils/api.js';

/* ===== i18n ===== */
const i18n = {
  zh: {
    appTitle: 'Novel2Screen',
    statusCheck: '检查中...',
    statusOnline: '已连接',
    statusOffline: '未连接',
    stepNovelInfo: '小说信息',
    stepAnalysis: 'AI 分析',
    stepOutput: '剧本输出',
    step1Title: '步骤 1：输入小说内容',
    step2Title: '步骤 2：AI 分析处理',
    step3Title: '步骤 3：剧本 YAML 输出',
    novelTextLabel: '小说文本',
    novelPlaceholder: '在此粘贴您的小说文本...',
    charCount: '{count} / {min} 字符',
    charCountMin: '最少需要 {min} 字符',
    pipelineMode: 'Pipeline 模式',
    modeFast: '快速',
    modeFull: '完整',
    modeAuto: '自动',
    fileUpload: '上传文件',
    dropOrClick: '拖拽文件或点击上传',
    btnConvert: '开始转换',
    btnReset: '重置',
    btnCopy: '复制',
    btnDownload: '下载',
    btnValidate: '验证',
    btnEdit: '编辑',
    btnSave: '保存',
    btnCancel: '取消',
    btnNewConvert: '开始新的转换',
    importEdits: '导入编辑',
    importEditsHint: '上传 YAML/JSON 编辑文件',
    alignmentReport: '对齐报告',
    tabNovel2Screen: '小说转剧本',
    tabYamlEditor: 'YAML 编辑器',
    yamlEditorTitle: 'YAML 编辑器（独立模式）',
    yamlPasteLabel: '粘贴 YAML 内容',
    yamlPastePlaceholder: '在此粘贴 YAML 内容...',
    yamlFileUpload: '上传 YAML 文件',
    yamlDropOrClick: '拖拽 YAML 文件或点击上传',
    yamlBtnLoad: '加载 YAML',
    yamlBtnReset: '清空',
    yamlBtnBack: '返回上传',
    elapsedTime: '耗时：',
    stageInit: '初始化...',
    stageProcessing: '处理中...',
    stageFinalizing: '收尾中...',
    toastConverted: '转换成功！',
    toastCopied: '已复制到剪贴板！',
    toastDownloaded: '下载完成！',
    toastValidated: 'YAML 验证通过 ✓',
    toastValidationError: '验证发现错误',
    toastEditsImported: '编辑已导入成功！',
    toastReset: '已重置。',
    toastError: '发生错误',
    toastUploadSuccess: '文件上传成功！',
    errorEmptyInput: '请输入小说文本或上传文件。',
    errorTooShort: '文本太短，至少需要 {min} 个字符。',
    errorUpload: '文件上传失败。',
    errorGenerate: '生成失败。',
    errorNetwork: '网络错误，请检查连接。',
    footerText: 'Novel2Screen — AI 驱动的小说转剧本平台',
    langLabel: '语言：',
    modeDesc: '快速模式仅提取关键信息，完整模式包含深度分析，自动模式根据文本长度智能选择。',
    langDetected: '检测语言：{lang}',
  },
  en: {
    appTitle: 'Novel2Screen',
    statusCheck: 'Checking...',
    statusOnline: 'Connected',
    statusOffline: 'Disconnected',
    stepNovelInfo: 'Novel Info',
    stepAnalysis: 'AI Analysis',
    stepOutput: 'Screenplay Output',
    step1Title: 'Step 1: Novel Input',
    step2Title: 'Step 2: AI Analysis',
    step3Title: 'Step 3: Screenplay Output',
    novelTextLabel: 'Novel Text',
    novelPlaceholder: 'Paste your novel text here...',
    charCount: '{count} / {min} characters',
    charCountMin: 'Min {min} characters required',
    pipelineMode: 'Pipeline Mode',
    modeFast: 'Fast',
    modeFull: 'Full',
    modeAuto: 'Auto',
    fileUpload: 'Upload File',
    dropOrClick: 'Drop file or click to upload',
    btnConvert: 'Convert',
    btnReset: 'Reset',
    btnCopy: 'Copy',
    btnDownload: 'Download',
    btnValidate: 'Validate',
    btnEdit: 'Edit',
    btnSave: 'Save',
    btnCancel: 'Cancel',
    btnNewConvert: 'New Conversion',
    importEdits: 'Import Edits',
    importEditsHint: 'Upload YAML/JSON edits file',
    alignmentReport: 'Alignment Report',
    tabNovel2Screen: 'Novel2Screen',
    tabYamlEditor: 'YAML Editor',
    yamlEditorTitle: 'YAML Editor (Standalone)',
    yamlPasteLabel: 'Paste YAML Content',
    yamlPastePlaceholder: 'Paste your YAML content here...',
    yamlFileUpload: 'Upload YAML File',
    yamlDropOrClick: 'Drop YAML file or click to upload',
    yamlBtnLoad: 'Load YAML',
    yamlBtnReset: 'Clear',
    yamlBtnBack: 'Back to Upload',
    elapsedTime: 'Elapsed:',
    stageInit: 'Initializing...',
    stageProcessing: 'Processing...',
    stageFinalizing: 'Finalizing...',
    toastConverted: 'Conversion complete!',
    toastCopied: 'Copied to clipboard!',
    toastDownloaded: 'Download complete!',
    toastValidated: 'YAML is valid!',
    toastValidationError: 'Validation found errors',
    toastEditsImported: 'Edits imported successfully!',
    toastReset: 'Reset complete.',
    toastError: 'An error occurred',
    toastUploadSuccess: 'File uploaded successfully!',
    errorEmptyInput: 'Please enter novel text or upload a file.',
    errorTooShort: 'Text is too short. Min {min} characters required.',
    errorUpload: 'File upload failed.',
    errorGenerate: 'Generation failed.',
    errorNetwork: 'Network error. Please check your connection.',
    footerText: 'Novel2Screen — AI-Powered Novel to Screenplay Conversion',
    langLabel: 'Language:',
    modeDesc: 'Fast mode extracts key info only. Full mode includes deep analysis. Auto mode picks based on text length.',
    langDetected: 'Detected: {lang}',
  },
};

let currentLang = 'zh';

function t(key) {
  const dict = i18n[currentLang] || i18n.zh;
  return dict[key] || key;
}

function setLang(lang) {
  currentLang = lang;
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (!key) return;
    const text = t(key);
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      if (el.dataset.i18nPlaceholder) el.placeholder = t(el.dataset.i18nPlaceholder);
    } else {
      el.textContent = text;
    }
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  updateCharCounter();
  updateStatusText();
}

/* ===== DOM References ===== */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  statusDot: $('#status-dot'),
  statusText: $('#status-text'),
  langSelector: $('#lang-selector'),
  stepPanel1: $('#step-1-panel'),
  stepPanel2: $('#step-2-panel'),
  stepPanel3: $('#step-3-panel'),
  stepCircle1: $('#step-circle-1'),
  stepCircle2: $('#step-circle-2'),
  stepCircle3: $('#step-circle-3'),
  stepLine1: $('#step-line-1'),
  stepLine2: $('#step-line-2'),
  stepLabels: $$('.step-label'),
  novelText: $('#novel-text'),
  charCounter: $('#char-counter'),
  langDetection: $('#lang-detection'),
  pipelineMode: $('#pipeline-mode'),
  fileUploadArea: $('#file-upload-area'),
  fileInput: $('#file-input'),
  fileName: $('#file-name'),
  btnConvert: $('#btn-convert'),
  btnReset: $('#btn-reset'),
  progressFill: $('#progress-bar-fill'),
  progressPercent: $('#progress-percent'),
  progressStage: $('#progress-stage'),
  elapsedTime: $('#elapsed-time'),
  spinner: $('#spinner'),
  yamlOutput: $('#yaml-output'),
  yamlEditor: $('#yaml-editor'),
  btnCopy: $('#btn-copy'),
  btnDownload: $('#btn-download'),
  btnValidate: $('#btn-validate'),
  btnToggleEdit: $('#btn-toggle-edit'),
  btnSaveEdit: $('#btn-save-edit'),
  btnCancelEdit: $('#btn-cancel-edit'),
  editActions: $('#edit-actions'),
  validationBadge: $('#validation-badge'),
  importUploadArea: $('#import-upload-area'),
  importFileInput: $('#import-file-input'),
  importFileName: $('#import-file-name'),
  alignmentSection: $('#alignment-section'),
  alignmentContent: $('#alignment-content'),
  btnNewConvert: $('#btn-new-convert'),
  errorContainer: $('#error-container'),
  toastContainer: $('#toast-container'),
  stepEl1: $('[data-step="1"]'),
  stepEl2: $('[data-step="2"]'),
  stepEl3: $('[data-step="3"]'),
  stepIndicator: $('.step-indicator'),

  // Mode tabs
  modeTabs: $$('.mode-tab'),

  // Standalone YAML Editor
  yamlEditorPanel: $('#yaml-editor-panel'),
  yamlUploadSection: $('#yaml-upload-section'),
  yamlEditorView: $('#yaml-editor-view'),
  yamlPasteInput: $('#yaml-paste-input'),
  yamlFileUploadArea: $('#yaml-file-upload-area'),
  yamlFileInput: $('#yaml-file-input'),
  yamlFileName: $('#yaml-file-name'),
  btnYamlLoad: $('#btn-yaml-load'),
  btnYamlReset: $('#btn-yaml-reset'),
  btnYamlBack: $('#btn-yaml-back'),
  yamlOutputStandalone: $('#yaml-output-standalone'),
  yamlEditorStandalone: $('#yaml-editor-standalone'),
  btnYamlCopy: $('#btn-yaml-copy'),
  btnYamlDownload: $('#btn-yaml-download'),
  btnYamlValidate: $('#btn-yaml-validate'),
  btnYamlToggleEdit: $('#btn-yaml-toggle-edit'),
  btnYamlSaveEdit: $('#btn-yaml-save-edit'),
  btnYamlCancelEdit: $('#btn-yaml-cancel-edit'),
  yamlValidationBadge: $('#yaml-validation-badge'),
  yamlEditActions: $('#yaml-edit-actions'),
  yamlQualityPanel: $('#yaml-quality-panel'),
  yamlQualityStats: $('#yaml-quality-stats'),
};

/* ===== State ===== */
let state = {
  taskId: null,
  yamlContent: '',
  isEditing: false,
  polling: null,
  elapsed: null,
  elapsedSeconds: 0,
  uploadFile: null,
  importFile: null,
  // Standalone YAML Editor mode
  yamlStandaloneContent: '',
  yamlStandaloneEditing: false,
  yamlStandaloneUploadFile: null,
};

/* ===== Initialization ===== */
function init() {
  const browserLang = (navigator.language || 'en').startsWith('zh') ? 'zh' : 'en';
  currentLang = browserLang;
  dom.langSelector.value = currentLang;
  setLang(currentLang);

  dom.novelText.addEventListener('input', onNovelInput);
  dom.langSelector.addEventListener('change', onLangChange);
  dom.btnConvert.addEventListener('click', handleConvert);
  dom.btnReset.addEventListener('click', handleReset);
  dom.btnCopy.addEventListener('click', handleCopy);
  dom.btnDownload.addEventListener('click', handleDownload);
  dom.btnValidate.addEventListener('click', handleValidate);
  dom.btnToggleEdit.addEventListener('click', handleToggleEdit);
  dom.btnSaveEdit.addEventListener('click', handleSaveEdit);
  dom.btnCancelEdit.addEventListener('click', handleCancelEdit);
  dom.btnNewConvert.addEventListener('click', handleReset);
  dom.fileInput.addEventListener('change', handleFileSelect);
  dom.fileUploadArea.addEventListener('dragover', (e) => { e.preventDefault(); dom.fileUploadArea.classList.add('drag-over'); });
  dom.fileUploadArea.addEventListener('dragleave', () => dom.fileUploadArea.classList.remove('drag-over'));
  dom.fileUploadArea.addEventListener('drop', handleFileDrop);
  dom.importFileInput.addEventListener('change', handleImportFileSelect);
  dom.importUploadArea.addEventListener('dragover', (e) => { e.preventDefault(); dom.importUploadArea.classList.add('drag-over'); });
  dom.importUploadArea.addEventListener('dragleave', () => dom.importUploadArea.classList.remove('drag-over'));
  dom.importUploadArea.addEventListener('drop', handleImportFileDrop);

  // Mode tabs
  dom.modeTabs.forEach((tab) => {
    tab.addEventListener('click', () => switchMode(tab.dataset.mode));
  });

  // Standalone YAML Editor
  dom.yamlPasteInput.addEventListener('input', () => { /* no-op, just for paste */ });
  dom.yamlFileInput.addEventListener('change', handleYamlFileSelect);
  dom.yamlFileUploadArea.addEventListener('dragover', (e) => { e.preventDefault(); dom.yamlFileUploadArea.classList.add('drag-over'); });
  dom.yamlFileUploadArea.addEventListener('dragleave', () => dom.yamlFileUploadArea.classList.remove('drag-over'));
  dom.yamlFileUploadArea.addEventListener('drop', handleYamlFileDrop);
  dom.btnYamlLoad.addEventListener('click', handleYamlLoad);
  dom.btnYamlReset.addEventListener('click', handleYamlReset);
  dom.btnYamlBack.addEventListener('click', handleYamlBack);
  dom.btnYamlCopy.addEventListener('click', handleYamlCopy);
  dom.btnYamlDownload.addEventListener('click', handleYamlDownload);
  dom.btnYamlValidate.addEventListener('click', handleYamlValidate);
  dom.btnYamlToggleEdit.addEventListener('click', handleYamlToggleEdit);
  dom.btnYamlSaveEdit.addEventListener('click', handleYamlSaveEdit);
  dom.btnYamlCancelEdit.addEventListener('click', handleYamlCancelEdit);

  checkHealth();
}

/* ===== Health Check ===== */
async function checkHealth() {
  dom.statusDot.className = 'status-dot status-checking';
  dom.statusText.textContent = t('statusCheck');
  try {
    await healthCheck();
    dom.statusDot.className = 'status-dot status-online';
    dom.statusText.textContent = t('statusOnline');
  } catch {
    dom.statusDot.className = 'status-dot status-offline';
    dom.statusText.textContent = t('statusOffline');
  }
}

function updateStatusText() {
  const dot = dom.statusDot.classList.contains('status-online') ? t('statusOnline')
    : dom.statusDot.classList.contains('status-offline') ? t('statusOffline')
    : t('statusCheck');
  dom.statusText.textContent = dot;
}

/* ===== Language Selection ===== */
function onLangChange() {
  setLang(dom.langSelector.value);
}

/* ===== Novel Input ===== */
let langDetectTimer = null;

function onNovelInput() {
  updateCharCounter();
  clearTimeout(langDetectTimer);
  const text = dom.novelText.value.trim();
  if (text.length >= 20) {
    langDetectTimer = setTimeout(autoDetectLang, 800);
  } else {
    dom.langDetection.classList.add('hidden');
  }
}

function updateCharCounter() {
  const count = dom.novelText.value.length;
  const min = 100;
  const key = count < min ? 'charCountMin' : 'charCount';
  let text = t(key).replace('{count}', count).replace('{min}', min);
  dom.charCounter.textContent = text;
  dom.charCounter.classList.toggle('warning', count > 0 && count < min);
  dom.charCounter.classList.toggle('error', false);
}

async function autoDetectLang() {
  const text = dom.novelText.value.trim();
  if (text.length < 20) return;
  try {
    const result = await detectLanguage(text);
    const lang = result.language || result.lang || 'unknown';
    dom.langDetection.textContent = t('langDetected').replace('{lang}', lang);
    dom.langDetection.classList.remove('hidden');
  } catch {
    dom.langDetection.classList.add('hidden');
  }
}

/* ===== File Upload ===== */
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    state.uploadFile = file;
    dom.fileName.textContent = file.name;
    dom.fileName.classList.remove('hidden');
    dom.fileUploadArea.querySelector('.file-upload-text').classList.add('hidden');
  }
}

function handleFileDrop(e) {
  e.preventDefault();
  dom.fileUploadArea.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    state.uploadFile = file;
    dom.fileName.textContent = file.name;
    dom.fileName.classList.remove('hidden');
    dom.fileUploadArea.querySelector('.file-upload-text').classList.add('hidden');
  }
}

/* ===== Convert ===== */
async function handleConvert() {
  hideError();

  if (state.uploadFile) {
    await doFileUpload();
    return;
  }

  const text = dom.novelText.value.trim();
  if (!text) {
    showError(t('errorEmptyInput'));
    return;
  }
  if (text.length < 100) {
    showError(t('errorTooShort').replace('{min}', '100'));
    return;
  }

  dom.btnConvert.disabled = true;
  showStep(2);

  try {
    const mode = dom.pipelineMode.value;
    const result = await convertNovelText(text, mode);
    state.taskId = result.task_id || result.id;
    startPolling();
    startTimer();
  } catch (err) {
    dom.btnConvert.disabled = false;
    showStep(1);
    showError(err.message || t('errorGenerate'));
  }
}

async function doFileUpload() {
  dom.btnConvert.disabled = true;
  showStep(2);

  try {
    const uploadResult = await uploadNovelFile(state.uploadFile);
    state.taskId = uploadResult.task_id || uploadResult.id;
    const mode = dom.pipelineMode.value;
    await generateScreenplay(state.taskId, 'auto', mode);
    showToast(t('toastUploadSuccess'), 'success');
    startPolling();
    startTimer();
  } catch (err) {
    dom.btnConvert.disabled = false;
    showStep(1);
    showError(err.message || t('errorUpload'));
  }
}

/* ===== Polling ===== */
function startPolling() {
  stopPolling();
  state.polling = setInterval(pollTask, 2000);
  pollTask();
}

function stopPolling() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }
}

async function pollTask() {
  if (!state.taskId) return;

  try {
    const data = await getTaskStatus(state.taskId);
    updateProgress(data);

    if (data.status === 'completed' || data.status === 'done') {
      stopPolling();
      stopTimer();
      state.yamlContent = data.yaml_content || data.output || '';
      showStep(3);
      renderYaml(state.yamlContent);
      renderQuality(data.quality || data.quality_report || {});
      showToast(t('toastConverted'), 'success');
    } else if (data.status === 'failed' || data.status === 'error') {
      stopPolling();
      stopTimer();
      showStep(1);
      dom.btnConvert.disabled = false;
      showError(data.error || data.message || t('errorGenerate'));
    }
  } catch (err) {
    stopPolling();
    stopTimer();
    showStep(1);
    dom.btnConvert.disabled = false;
    showError(err.message || t('errorNetwork'));
  }
}

function updateProgress(data) {
  const pct = data.progress != null ? data.progress : 5;
  dom.progressFill.style.width = Math.min(100, Math.max(5, pct)) + '%';
  dom.progressPercent.textContent = Math.round(pct) + '%';

  const stage = data.current_stage || data.stage || '';
  if (stage) {
    dom.progressStage.textContent = stage;
  } else if (pct < 30) {
    dom.progressStage.textContent = t('stageInit');
  } else if (pct < 80) {
    dom.progressStage.textContent = t('stageProcessing');
  } else {
    dom.progressStage.textContent = t('stageFinalizing');
  }
}

/* ===== Timer ===== */
function startTimer() {
  state.elapsedSeconds = 0;
  dom.elapsedTime.textContent = '00:00';
  state.elapsed = setInterval(() => {
    state.elapsedSeconds++;
    const m = String(Math.floor(state.elapsedSeconds / 60)).padStart(2, '0');
    const s = String(state.elapsedSeconds % 60).padStart(2, '0');
    dom.elapsedTime.textContent = m + ':' + s;
  }, 1000);
}

function stopTimer() {
  if (state.elapsed) {
    clearInterval(state.elapsed);
    state.elapsed = null;
  }
}

/* ===== Step Navigation ===== */
function showStep(step) {
  [dom.stepPanel1, dom.stepPanel2, dom.stepPanel3].forEach((p, i) => {
    p.classList.toggle('hidden', i + 1 !== step);
  });

  [dom.stepEl1, dom.stepEl2, dom.stepEl3].forEach((el, i) => {
    el.classList.remove('active', 'completed');
    if (i + 1 === step) el.classList.add('active');
    else if (i + 1 < step) el.classList.add('completed');
  });

  [dom.stepCircle1, dom.stepCircle2, dom.stepCircle3].forEach((c, i) => {
    c.classList.remove('active', 'completed');
    if (i + 1 === step) c.classList.add('active');
    else if (i + 1 < step) c.classList.add('completed');
  });

  [dom.stepLine1, dom.stepLine2].forEach((l, i) => {
    l.classList.remove('completed', 'active');
    if (i + 1 < step) l.classList.add('completed');
    else if (i + 1 === step) l.classList.add('active');
  });
}

/* ===== YAML Rendering ===== */
function renderYaml(yaml) {
  state.yamlContent = yaml;
  dom.yamlOutput.innerHTML = highlightYaml(yaml);
  dom.yamlEditor.value = yaml;
}

function highlightYaml(yaml) {
  const escaped = yaml
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return escaped
    .split('\n')
    .map((line) => {
      if (/^\s*#/.test(line)) {
        return '<span class="yaml-comment">' + line + '</span>';
      }
      if (/^\s*$/.test(line)) return '';
      const m = line.match(/^(\s*)([^:]+?)\s*:(.*)$/);
      if (m) {
        const indent = m[1];
        const key = m[2];
        let val = m[3].trim();

        let coloredVal = '';
        if (val === '' || val === 'null' || val === '~') {
          coloredVal = '<span class="yaml-null">' + (val || 'null') + '</span>';
        } else if (val === 'true' || val === 'false' || val === 'yes' || val === 'no') {
          coloredVal = '<span class="yaml-bool">' + val + '</span>';
        } else if (/^-?\d+\.?\d*$/.test(val)) {
          coloredVal = '<span class="yaml-number">' + val + '</span>';
        } else {
          coloredVal = '<span class="yaml-string">' + val + '</span>';
        }

        const formattedKey = key
          .replace(/\\&lt;/g, '&lt;')
          .replace(/\\&gt;/g, '&gt;');

        return indent + '<span class="yaml-key">' + formattedKey + '</span>: ' + coloredVal;
      }
      return '<span class="yaml-string">' + line + '</span>';
    })
    .join('\n');
}

/* ===== YAML Actions ===== */
async function handleCopy() {
  try {
    await navigator.clipboard.writeText(state.yamlContent);
    showToast(t('toastCopied'), 'success');
    dom.btnCopy.style.animation = 'copiedPulse 0.3s ease';
    setTimeout(() => { dom.btnCopy.style.animation = ''; }, 300);
  } catch {
    showToast(t('toastError'), 'error');
  }
}

function handleDownload() {
  const blob = new Blob([state.yamlContent], { type: 'text/yaml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'screenplay.yaml';
  a.click();
  URL.revokeObjectURL(url);
  showToast(t('toastDownloaded'), 'success');
}

async function handleValidate() {
  const content = state.yamlContent || state.yamlStandaloneContent || '';
  if (!content) return;
  dom.validationBadge.classList.add('hidden');
  try {
    const result = await validateYaml(content);
    if (result.valid || result.is_valid) {
      dom.validationBadge.textContent = '\u2714 ' + t('toastValidated');
      dom.validationBadge.className = 'badge badge-success';
      dom.validationBadge.classList.remove('hidden');
      showToast(t('toastValidated'), 'success');
    } else {
      dom.validationBadge.textContent = '\u2718 ' + t('toastValidationError');
      dom.validationBadge.className = 'badge badge-error';
      dom.validationBadge.classList.remove('hidden');
      if (result.errors && result.errors.length) {
        renderValidationErrors(result.errors);
      }
      showToast(t('toastValidationError'), 'warning');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderValidationErrors(errors) {
  const list = errors.map((e) => {
    const cls = e.severity === 'error' ? 'validation-error' : 'validation-warning';
    return '<li class="validation-item ' + cls + '">' + (e.message || e.msg || e) + '</li>';
  }).join('');
  dom.alignmentContent.innerHTML = '<ul class="validation-list">' + list + '</ul>';
  dom.alignmentSection.classList.remove('hidden');
}

/* ===== Edit Mode ===== */
function handleToggleEdit() {
  state.isEditing = !state.isEditing;
  if (state.isEditing) {
    dom.yamlOutput.classList.add('hidden');
    dom.yamlEditor.classList.remove('hidden');
    dom.editActions.classList.remove('hidden');
    dom.btnToggleEdit.textContent = currentLang === 'zh' ? '\u2715 取消' : '\u2715 Cancel';
    dom.yamlEditor.focus();
  } else {
    dom.yamlOutput.classList.remove('hidden');
    dom.yamlEditor.classList.add('hidden');
    dom.editActions.classList.add('hidden');
    dom.btnToggleEdit.textContent = t('btnEdit');
  }
}

function handleSaveEdit() {
  state.yamlContent = dom.yamlEditor.value;
  renderYaml(state.yamlContent);
  dom.yamlOutput.classList.remove('hidden');
  dom.yamlEditor.classList.add('hidden');
  dom.editActions.classList.add('hidden');
  dom.btnToggleEdit.textContent = t('btnEdit');
  state.isEditing = false;
}

function handleCancelEdit() {
  dom.yamlEditor.value = state.yamlContent;
  dom.yamlOutput.classList.remove('hidden');
  dom.yamlEditor.classList.add('hidden');
  dom.editActions.classList.add('hidden');
  dom.btnToggleEdit.textContent = t('btnEdit');
  state.isEditing = false;
}

/* ===== Import Edits ===== */
function handleImportFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    state.importFile = file;
    dom.importFileName.textContent = file.name;
    dom.importFileName.classList.remove('hidden');
    dom.importUploadArea.querySelector('.file-upload-text').classList.add('hidden');
    doImportEdits(file);
  }
}

function handleImportFileDrop(e) {
  e.preventDefault();
  dom.importUploadArea.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    state.importFile = file;
    dom.importFileName.textContent = file.name;
    dom.importFileName.classList.remove('hidden');
    dom.importUploadArea.querySelector('.file-upload-text').classList.add('hidden');
    doImportEdits(file);
  }
}

async function doImportEdits(file) {
  if (!state.taskId) return;
  try {
    const yamlContent = await file.text();
    await importEdits(state.taskId, yamlContent);
    showToast(t('toastEditsImported'), 'success');
    loadAlignment();
  } catch (err) {
    showToast(err.message || t('toastError'), 'error');
  }
}

async function loadAlignment() {
  if (!state.taskId) return;
  try {
    const result = await getAlignment(state.taskId);
    dom.alignmentSection.classList.remove('hidden');

    let html = '';
    const alignments = result.alignment || result.differences || result.diffs || [];
    alignments.forEach((item) => {
      const field = item.field || item.key || '';
      const original = item.original || item.ai_value || '';
      const edited = item.edited || item.imported_value || '';
      const match = item.match !== false;
      const cls = match ? 'alignment-match' : 'alignment-mismatch';
      html += '<div class="alignment-item">';
      html += '<span class="alignment-field">' + field + '</span>';
      html += '<span class="' + cls + '">' + (match ? 'MATCH' : 'DIFF') + '</span>';
      if (original) html += '<span>' + escapeHtml(String(original)) + '</span>';
      if (edited && !match) html += '<span>\u2192 ' + escapeHtml(String(edited)) + '</span>';
      html += '</div>';
    });

    if (!alignments.length) {
      html = '<p>' + (currentLang === 'zh' ? '\u65E0对齐差异。' : 'No alignment differences.') + '</p>';
    }

    dom.alignmentContent.innerHTML = html;
  } catch {
    dom.alignmentSection.classList.remove('hidden');
    dom.alignmentContent.innerHTML = '<p>' + (currentLang === 'zh' ? '\u52A0\u8F7D\u62A5\u544A\u5931\u8D25。' : 'Failed to load report.') + '</p>';
  }
}

/* ===== Mode Switching ===== */
function switchMode(mode) {
  dom.modeTabs.forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.mode === mode);
  });

  if (mode === 'yaml-editor') {
    dom.stepIndicator.classList.add('hidden');
    dom.stepPanel1.classList.add('hidden');
    dom.stepPanel2.classList.add('hidden');
    dom.stepPanel3.classList.add('hidden');
    dom.yamlEditorPanel.classList.remove('hidden');
  } else {
    dom.stepIndicator.classList.remove('hidden');
    dom.yamlEditorPanel.classList.add('hidden');
    // Show current step
    const visibleStep = [dom.stepPanel1, dom.stepPanel2, dom.stepPanel3].findIndex((p) => !p.classList.contains('hidden'));
    if (visibleStep === -1) dom.stepPanel1.classList.remove('hidden');
  }
}

/* ===== Standalone YAML Editor ===== */
function handleYamlFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    state.yamlStandaloneUploadFile = file;
    dom.yamlFileName.textContent = file.name;
    dom.yamlFileName.classList.remove('hidden');
    dom.yamlFileUploadArea.querySelector('.file-upload-text').classList.add('hidden');
  }
}

function handleYamlFileDrop(e) {
  e.preventDefault();
  dom.yamlFileUploadArea.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    state.yamlStandaloneUploadFile = file;
    dom.yamlFileName.textContent = file.name;
    dom.yamlFileName.classList.remove('hidden');
    dom.yamlFileUploadArea.querySelector('.file-upload-text').classList.add('hidden');
  }
}

function handleYamlLoad() {
  const pasteText = dom.yamlPasteInput.value.trim();
  if (pasteText) {
    state.yamlStandaloneContent = pasteText;
    showYamlEditorView();
    renderYamlStandalone(pasteText);
    return;
  }
  if (state.yamlStandaloneUploadFile) {
    const reader = new FileReader();
    reader.onload = (e) => {
      state.yamlStandaloneContent = e.target.result;
      showYamlEditorView();
      renderYamlStandalone(state.yamlStandaloneContent);
    };
    reader.readAsText(state.yamlStandaloneUploadFile);
    return;
  }
  showToast(currentLang === 'zh' ? '请粘贴 YAML 内容或上传文件。' : 'Please paste YAML or upload a file.', 'warning');
}

function showYamlEditorView() {
  dom.yamlUploadSection.classList.add('hidden');
  dom.yamlEditorView.classList.remove('hidden');
  dom.yamlValidationBadge.classList.add('hidden');
  dom.yamlQualityPanel.classList.add('hidden');
}

function showYamlUploadView() {
  dom.yamlUploadSection.classList.remove('hidden');
  dom.yamlEditorView.classList.add('hidden');
  dom.yamlValidationBadge.classList.add('hidden');
}

function handleYamlBack() {
  state.yamlStandaloneContent = '';
  state.yamlStandaloneEditing = false;
  dom.yamlEditorStandalone.classList.add('hidden');
  dom.yamlOutputStandalone.classList.remove('hidden');
  dom.yamlEditActions.classList.add('hidden');
  dom.btnYamlToggleEdit.textContent = t('btnEdit');
  showYamlUploadView();
}

function handleYamlReset() {
  state.yamlStandaloneContent = '';
  state.yamlStandaloneEditing = false;
  state.yamlStandaloneUploadFile = null;
  dom.yamlPasteInput.value = '';
  dom.yamlFileInput.value = '';
  dom.yamlFileName.classList.add('hidden');
  dom.yamlFileUploadArea.querySelector('.file-upload-text').classList.remove('hidden');
  dom.yamlOutputStandalone.innerHTML = '';
  dom.yamlEditorStandalone.value = '';
  dom.yamlEditorStandalone.classList.add('hidden');
  dom.yamlOutputStandalone.classList.remove('hidden');
  dom.yamlEditActions.classList.add('hidden');
  dom.btnYamlToggleEdit.textContent = t('btnEdit');
  dom.yamlValidationBadge.classList.add('hidden');
  dom.yamlQualityPanel.classList.add('hidden');
  showYamlUploadView();
}

function renderYamlStandalone(yaml) {
  state.yamlStandaloneContent = yaml;
  dom.yamlOutputStandalone.innerHTML = highlightYaml(yaml);
  dom.yamlEditorStandalone.value = yaml;
}

function handleYamlCopy() {
  if (!state.yamlStandaloneContent) return;
  navigator.clipboard.writeText(state.yamlStandaloneContent).then(() => {
    showToast(t('toastCopied'), 'success');
  }).catch(() => {
    showToast(t('toastError'), 'error');
  });
}

function handleYamlDownload() {
  if (!state.yamlStandaloneContent) return;
  const blob = new Blob([state.yamlStandaloneContent], { type: 'text/yaml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'screenplay.yaml';
  a.click();
  URL.revokeObjectURL(url);
  showToast(t('toastDownloaded'), 'success');
}

async function handleYamlValidate() {
  if (!state.yamlStandaloneContent) return;
  dom.yamlValidationBadge.classList.add('hidden');
  try {
    const result = await validateYaml(state.yamlStandaloneContent);
    if (result.valid || result.is_valid) {
      dom.yamlValidationBadge.textContent = '\u2714 ' + t('toastValidated');
      dom.yamlValidationBadge.className = 'badge badge-success';
      dom.yamlValidationBadge.classList.remove('hidden');
      showToast(t('toastValidated'), 'success');
      // Also try quality assessment
      try {
        const qResult = await assessYaml(state.yamlStandaloneContent);
        if (qResult && qResult.valid_yaml) {
          renderYamlQuality(qResult);
        }
      } catch {}
    } else {
      dom.yamlValidationBadge.textContent = '\u2718 ' + t('toastValidationError');
      dom.yamlValidationBadge.className = 'badge badge-error';
      dom.yamlValidationBadge.classList.remove('hidden');
      showToast(t('toastValidationError'), 'warning');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function handleYamlToggleEdit() {
  state.yamlStandaloneEditing = !state.yamlStandaloneEditing;
  if (state.yamlStandaloneEditing) {
    dom.yamlOutputStandalone.classList.add('hidden');
    dom.yamlEditorStandalone.classList.remove('hidden');
    dom.yamlEditActions.classList.remove('hidden');
    dom.btnYamlToggleEdit.textContent = currentLang === 'zh' ? '\u2715 取消' : '\u2715 Cancel';
    dom.yamlEditorStandalone.focus();
  } else {
    dom.yamlOutputStandalone.classList.remove('hidden');
    dom.yamlEditorStandalone.classList.add('hidden');
    dom.yamlEditActions.classList.add('hidden');
    dom.btnYamlToggleEdit.textContent = t('btnEdit');
  }
}

function handleYamlSaveEdit() {
  state.yamlStandaloneContent = dom.yamlEditorStandalone.value;
  renderYamlStandalone(state.yamlStandaloneContent);
  dom.yamlOutputStandalone.classList.remove('hidden');
  dom.yamlEditorStandalone.classList.add('hidden');
  dom.yamlEditActions.classList.add('hidden');
  dom.btnYamlToggleEdit.textContent = t('btnEdit');
  state.yamlStandaloneEditing = false;
}

function handleYamlCancelEdit() {
  dom.yamlEditorStandalone.value = state.yamlStandaloneContent;
  dom.yamlOutputStandalone.classList.remove('hidden');
  dom.yamlEditorStandalone.classList.add('hidden');
  dom.yamlEditActions.classList.add('hidden');
  dom.btnYamlToggleEdit.textContent = t('btnEdit');
  state.yamlStandaloneEditing = false;
}

function renderYamlQuality(quality) {
  if (!quality || !quality.valid_yaml) {
    dom.yamlQualityPanel.classList.add('hidden');
    return;
  }
  dom.yamlQualityPanel.classList.remove('hidden');

  const emo = Math.round((1 - (quality.emotion_null_rate || 0)) * 100);
  const cid = Math.round((1 - (quality.char_id_null_rate || 0)) * 100);
  const dur = Math.round((1 - (quality.duration_diversity || 0)) * 100);
  const beats = quality.beat_count || 0;
  const scenes = quality.scene_count || 0;
  const issues = quality.issues || [];

  const grade = (v) => v >= 90 ? 'good' : v >= 60 ? 'warn' : 'bad';

  dom.yamlQualityStats.innerHTML = `
    <div class="q-stat ${grade(emo)}"><span class="q-val">${emo}%</span><span class="q-label">Emotion</span></div>
    <div class="q-stat ${grade(cid)}"><span class="q-val">${cid}%</span><span class="q-label">Char ID</span></div>
    <div class="q-stat ${grade(dur)}"><span class="q-val">${dur}%</span><span class="q-label">Variety</span></div>
    <div class="q-stat"><span class="q-val">${beats}</span><span class="q-label">Beats</span></div>
    <div class="q-stat"><span class="q-val">${scenes}</span><span class="q-label">Scenes</span></div>
  ` + (issues.length > 0 ? `<div class="q-issues">${issues.filter(i => !i.includes('No quality issues')).map(i => '<span>' + escapeHtml(i) + '</span>').join('')}</div>` : '');
}

/* ===== Reset ===== */
function handleReset() {
  stopPolling();
  stopTimer();
  state.taskId = null;
  state.yamlContent = '';
  state.isEditing = false;
  state.uploadFile = null;
  state.importFile = null;
  state.yamlStandaloneContent = '';
  state.yamlStandaloneEditing = false;
  state.yamlStandaloneUploadFile = null;
  dom.novelText.value = '';
  dom.fileInput.value = '';
  dom.fileName.classList.add('hidden');
  dom.fileUploadArea.querySelector('.file-upload-text').classList.remove('hidden');
  dom.btnConvert.disabled = false;
  dom.yamlOutput.innerHTML = '';
  dom.yamlEditor.value = '';
  dom.yamlEditor.classList.add('hidden');
  dom.yamlOutput.classList.remove('hidden');
  dom.editActions.classList.add('hidden');
  dom.validationBadge.classList.add('hidden');
  dom.alignmentSection.classList.add('hidden');
  dom.importFileName.classList.add('hidden');
  dom.importUploadArea.querySelector('.file-upload-text').classList.remove('hidden');
  dom.importFileInput.value = '';
  dom.langDetection.classList.add('hidden');
  dom.progressFill.style.width = '0%';
  dom.progressPercent.textContent = '0%';
  dom.progressStage.textContent = t('stageInit');
  dom.elapsedTime.textContent = '00:00';
  dom.btnToggleEdit.textContent = t('btnEdit');
  showStep(1);
  hideError();
  updateCharCounter();
  showToast(t('toastReset'), 'info');
  // Also reset standalone YAML view
  handleYamlReset();
  // Ensure we're in novel2screen mode
  switchMode('novel2screen');
}

/* ===== Error Display ===== */
function showError(msg) {
  dom.errorContainer.innerHTML = '<span class="error-content">' + escapeHtml(msg) + '</span><button class="error-close" onclick="this.parentElement.classList.add(\'hidden\')">&times;</button>';
  dom.errorContainer.classList.remove('hidden');
}

function hideError() {
  dom.errorContainer.classList.add('hidden');
}

/* ===== Toast Notifications ===== */
function showToast(msg, type) {
  type = type || 'info';
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.innerHTML = '<span>' + escapeHtml(msg) + '</span><button class="toast-close">&times;</button>';
  dom.toastContainer.appendChild(toast);

  toast.querySelector('.toast-close').addEventListener('click', () => {
    toast.remove();
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ===== Quality Assessment ===== */
function renderQuality(quality) {
  const panel = document.getElementById('quality-panel');
  const stats = document.getElementById('quality-stats');
  if (!panel || !stats) return;
  if (!quality || !quality.valid_yaml) {
    panel.classList.add('hidden');
    return;
  }
  panel.classList.remove('hidden');

  const emo = Math.round((1 - quality.emotion_null_rate) * 100);
  const cid = Math.round((1 - quality.char_id_null_rate) * 100);
  const dur = Math.round((1 - quality.duration_diversity) * 100);
  const beats = quality.beat_count || 0;
  const scenes = quality.scene_count || 0;
  const issues = quality.issues || [];

  const grade = (v) => v >= 90 ? 'good' : v >= 60 ? 'warn' : 'bad';

  stats.innerHTML = `
    <div class="q-stat ${grade(emo)}"><span class="q-val">${emo}%</span><span class="q-label">Emotion</span></div>
    <div class="q-stat ${grade(cid)}"><span class="q-val">${cid}%</span><span class="q-label">Char ID</span></div>
    <div class="q-stat ${grade(dur)}"><span class="q-val">${dur}%</span><span class="q-label">Variety</span></div>
    <div class="q-stat"><span class="q-val">${beats}</span><span class="q-label">Beats</span></div>
    <div class="q-stat"><span class="q-val">${scenes}</span><span class="q-label">Scenes</span></div>
  ` + (issues.length > 0 ? `<div class="q-issues">${issues.filter(i => !i.includes('No quality issues')).map(i => '<span>' + escapeHtml(i) + '</span>').join('')}</div>` : '');
}

/* ===== Utilities ===== */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ===== Start ===== */
document.addEventListener('DOMContentLoaded', init);

export { i18n, t, setLang };
