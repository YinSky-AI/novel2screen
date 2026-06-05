# Novel2Screen — Vibe Coding Prompt

> 本文件是整个 Vibe Coding 过程的唯一入口 Prompt。主 Agent 根据此文件执行所有任务，无需人工介入。

---

## 一、项目概述

将小说自动改编为结构化剧本（YAML 格式）的多智能体系统。支持两种 Pipeline：
- **Fast**（2~3 次 LLM 调用，适合生产默认）
- **Full**（9+ Agent 链式调用，适合长篇小说）

**输入**：小说文本（最少 3 章）
**输出**：结构化剧本 YAML（Pydantic → YAML 序列化）

---

## 二、项目结构（目标状态）

项目以 `backend/` 为主代码库。需要将 `novel2screen/backend/harness/` 中的 Harness 引擎合并到 `backend/` 中。

```
novel2screen/
├── backend/              # 主后端代码（目标工作目录）
│   ├── agents/           # 11 个 Agent + 基类
│   │   ├── base.py           # AgentBase (ABC: run/validate/retry)
│   │   ├── narrative.py
│   │   ├── character.py
│   │   ├── world.py
│   │   ├── timeline.py
│   │   ├── episode_planner.py
│   │   ├── scene_planner.py
│   │   ├── dialogue.py
│   │   ├── critic.py
│   │   ├── repair.py
│   │   └── consistency.py
│   ├── core/             # LLM 客户端、记忆系统、提示、预处理
│   │   ├── llm.py
│   │   ├── prompts.py
│   │   ├── prompt_loader.py
│   │   ├── memory.py
│   │   ├── database.py
│   │   ├── preprocessor.py
│   │   ├── fact_extractor.py
│   │   └── router.py
│   ├── harness/          # [NEW] 从 novel2screen/backend/harness/ 合并过来
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── output_validator.py
│   │   ├── fidelity.py
│   │   └── novel_reader.py
│   ├── schemas/
│   │   ├── models.py
│   │   └── validator.py
│   ├── workflows/
│   │   └── novel2screen.py
│   ├── prompts/          # YAML 提示模板
│   ├── config.py
│   └── main.py           # FastAPI 入口
├── frontend/
│   ├── index.html
│   └── src/
│       ├── components/app.js
│       ├── utils/api.js
│       └── styles/main.css
├── tests/
│   ├── unit/
│   │   ├── test_schema.py
│   │   ├── test_schemas.py
│   │   └── test_agents.py
│   └── integration/
│       └── test_pipeline.py
├── data/
├── mcp-server/
│   └── server.py
├── doc/
│   └── tasks/           # 任务划分文件（每个模块一个 .md）
├── pyproject.toml        # [NEW] mypy + ruff 配置
├── README.md
└── docker-compose.yml
```

---

## 三、起点状态（已完成的内容）

以下模块已 **完全实现并通过验证**（无需重写，可直接使用）：

| 模块 | 说明 |
|------|------|
| 05 NarrativeAgent | 叙事提取（事件、子情节、转折点、主题） |
| 06 CharacterAgent | 角色档案提取 |
| 07 WorldAgent | 世界观构建（Long 模式） |
| 09 EpisodePlanner | 剧集结构规划 |
| 10 ScenePlanner | 场景规划 |
| 13 CriticAgent | 质量评审 |
| 15 ConsistencyAgent | 双向一致性检查 |
| AgentBase | 基类（run/validate/retry） |
| LLMClient | DeepSeek → OpenAI → Anthropic → Ollama → Demo 后备 |
| ModelRouter | 模型路由 + 指数退避重试 |
| Pydantic Schema | 完整数据模型 |
| ORM 模型 | SQLAlchemy（Novel/Chapter/CharacterDB/EpisodeDB/SceneDB/BeatDB/HumanEdit/Export） |
| 记忆系统 | STM / CharacterBible / WorldBible / SemanticMemory (ChromaDB) |
| 提示模板 | 所有 Agent Prompt 常量 + YAML 文件 |

以下模块 **部分完成**（需修复/补充）：

| 模块 | 剩余任务数 | 主要内容 |
|------|-----------|----------|
| 18 工作流编排 | 5 | 修复 Full Pipeline 已知 Bug、合并 Orchestrator |
| 22 Harness 引擎 | 13 | [NEW] 从 novel2screen/ 合并整个 harness 模块 |
| 20 前端应用 | 7 | 高级上传/编辑/对齐 UI |
| 19 后端 API | 6 | 任务持久化、端点合并、CORS、速率限制 |
| 24 测试 | 7 | API 测试、E2E、质量测试 |
| 17 记忆系统 | 2 | 关键词搜索增强、verify_yaml_against_facts |
| 21 人机协作 | 4 | 前端 YAML 编辑器、差异对比 UI |
| 01 基础架构 | 3 | 配置合并、API 密钥安全 |
| 25 部署 | 2 | Docker 服务同步、nginx |
| 其他模块 | 少量 | 见各任务文件 |

---

## 四、环境与工具链

### 4.1 Python 环境

使用 **Python 3.12**（当前系统未安装时请创建 Conda/venv 环境）。

