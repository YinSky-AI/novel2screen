# Demo 演示讲解词

## 场景 1：项目概述（30 秒）

> **"Novel2Screen 是一个 AI 驱动的多智能体小说改编剧本系统。你只需粘贴 3 章以上的小说文本，它就能自动生成结构化 YAML 剧本——包含角色档案、世界观设定、分集大纲、场景节拍和对白。今天我们演示它的核心能力。"**
> 
> **设计亮点：** 11 个专业 Agent 组成流水线，每个 Agent 只负责一件事——叙事分析、角色提取、世界观构建、时间线追踪、剧集规划、场景设计、对白写作、质量评审、自动修复、一致性检查，以及预处理。这遵循了单一职责原则，让每个环节都可以独立优化。"

## 场景 2：提示词工程（1 分钟）

> **"在讲功能之前，先看一个关键设计——提示词工程。这可能是整个系统最重要的部分。我们的每个 Agent 都配备了两套提示词模板，以 NarrativeAgent 为例，打开 `backend/core/prompts.py`：**
>
> **"能看到 V2 版本的提示词采用了结构化五段式设计——ROLE 角色定义、OUTPUT_SCHEMA 输出约束、CONSTRAINTS 规则限制、THINKING_STEPS 思维链、EXAMPLE 少样本示例——这是经过 20+ 次迭代后的最佳实践。比起简单的 'You are an expert, do X'，这套格式让 LLM 输出更稳定、幻觉率更低。特别是 Few-Shot Example 部分，我们为每个 Agent 都手工编写了完整的输入输出示例，相当于给模型做了一次 in-context learning。"**
>
> **"再看 CONSTRAINTS 里的限制——'只提取有明确出场和描写的角色，不要臆造角色'、'角色弧线必须基于原文实际发展，不要推测未发生的变化'——这些都是在对抗大模型的编造倾向。做完约束之后，我们还加了一层 Hallucination Detection——在输出验证阶段，检查模型是否编造了原文中不存在的角色名或地名。"**
>
> **"另外，如果你输入的是中文小说，所有 Agent 的 prompt 会自动切换到中文 V2 版本。角色标签也会输出为'主角/反派/配角'而不是 protagonist/antagonist。这是语言自适应设计。"**

## 场景 3：Fast 模式实时演示（2 分钟）

> **"现在演示 Fast 模式。粘贴这段 3 章的小说——一个关于赛博朋克都市里黑客少年追查真相的故事。Pipeline 选 Fast。"**
>
> **"点击 Convert，看到进度条实时更新。每个阶段都是中文文字提示——当前走到哪一步一目了然。这个进度不是前端写死的动画，而是后端 workflow 在每个 Agent 完成后推送给前端的真实状态。"**
>
> **"Fast 模式只做 3 次 LLM 调用——叙事提取、角色分析、场景对话合成——大约 30 秒完成。输出是完整的 YAML 剧本结构：title、logline、characters 列表带 role 标签、episodes 带 scenes 和 beats。"**
>
> **"注意看这里的 emotion 字段——每个 beat 都标注了情感状态。还有 character_id，标记了每句台词/动作属于哪个角色。这些都是我们要求的输出 schema 中的必填字段。"**
>
> **"往下看 Quality Assessment 面板——这是后端 `evaluate_yaml_quality()` 函数对生成的剧本做的自动评估。emotion 空值率 5%、character_id 完整度 98%、duration 多样性 75%——用绿色/黄色/红色直观展示质量。这些都是 AI 输出质量的硬指标。"**

## 场景 4：编辑与导出（30 秒）

> **"如果对输出不满意，可以点 Edit 进入编辑模式。这里就是标准的文本编辑器。你可以手动调整角色的台词或者场景的节奏。改完之后点 Save 保存，或者用 Validate 校验格式。"**
>
> **"旁边的 Download 按钮可以直接下载 .yaml 文件。这个 YAML 可以用在任何后续的剧本编辑工具里。"**

## 场景 5：Full 模式对比（1 分钟）

> **"Fast 模式快但浅。如果你的小说更长、更复杂，用 Full 模式。它走完整的 9+ Agent 链——先做预处理，提取关键节点（对话、时间地点对、开头结尾句），这些节点会作为 must_preserve 注入后续每个 Agent 的 prompt，防止模型丢失重要信息。"**
>
> **"然后走 Narrative → Character → World → Timeline 四个分析 Agent，接着是 Episode Planner 生成剧集骨架。但这里有个关键设计——骨架生成后不是直接往下走，而是先交给 CriticAgent 对照 must_preserve 打分。分数低于阈值就重试。这就是骨架校验机制。"**
>
> **"通过后才走 Scene Planner → Dialogue Writer → 最终 YAML 编译。整个过程约 3-5 分钟，但质量比 Fast 模式高一个量级。"**

## 场景 6：技术架构速览（30 秒）

> **"最后总结一下技术栈。后端是 Python + FastAPI，LLM 默认用 DeepSeek（也支持 OpenAI/Anthropic/Ollama 自动回退）。向量检索用 ChromaDB + BGE 中文嵌入模型。前端是纯 Vanilla JS，没有 React/Vue 依赖，零 node_modules，一个 python -m http.server 就能跑。"**
>
> **"整个项目 68 个单元测试全部通过，覆盖了 Schema 验证、Agent 输出逻辑、预处理管线、端到端流程。你可以放心地在它的基础上构建自己的改编流水线。"**

---

## 录制提示

| 场景 | 时长 | 屏幕内容 | 同步操作 |
|------|------|----------|----------|
| 1 项目概述 | 30s | 首页 + 架构图 | 口播，鼠标划过 UI |
| 2 提示词工程 | 60s | VS Code 打开 prompts.py | 滚动展示 V2 prompt 结构 |
| 3 Fast 演示 | 120s | 浏览器全程 | 粘贴文本 → Convert → 等结果 → 滚动 YAML |
| 4 编辑导出 | 30s | 结果页 | 点 Edit → 改一行 → Save → Download |
| 5 Full 对比 | 60s | 浏览器 + 后端日志 | 选 Full → Convert → 看进度阶段 |
| 6 技术总结 | 30s | 终端跑 pytest | 强调 68 测试全过 + 技术栈 |

**总时长：约 5 分 30 秒**
