const API_BASE = "";

async function convertNovelText(title, genre, mode, novelText, demo) {
    showProgress();

    try {
        const resp = await fetch(API_BASE + "/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                novel_text: novelText,
                title: title,
                genre: genre,
                mode: mode,
                demo: demo,
            }),
        });

        const data = await resp.json();
        hideProgress();

        if (data.status === "error") {
            showError(data.error);
            return null;
        }

        return data;
    } catch (err) {
        hideProgress();
        showError("连接失败: " + err.message + "\n请确保后端服务已启动 (python -m novel2screen.backend.main)");
        return null;
    }
}

async function uploadNovelFile(file, title, genre, mode) {
    showProgress();

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    formData.append("genre", genre);
    formData.append("mode", mode);

    try {
        const resp = await fetch(API_BASE + "/convert/file", {
            method: "POST",
            body: formData,
        });

        const data = await resp.json();
        hideProgress();

        if (data.status === "error") {
            showError(data.error);
            return null;
        }

        return data;
    } catch (err) {
        hideProgress();
        showError("上传失败: " + err.message);
        return null;
    }
}

async function validateYaml(yamlText) {
    const formData = new FormData();
    formData.append("yaml_text", yamlText);

    try {
        const resp = await fetch(API_BASE + "/validate", {
            method: "POST",
            body: formData,
        });
        return await resp.json();
    } catch (err) {
        return { valid: false, errors: [err.message] };
    }
}


// Override default fetch timeout
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
  if (!options.signal) {
    const controller = new AbortController();
    options.signal = controller.signal;
    setTimeout(() => controller.abort(), 600000);
  }
  return originalFetch(url, options);
};
