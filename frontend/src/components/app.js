// ── Navigation ──
document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const target = link.getAttribute("href").slice(1);
        document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
        document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
        document.getElementById(target).classList.add("active");
        link.classList.add("active");
    });
});

// ── File Upload ──
document.getElementById("fileInput").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    document.getElementById("novelText").value = text;
    const title = document.getElementById("title");
    if (title.value === "未命名作品" || title.value === "Untitled") {
        title.value = file.name.replace(/\.(txt|md)$/, "");
    }
});

// ── Progress ──
function showProgress() {
    document.getElementById("progress").classList.remove("hidden");
    document.getElementById("progressFill").style.width = "0%";
    updateProgress(5, "正在连接服务器...");
}

function updateProgress(pct, text) {
    document.getElementById("progressFill").style.width = pct + "%";
    document.getElementById("progressText").textContent = text;
}

function hideProgress() {
    document.getElementById("progressFill").style.width = "100%";
    setTimeout(() => {
        document.getElementById("progress").classList.add("hidden");
    }, 600);
}

function showError(msg) {
    const preview = document.getElementById("previewContent");
    preview.innerHTML = '<div class="empty-state"><span class="empty-icon">⚠️</span><p style="color:var(--error)">' + msg.replace(/\n/g, "<br>") + "</p></div>";
    document.querySelector("[href='#preview']").click();
}

// ── Main Convert ──
async function convertNovel() {
    const title = document.getElementById("title").value || "Untitled";
    const genre = document.getElementById("genre").value;
    const modeRadios = document.getElementsByName("mode");
    let mode = "";
    for (const r of modeRadios) {
        if (r.checked) mode = r.value;
    }
    if (mode === "auto") mode = "";
    const demo = document.getElementById("demoMode").checked;
    const novelText = document.getElementById("novelText").value;

    if (!novelText || novelText.length < 100) {
        alert("请输入至少100字符的小说内容");
        return;
    }

    const btn = document.getElementById("convertBtn");
    btn.disabled = true;
    btn.textContent = "处理中...";

    updateProgress(10, "正在解析小说内容...");

    updateProgress(15, demo ? "Demo模式：快速生成中..." : "正在调用AI模型分析...");
    const result = await convertNovelText(title, genre, mode, novelText, demo);

    btn.disabled = false;
    btn.textContent = "开始转换";

    if (!result) return;

    updateProgress(90, "正在生成报告...");
    displayScreenplay(result.screenplay_yaml, result);
    displayCriticReport(result.violations, result.critic_score);
    setupExport(result.screenplay_yaml, title);

    document.querySelector("[href='#preview']").click();
}

// ── Display Screenplay ──
function displayScreenplay(yaml, result) {
    const content = document.getElementById("previewContent");
    if (!yaml) {
        content.innerHTML = '<div class="empty-state"><span class="empty-icon">😕</span><p>未能生成剧本内容</p></div>';
        return;
    }
    const stats = document.getElementById("previewStats");
    if (result) {
        stats.innerHTML = [
            '<span class="stat-badge">📊 ' + (result.mode || result.status || "") + '</span>',
            '<span class="stat-badge">📖 ' + (result.chapters_processed || "?") + ' 章</span>',
            '<span class="stat-badge">👥 ' + (result.characters_extracted || "?") + ' 角色</span>',
            '<span class="stat-badge">📺 ' + (result.episodes_planned || "?") + ' 集</span>',
            '<span class="stat-badge">🎬 ' + (result.scenes_written || "?") + ' 场</span>'
        ].join("");
    }
    content.innerHTML = '<div class="yaml-viewer">' + escapeHtml(yaml) + '</div>';
}

// ── Critic Report ──
function displayCriticReport(violations, score) {
    const report = document.getElementById("criticReport");
    const content = document.getElementById("criticContent");
    if (!violations || violations.length === 0) {
        report.classList.add("hidden");
        return;
    }
    report.classList.remove("hidden");
    const scoreClass = score >= 0.8 ? "good" : score >= 0.6 ? "fair" : "poor";
    const scoreLabel = score >= 0.8 ? "优秀" : score >= 0.6 ? "一般" : "需改进";
    let html = '<div style="margin-bottom:16px">';
    html += '<span class="score-badge ' + scoreClass + '">⭐ 质量评分: ' + (score * 100).toFixed(0) + "/100 (" + scoreLabel + ")</span>";
    html += "</div>";
    for (const v of violations) {
        const sev = v.severity || "warning";
        html += '<div class="violation-item ' + sev + '">';
        html += '<span class="violation-severity">' + sev + "</span>";
        html += '<div><span class="violation-category">' + (v.category || "") + "</span>";
        html += v.description + "</div></div>";
    }
    content.innerHTML = html;
}

// ── Export ──
function setupExport(yaml, title) {
    const content = document.getElementById("exportContent");
    let h = '<p style="margin-bottom:12px;color:var(--text-muted)">剧本 <strong style="color:var(--text)">' + escapeHtml(title) + '</strong> 已就绪</p>';
    h += '<div class="export-actions">';
    h += '<button class="btn btn-primary" onclick="downloadYAML()">下载 YAML</button>';
    h += '<button class="btn btn-secondary" onclick="copyYAML()">复制到剪贴板</button>';
    h += '</div>';
    content.innerHTML = h;
    window._exportYAML = yaml;
    window._exportTitle = title;
}

function downloadYAML() {
    const yaml = window._exportYAML;
    const title = window._exportTitle || "screenplay";
    if (!yaml) return;
    const blob = new Blob([yaml], { type: "text/yaml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = title + ".screenplay.yaml";
    a.click();
    URL.revokeObjectURL(url);
}

function copyYAML() {
    const yaml = window._exportYAML;
    if (!yaml) return;
    navigator.clipboard.writeText(yaml).then(() => {
        alert("已复制到剪贴板！");
    });
}

// ── Helpers ──
function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
