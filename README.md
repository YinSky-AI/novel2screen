# Novel2Screen

> AI-Powered Multi-Agent System for Novel-to-Screenplay Conversion

将小说自动改编为结构化剧本（YAML 格式）的多智能体系统。支持 Fast / Full 两种 Pipeline，RAG 检索增强，幻觉检测，人机协作编辑回路。

## Features

- **双管线模式**：Fast（2~3次LLM调用）和 Full（9+ Agent链），自动按章节数路由
- **11个专业Agent**：叙事提取 → 角色分析 → 世界观构建 → 时间线组织 → 剧集规划 → 场景规划 → 对话写作 → 质量评审 → 自动修复 → 一致性检查
- **RAG检索增强**：ChromaDB向量库 + BGE embedding，每个Agent生成前自动检索原文片段注入Prompt
- **幻觉检测**：自动检测模型是否编造了不存在的角色或地点
- **两轮修正**：Agent输出验证失败时，将具体错误反馈给模型重新生成
- **多提供商回退**：DeepSeek → OpenAI → Anthropic → Ollama 自动切换，无Key时Demo模式
- **人机协作**：支持编辑YAML后重新导入、差分对比、一致性报告
- **Model Context Protocol**：MCP服务支持stdin/stdout外部调用

## Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，至少配置一个LLM提供商的Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

> 不配任何Key时会自动使用Demo模式返回示例剧本。

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

浏览器打开：http://localhost:3000

## Architecture

```
Upload → Parser → ModeRouter
  ↓
NarrativeAgent → CharacterAgent → WorldAgent → TimelineAgent
  ↓
EpisodePlanner → ScenePlanner → DialogueWriter → YAMLCompiler
  ↓
CriticAgent → RepairAgent → FidelityCheck → Export
```

| 模块 | 说明 |
|------|------|
| `backend/agents/` | 11个Agent + AgentBase基类 |
| `backend/core/` | LLM客户端、记忆系统、预处理、路由、数据库 |
| `backend/schemas/` | Pydantic数据模型 + YAML校验 |
| `backend/workflows/` | Fast/Full管线编排 |
| `backend/harness/` | 管线引擎、输出验证、保真度检测、小说阅读器 |
| `frontend/` | 暖色调SPA，支持中英文切换 |
| `mcp-server/` | MCP stdin/stdout桥接服务 |
| `tests/` | 单元测试 + 集成测试 |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/convert` | 主转换端点 (fast/full/demo/auto) |
| `POST` | `/novels/upload` | 上传小说文件 |
| `POST` | `/generate/{task_id}` | 开始生成 (mode + pipeline参数) |
| `GET` | `/tasks/{task_id}` | 获取任务状态和进度 |
| `GET` | `/export/yaml/{task_id}` | 下载最终YAML |
| `POST` | `/import-edits/{task_id}` | 上传编辑后的YAML |
| `GET` | `/alignment/{task_id}` | 获取一致性报告 |
| `POST` | `/validate` | 校验YAML格式 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/usage` | 用量统计 |
| `POST` | `/detect-language` | 语言检测 |

## YAML Output Schema

```yaml
title: string
logline: string
genre: string
theme: string
characters:
  - id: char_001
    name: string
    role: protagonist|antagonist|supporting
    goal: string
    arc: string
episodes:
  - id: ep_001
    title: string
    summary: string
    scenes:
      - scene_id: sc_01
        location: string
        time: string
        visual_focus: string|null
        sound_effect: string|null
        beats:
          - type: dialogue|action|silence|reaction
            character_id: string|null
            content: string
            emotion: string|null
        transition: cut|fade|dissolve|wipe
        duration_estimate: string
```

## Model Routing

| Agent | Model | Reason |
|-------|-------|--------|
| NarrativeAgent | DeepSeek | Fast extraction |
| CharacterAgent | DeepSeek | Simple profiling |
| ScenePlanner | DeepSeek | Structured planning |
| CriticAgent | DeepSeek | Deep reasoning |
| DialogueWriter | DeepSeek | Fast generation |
| RepairAgent | DeepSeek | Quick fixes |

## Docker

```bash
docker-compose up -d
```

服务：backend(:8000) + frontend(:3000) + chromadb(:8001)

## Testing

```bash
pytest tests/ -v
```

## Tech Stack

- **Python 3.12** + FastAPI + Pydantic v2
- **ChromaDB** 向量检索 + sentence-transformers (BGE)
- **DeepSeek / OpenAI / Anthropic** 多提供商LLM
- **SQLite** 本地存储
- **Vanilla JS** 前端 (ES Modules, CSS Variables)
