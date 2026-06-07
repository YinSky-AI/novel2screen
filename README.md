# Novel2Screen

> AI-Powered Multi-Agent System for Novel-to-Screenplay Conversion

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-68%20passed-green)](.)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

**Demo 演示视频：[Bilibili →](https://www.bilibili.com/video/BV1uQEx6uEEf/)**

将小说自动改编为结构化剧本（YAML 格式）的多智能体系统。输入 3 章以上小说文本，输出可直接编辑的剧本初稿，支持中英文自适应。

## Features

- **双管线模式**：Fast（3次LLM调用，~30s）和 Full（9+ Agent链，~3-5min），自动按文本量路由
- **11个专业Agent**：预处理 → 叙事分析 → 角色提取 → 世界观构建 → 时间线 → 剧集规划 → 场景设计 → 对白写作 → 质量评审 → 自动修复 → 一致性检查
- **五段式提示词工程**：每个 Agent 配备结构化 Prompt（ROLE / SCHEMA / CONSTRAINTS / THINKING_STEPS / EXAMPLE），带少样本示例和反幻觉约束
- **RAG检索增强**：ChromaDB向量库 + BGE中文嵌入，每个 Agent 生成前检索原文片段注入 Prompt
- **关键节点检测**：自动提取对话/时间地点/首尾句，作为 must_preserve 强制保留
- **骨架校验 + 重试**：Full 模式生成剧集骨架后，CriticAgent 对照关键点打分，不合格自动重试
- **质量评估面板**：前端实时显示 emotion 空值率、character_id 完整度、duration 多样性
- **语言自适应**：中文输入 → 中文 Prompt + 中文剧本；英文输入 → 英文 Prompt + 英文剧本
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

### 3. 启动

```bash
# 后端 (终端1)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (终端2)
cd frontend
python -m http.server 3000 --bind 127.0.0.1
```

浏览器打开：**http://localhost:3000**

API 文档：http://localhost:8000/docs

## Architecture

```
Novel Text → Parser → ModeRouter
    ↓
Preprocessor → NarrativeAgent → CharacterAgent → WorldAgent → TimelineAgent
    ↓
EpisodePlanner → ScenePlanner → DialogueWriter → YAMLCompiler
    ↓                ↑
CriticAgent ← Key Point Detector → Must-Preserve Injection
    ↓
RepairAgent → FidelityCheck → Export → Quality Evaluator (frontend)
```

| 模块 | 说明 |
|------|------|
| `backend/agents/` | 11个Agent + AgentBase基类（RAG/retry/JSON修复） |
| `backend/core/` | LLM客户端、记忆系统（ChromaDB）、Prompt工程、预处理、路由 |
| `backend/schemas/` | Pydantic v2数据模型 + YAML序列化/校验 |
| `backend/workflows/` | Fast/Full双管线编排 |
| `backend/harness/` | 管线引擎、输出验证、保真度检测 |
| `frontend/` | 暖色调 SPA，中英文切换，质量评估面板 |
| `mcp-server/` | MCP stdin/stdout 桥接服务 |
| `docs/` | Demo 解讲词、Prompt 工程文档 |
| `tests/` | 68 个测试（单元 + 集成） |

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/convert` | 主转换端点 (fast/full/demo/auto) |
| `POST` | `/novels/upload` | 上传小说文件 |
| `POST` | `/generate/{task_id}` | 开始生成 |
| `GET` | `/tasks/{task_id}` | 获取任务状态、进度、质量评估 |
| `GET` | `/export/yaml/{task_id}` | 下载 YAML |
| `POST` | `/validate` | 校验 YAML 格式 |
| `GET` | `/health` | 健康检查 |

## Testing

```bash
pytest tests/ -v
```

68 tests: Schema 模型 / Agent 逻辑 / 章节解析与分块 / 关键节点检测 / 质量评估器 / 角色语言映射 / YAML 完整性 / 管线集成

## Tech Stack

- **Python 3.12** + FastAPI + Pydantic v2
- **ChromaDB** + sentence-transformers (BAAI/bge-small-zh-v1.5, ~100MB)
- **DeepSeek** 主 LLM（OpenAI / Anthropic / Ollama 备选）
- **SQLite** 本地存储
- **Vanilla JS** + CSS Variables（零 Node.js 依赖）
