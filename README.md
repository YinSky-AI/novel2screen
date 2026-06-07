# Novel2Screen

> AI-Powered Multi-Agent System for Novel-to-Screenplay Conversion

将小说自动改编为结构化剧本（YAML 格式）的多智能体系统。输入 3 章以上小说文本，输出可直接编辑、可进一步打磨的剧本初稿。

## Demo

![demo](https://img.shields.io/badge/Python-3.12-blue) ![tests](https://img.shields.io/badge/tests-68%20passed-green) ![license](https://img.shields.io/badge/license-MIT-yellow)

## Features

- **双管线模式**：Fast（3次LLM调用，~30s）和 Full（9+ Agent链，~3-5min），智能按文本量路由
- **11个专业Agent**：叙事提取 → 角色分析 → 世界观构建 → 时间线 → 剧集规划 → 场景规划 → 对话写作 → 质量评审 → 自动修复 → 一致性检查
- **RAG检索增强**：ChromaDB向量库 + BGE中文embedding，生成前检索原文片段注入Prompt
- **关键节点检测**：自动提取对话/时间地点/首尾句，强制要求LLM保留
- **骨架校验**：Full模式先生成剧集骨架，CriticAgent对照原文关键点打分，不合格自动重试
- **质量评估面板**：前端实时显示 emotion 空值率、character_id 完整度、duration 多样性
- **语言自适应**：中文输入→中文剧本，英文输入→英文剧本，角色标签自动匹配
- **幻觉检测**：对比原文角色名/地名，标记虚构内容
- **多提供商回退**：DeepSeek → OpenAI → Anthropic → Ollama 自动切换

## Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入 DeepSeek Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

### 3. 启动后端

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API文档：http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
python -m http.server 3000 --bind 127.0.0.1
```

浏览器打开：**http://localhost:3000**

## Architecture

```
Novel Text → Parser → ModeRouter
    ↓
NarrativeAgent → CharacterAgent → WorldAgent → TimelineAgent
    ↓
EpisodePlanner → ScenePlanner → DialogueWriter
    ↓
CriticAgent → RepairAgent → FidelityCheck → YAML Export
    ↑                    ↑
  Key Point Detector   Quality Evaluator (frontend panel)
```

| 模块 | 说明 |
|------|------|
| `backend/agents/` | 11个Agent + AgentBase基类（RAG/retry/JSON修复） |
| `backend/core/` | LLM客户端、记忆系统（ChromaDB）、预处理、路由、数据库 |
| `backend/schemas/` | Pydantic v2数据模型 + YAML序列化/校验 |
| `backend/workflows/` | Fast/Full双管线编排 + 保真度检测 |
| `backend/harness/` | 管线引擎、输出验证、小说阅读器 |
| `frontend/` | 暖色调SPA，中英文自适应，质量评估面板 |
| `mcp-server/` | MCP stdin/stdout桥接服务 |
| `tests/` | 68 tests（单元+集成+质量验证） |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/convert` | 主转换端点（fast/full/demo/auto） |
| `POST` | `/novels/upload` | 上传小说文件 |
| `POST` | `/generate/{task_id}` | 开始生成（pipeline参数） |
| `GET` | `/tasks/{task_id}` | 获取任务状态、进度、质量评估 |
| `GET` | `/export/yaml/{task_id}` | 下载YAML |
| `POST` | `/import-edits/{task_id}` | 上传编辑后YAML并校验 |
| `GET` | `/alignment/{task_id}` | 一致性报告 |
| `POST` | `/validate` | 校验YAML格式 |
| `GET` | `/health` | 健康检查 |

## YAML Output Schema

```yaml
title: string
logline: string
genre: string
theme: string
characters:
  - id: char_001
    name: string
    role: protagonist|antagonist|supporting  (中文: 主角|反派|配角)
    goal: string
    arc: string
episodes:
  - id: ep_001
    title: string
    summary: string
    scenes:
      - scene_id: sc_001
        location: string
        time: string
        visual_focus: string|null
        sound_effect: string|null
        beats:
          - type: dialogue|action|silence|reaction
            character_id: string|null
            content: string
            emotion: string|null
            source: string       # 可选，原文证据引用
        transition: cut|fade|dissolve|wipe
        duration_estimate: string   # "45s", "2m"
```

## Testing

```bash
pytest tests/ -v
```

68 tests: Schema模型 / Agent逻辑 / 章节解析与分块 / 关键节点检测 / 质量评估器 / 角色语言映射 / YAML完整性 / 管线集成

## Tech Stack

- **Python 3.12** + FastAPI + Pydantic v2
- **ChromaDB** + sentence-transformers (BAAI/bge-small-zh-v1.5, ~100MB)
- **DeepSeek** 主LLM（支持OpenAI/Anthropic/Ollama备选）
- **SQLite** 本地存储
- **Vanilla JS** + CSS Variables（无需Node.js）
