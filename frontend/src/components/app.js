// Mode switch
function switchMode(m) {
    document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
    const tab = document.querySelector('.mode-tab[data-mode="' + m + '"]');
    if (tab) tab.classList.add('active');
}

// File upload
document.getElementById('fileInput').addEventListener('change', async e => {
    const f = e.target.files[0];
    if (!f) return;
    document.getElementById('novelText').value = await f.text();
    const t = document.getElementById('title');
    if (!t.value) t.value = f.name.replace(/\.(txt|md)$/, '');
});

// Steps
function updateStep(n) {
    ['step1', 'step2', 'step3'].forEach((id, i) => {
        const el = document.getElementById(id);
        el.classList.remove('active', 'completed');
        if (i < n - 1) el.classList.add('completed');
        if (i === n - 1) el.classList.add('active');
    });
}

// Progress
function showProgress() {
    document.getElementById('progress').classList.remove('hidden');
    document.getElementById('progressFill').style.width = '0%';
    updateProgress(5, '正在初始化...');
    updateStep(2);
}
function updateProgress(pct, txt) {
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressText').textContent = txt;
}
function hideProgress() {
    document.getElementById('progressFill').style.width = '100%';
    setTimeout(() => document.getElementById('progress').classList.add('hidden'), 500);
}
function showError(msg) {
    document.getElementById('previewContent').innerHTML = '<div class="empty-state"><span class="empty-icon"><svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="24" cy="24" r="20"/><line x1="24" y1="14" x2="24" y2="30"/><line x1="24" y1="34" x2="24.01" y2="34"/></svg></span><p style="color:var(--error)">' + msg.replace(/\n/g, '<br>') + '</p></div>';
}

// Convert
async function convertNovel() {
    const title = document.getElementById('title').value || '未命名小说';
    const genre = document.getElementById('genre').value || 'Drama';
    const demo = document.querySelector('.mode-tab.active').dataset.mode === 'fast';
    const text = document.getElementById('novelText').value;
    if (!text || text.length < 100) { alert('请至少输入100字的小说内容！'); return; }

    const btn = document.getElementById('convertBtn');
    btn.disabled = true; btn.textContent = '处理中...';
    updateStep(2); updateProgress(15, demo ? 'Demo模式：正在生成示例剧本...' : 'AI模式：正在深度分析小说...');

    const result = await convertNovelText(title, genre, '', text, demo);

    btn.disabled = false;
    btn.innerHTML = '开始创作<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';

    if (!result) return;

    updateStep(3); updateProgress(90, '正在准备结果...');
    displayScreenplay(result.screenplay_yaml, result);
    displayCriticReport(result.violations, result.critic_score);
    setupExport(result.screenplay_yaml, title);
    hideProgress();

    // Scroll to result
    document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
}

// Display
function displayScreenplay(yaml, result) {
    const c = document.getElementById('previewContent');
    if (!yaml) { c.innerHTML = '<div class="empty-state"><p>暂未生成剧本</p></div>'; return; }
    if (result) {
        document.getElementById('previewStats').innerHTML = [
            '<span class="stat-badge">' + (result.chapters_processed || '?') + ' 章</span>',
            '<span class="stat-badge">' + (result.characters_extracted || '?') + ' 角色</span>',
            '<span class="stat-badge">' + (result.episodes_planned || '?') + ' 集</span>',
            '<span class="stat-badge">' + (result.scenes_written || '?') + ' 场</span>'
        ].join('');
    }
    c.innerHTML = '<div class="yaml-viewer">' + escapeHtml(yaml) + '</div>';
}

function displayCriticReport(violations, score) {
    const r = document.getElementById('criticReport'), c2 = document.getElementById('criticContent');
    if (!violations || !violations.length) { r.classList.add('hidden'); return; }
    r.classList.remove('hidden');
    const cls = score >= .8 ? 'good' : score >= .6 ? 'fair' : 'poor';
    const lbl = score >= .8 ? '优秀' : score >= .6 ? '一般' : '待改进';
    let h = '<span class="score-badge ' + cls + '">评分: ' + (score * 100).toFixed(0) + '/100 (' + lbl + ')</span>';
    violations.forEach(v => {
        h += '<div style="margin-top:10px;padding:10px;background:var(--bg-input);border-radius:6px;font-size:13px">';
        h += '<span style="color:var(--text-muted)">' + (v.category || '') + '</span>: ' + v.description + '</div>';
    });
    c2.innerHTML = h;
}

// Export
function setupExport(yaml, title) {
    const area = document.getElementById('exportArea');
    area.classList.remove('hidden');
    const c = document.getElementById('exportContent');
    c.innerHTML = '<p style="color:var(--text-muted);margin-bottom:16px">剧本 <strong style="color:var(--text)">' + escapeHtml(title) + '</strong> 已就绪</p>' +
        '<div class="export-actions"><button class="btn btn-primary" onclick="downloadYAML()">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
        '下载 YAML</button><button class="btn btn-secondary" onclick="copyYAML()">复制到剪贴板</button></div>';
    window._yaml = yaml; window._title = title;
}

function downloadYAML() {
    if (!window._yaml) return;
    const b = new Blob([window._yaml], { type: 'text/yaml;charset=utf-8' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(b);
    a.download = (window._title || 'screenplay') + '.yaml'; a.click(); URL.revokeObjectURL(a.href);
}

function copyYAML() {
    if (!window._yaml) return;
    navigator.clipboard.writeText(window._yaml).then(() => alert('已复制!'));
}

function escapeHtml(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