```bash
# 如需要，创建 Python 3.12 环境
conda create -n novel2screen python=3.12 -y
conda activate novel2screen
# 或使用 venv
python -m venv venv
.\venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 4.2 所需依赖

```txt
# backend/requirements.txt（按需补充以下包）
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.0.0
pyyaml>=6.0
openai>=1.6.0
anthropic>=0.8.0
sqlalchemy>=2.0.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
httpx>=0.25.0
python-multipart>=0.0.6
pytest>=8.0
pytest-asyncio>=0.23.0
ruff>=0.3.0
mypy>=1.8.0
```

### 4.3 代码检查（必须通过）

#### ruff（严格模式）
```bash
ruff check backend/ tests/ --fix
```

#### mypy（严格模式）
```bash
mypy --strict backend/ --ignore-missing-imports
```

**要求**：
- ruff 零错误（所有规则启用）
- mypy 严格模式通过（`--ignore-missing-imports` 用于第三方库）
- 修改后自动修复（`ruff --fix`）

**pyproject.toml 配置**（需创建）：
```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["ALL"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "ANN001", "ANN201", "D100", "D101", "D102", "D103", "D104", "D107", "PLR2004", "PLR0913", "ARG001", "ARG002", "ARG003", "ARG004", "ARG005", "T20"]

[tool.mypy]
strict = true
ignore_missing_imports = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 4.4 测试（必须通过）

```bash
pytest tests/ -v --tb=short
```

**要求**：
- 所有已有测试必须通过（含已有通过的 28 个测试）
- 新增代码必须覆盖以下测试：
  - 每个新模块的单元测试（正常路径 + 边缘情况）
  - API 端到端集成测试（使用 TestClient）
  - 质量测试（对话自然度、可拍摄性、台词均衡）
  - Harness 引擎测试（orchestrator、output_validator、fidelity、novel_reader）

---

## 五、执行顺序（里程碑驱动）

所有剩余的待办任务分散在 25 个模块文件中（`doc/tasks/*.md`）。按以下里程碑顺序执行：

### 阶段 0：环境准备（启动时必须完成）

- [ ] 创建 Python 3.12 环境
- [ ] 安装依赖
- [ ] 创建 `pyproject.toml`（含 ruff/mypy 配置）
- [ ] 验证当前测试全部通过

### 阶段 1：基础设施修补（模块 01、17、19 中未完成项）

- [ ] 合并 `novel2screen/backend/config.py` 的额外配置项
- [ ] 补充 `verify_yaml_against_facts()` 实现
- [ ] 增强 `SemanticMemory._keyword_search()` 后备搜索
- [ ] `_task_store` 从内存 dict 迁移到数据库持久化
- [ ] 限制 CORS `allow_origins` 为白名单（非 `*`）
- [ ] 添加 API 速率限制

### 阶段 2：工作流加固（模块 18、08、11、12、14）

- [ ] **修复 Full Pipeline Bug：**
  - `scenes_in_episode` → `scenes` 键名修正
  - `dialogue_idx` 索引计算修复
  - TimelineAgent 输出接入 EpisodePlanner
  - 场景组装逻辑重写（消除脆弱假设）
- [ ] YAML 编译器提示集成到工作流
- [ ] RepairAgent 返回结构化为 `RepairOutput`
- [ ] 更新 ModelRouter 模型表匹配设计方案 §13

### 阶段 3：Harness 引擎集成（模块 22 — 重中之重）

- [ ] 创建 `backend/harness/` 目录
- [ ] 迁移 `orchestrator.py`（基于阶段的 Pipeline 引擎）
  - `build_fast_pipeline()` / `build_full_pipeline()`
  - `_normalize_episodes()` 深度标准化
  - `state_to_response()` 转换
- [ ] 迁移 `output_validator.py`（情感标签、角色 ID、场景计数等校验）
  - 集成 `ValidationReport` / `validate_emotion_labels()` / 等
- [ ] 迁移 `fidelity.py`（幻觉检测）
  - `detect_fabricated_characters()` / `detect_fabricated_locations()`
  - `validate_character_ids_in_episodes()` / `run_fidelity_check()`
- [ ] 迁移 `novel_reader.py`（语言检测、章节解析、智能分块）
  - `detect_language()` / `parse_chapters()` / `estimate_tokens()` 等
- [ ] 编写 `harness/__init__.py` 导出全部公共 API
- [ ] **删除 `novel2screen/` 目录**（完成迁移后）

### 阶段 4：前端增强（模块 20、21）

- [ ] `uploadNovelFile()` UI 集成
- [ ] `/novels/upload` + `/generate/{task_id}` 高级上传工作流 UI
- [ ] YAML 编辑器组件
- [ ] `/import-edits` 导入 UI
- [ ] `/alignment` 一致性报告可视化
- [ ] 差异对比可视化
- [ ] 错误状态处理、语言选择

### 阶段 5：测试全覆盖（模块 24）

