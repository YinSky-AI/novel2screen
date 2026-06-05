# Novel2Screen 🎬

> Multi-Agent System for Novel-to-Screenplay Conversion  
> 将小说自动改编为结构化剧本，支持 DeepSeek / OpenAI / Anthropic

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ 特性

- **多 Agent 协作** — 9 个专职 Agent 分别处理叙事分析、角色提取、世界观、分集规划、场景设计、对话编写、质量评审
- **快速流水线** — 2~3 次 LLM 调用完成全流程，比传统串行方案快 6~8 倍
- **Demo 模式** — 一键生成样例剧本，无需等待 AI 响应
- **多模型支持** — DeepSeek → OpenAI → Anthropic 自动降级
- **暗色 Web UI** — 三页签界面（转换 / 预览 / 导出），支持文件上传与剪贴板复制

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- DeepSeek API Key（推荐）或 OpenAI / Anthropic Key

### 安装运行

```bash
# 1. 克隆仓库
git clone https://github.com/YinSky-AI/novel2screen.git
cd novel2screen

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 设置 API Key
set DEEPSEEK_API_KEY=sk-your-key-here  # Windows
# export DEEPSEEK_API_KEY=sk-your-key-here  # macOS/Linux

# 5. 启动后端
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

打开浏览器访问 **http://localhost:8000**

---

## 🧠 架构

```
用户输入小说
    │
    ▼
┌─────────────────┐
│  Parser + 分章   │  自动识别章节边界
└────────┬────────┘
         ▼
┌─────────────────┐
│  预处理 (1次调用) │  叙事结构 + 角色 + 世界观 → JSON 摘要
└────────┬────────┘
         ▼
┌─────────────────┐
│  批量规划 (1次调用)│  分集 + 场景 + 对话节奏 → 完整剧本
└────────┬────────┘
         ▼
┌─────────────────┐
│  快速评审 (可选)   │  质量评分 + 问题检测
└────────┬────────┘
         ▼
    📄 YAML 剧本
```

### 两种模式

| 模式 | LLM 调用 | 耗时 | 说明 |
|------|----------|------|------|
| ⚡ Demo | 0 | < 1s | 预生成样例，即时预览 |
| 🤖 AI | 2~3 | 15~30s | DeepSeek 真实分析生成 |

---

## 📁 项目结构

```
novel2screen/
├── backend/
│   ├── agents/          # 9 个 AI Agent 模块
│   │   ├── narrative.py   # 叙事结构分析
│   │   ├── character.py   # 角色提取
│   │   ├── world.py       # 世界观构建
│   │   ├── timeline.py    # 时间线整理
│   │   ├── episode_planner.py  # 分集规划
│   │   ├── scene_planner.py    # 场景设计
│   │   ├── dialogue.py    # 对话编写
│   │   ├── critic.py      # 质量评审
│   │   └── repair.py      # 自动修复
│   ├── core/            # LLM 客户端、记忆系统、预处理
│   ├── schemas/         # Pydantic 数据模型与验证
│   ├── workflows/       # LangGraph 风格编排器
│   └── main.py          # FastAPI 入口
├── frontend/
│   ├── index.html       # Web UI 入口
│   └── src/
│       ├── components/  # JS 组件逻辑
│       ├── utils/       # API 调用封装
│       └── styles/      # 暗色主题 CSS
├── tests/               # 单元测试 & 集成测试
├── mcp-server/          # MCP 协议服务
└── docker-compose.yml   # Docker 部署配置
```

---

## 🔌 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Web UI 首页 |
| `POST` | `/convert` | 文本转剧本 (支持 demo 参数) |
| `POST` | `/convert/file` | 上传 txt/md 文件转换 |
| `POST` | `/validate` | 校验 YAML 剧本格式 |
| `GET` | `/export/{title}` | 下载剧本 YAML 文件 |
| `GET` | `/docs` | Swagger API 文档 |

---

## 🎮 使用示例

### Web UI

1. 打开 http://localhost:8000
2. 粘贴小说内容（至少 100 字符）
3. 选择类型和模式
4. 点击 "开始转换"
5. 在预览页查看结果，导出页下载 YAML

### API 调用

```bash
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{
    "novel_text": "第一章 初入江湖\n\n夜雨潇潇...\n\n第二章 恩怨情仇...\n\n第三章 决战前夕...",
    "title": "江湖风雨录",
    "genre": "Drama",
    "demo": false
  }'
```

---

## 🛠 技术栈

- **后端**: FastAPI + Pydantic + PyYAML
- **AI**: DeepSeek (OpenAI 兼容) / OpenAI / Anthropic
- **编排**: LangGraph 风格状态机
- **前端**: 原生 HTML/CSS/JS（暗色主题）

---

## 📝 License

MIT © YinSky-AI