- [ ] Preprocessor 单元测试
- [ ] Harness 引擎单元测试（orchestrator / output_validator / fidelity / novel_reader）
- [ ] API 端到端测试（httpx TestClient）
- [ ] 人机协作工作流测试（import-edits / alignment）
- [ ] 对话自然度测试（LLM-as-Judge）
- [ ] 可拍摄性测试、台词均衡测试
- [ ] pytest-cov 覆盖率配置

### 阶段 6：部署就绪（模块 25 + 其他收尾）

- [ ] 更新 Docker Compose（ChromaDB 替代 Qdrant，SQLite 或 PG）
- [ ] nginx 配置（反向代理 + 静态文件）
- [ ] 统一环境变量管理
- [ ] MCP Server 错误处理完善
- [ ] API 密钥安全管理（推荐环境变量而非 `.env`）

---

## 六、子 Agent 任务分配原则

主 Agent 按以下方式分配子 Agent：

1. **每次只聚焦一个阶段**（Phase 0→1→2→...）
2. **每个阶段内部，每个模块分配一个子 Agent**
3. **子 Agent 的输入**：该模块的 `doc/tasks/XX-模块名.md` + 本 Prompt
4. **子 Agent 必须**：
   - 读取当前所有相关代码文件
   - 只完成该模块的未勾选子任务
   - 不重写已完成的代码
   - 为该模块编写完整的 pytest 测试
   - 运行 `ruff check` + `mypy` 确保零错误
   - 运行 `pytest` 确保所有测试通过
5. **主 Agent 在每阶段结束后**：
   - 运行完整测试套件、ruff、mypy
   - 更新 `progress.md` 中的完成状态
   - 确定所有检查通过后进入下一阶段

---

## 七、必须遵守的规则

1. **不重写已有完成代码** — 除非修复 Bug，否则不修改标记为 `[x]` 的子任务对应的代码
2. **先读后改** — 修改任何文件前先完整阅读当前内容
3. **每个模块必须有自己的测试文件** — 测试覆盖正常路径 + 边缘情况
4. **ruff 零错误** — `ruff check --fix` 后必须无任何错误
5. **mypy 严格通过** — `mypy --strict` 通过（可 `# type: ignore` 处理第三方库）
6. **不修改 `doc/tasks/` 中的勾选状态** — 那是人工跟踪用的，代码 Agent 不修改
7. **整个过程中不删除已有功能** — 除非被明确要求
8. **`novel2screen/` 目录迁移后删除** — 合并完成并且测试通过后清理

---

## 八、成功标准

最终验证清单（全部必须通过）：

| 检查项 | 命令 |
|--------|------|
| ruff 检查 | `ruff check backend/ tests/` → 零错误 |
| mypy 检查 | `mypy --strict backend/ --ignore-missing-imports` → 通过 |
| 单元测试 | `pytest tests/unit/ -v` → 全部通过 |
| 集成测试 | `pytest tests/integration/ -v` → 全部通过 |
| 完整测试 | `pytest tests/ -v` → 全部通过（≥40 个测试） |
| FastAPI 启动 | `python -c "from backend.main import app; print('OK')"` → OK |
| 快速流水线 | `POST /convert` 含 `pipeline=fast` → 返回 YAML |
| 完整流水线 | `POST /convert` 含 `pipeline=full` → 返回 YAML |
| YAML 导出 | `GET /export/yaml/{task_id}` → 有效 YAML |
| 编辑导入 | `POST /import-edits/{task_id}` → 协调后 YAML |
| 健康检查 | `GET /health` → `{"status": "ok"}` |
| MCP 服务 | `python mcp-server/server.py` → 启动正常 |

---

## 九、各模块详细任务索引

每个模块的详细子任务见 `doc/tasks/` 目录中对应的 `.md` 文件：

| 文件 | 内容 |
|------|------|
| `01-基础架构与配置.md` | config 合并、API 密钥安全、数据库迁移 |
| `03-小说解析与预处理.md` | novel_reader 合并、语言检测、智能分块 |
| `04-模式路由.md` | ModelRouter 模型表更新 |
| `08-TimelineAgent.md` | 时间线输出接入下游 |
| `11-DialogueWriter.md` | Full Pipeline 场景组装修复 |
| `12-YAMLCompiler.md` | YAML 编译器提示集成 |
| `14-RepairAgent.md` | RepairOutput 结构化返回 |
| `16-提示工程.md` | Prompt 格式合规、PromptLoader 集成 |
| `17-记忆系统.md` | 关键词搜索增强、verify_yaml_against_facts |
| `18-工作流编排.md` | Full Pipeline Bug 修复 + Orchestrator 合并 |
| `19-后端API.md` | 任务持久化、端点合并、CORS、速率限制 |
| `20-前端应用.md` | 高级上传/编辑/对齐 UI |
| `21-人机协作工作流.md` | 前端 YAML 编辑器、差异可视化 |
| `22-Harness引擎.md` | [新模块] 整个 Harness 引擎从 novel2screen 合并 |
| `23-MCP服务.md` | Fast Pipeline 支持、错误处理 |
| `24-测试.md` | 全部测试补充 |
| `25-部署与Docker.md` | Docker 更新、nginx 配置 |
