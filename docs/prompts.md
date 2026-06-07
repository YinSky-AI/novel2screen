# 提示词工程文档

## 设计原则

Novel2Screen 的所有 Agent 提示词采用**结构化五段式设计**：

```
# ROLE        → 角色定位：“你是谁”
# OUTPUT_SCHEMA → 输出约束：“必须输出什么格式”
# CONSTRAINTS → 规则限制：“什么不能做”
# THINKING_STEPS → 思维链：“按什么步骤思考”
# EXAMPLE     → 少样本示例：“正确输出长什么样”
```

这套格式经过 20+ 次迭代验证，相比简单的一句 "You are an expert, do X"，能显著降低 LLM 的幻觉率和格式偏差。

## Agent 提示词索引

| Agent | 文件位置 | 核心任务 | 关键约束 |
|-------|----------|----------|----------|
| NarrativeAgent | `prompts.py:209` | 拆解叙事结构 | 转折点必须对应原文事件；不编造情节 |
| CharacterAgent | `prompts.py:237` | 提取角色档案 | 每个角色必须有独特 voice_style；只提取已有角色 |
| WorldAgent | `prompts.py:262` | 构建世界观 | 地点按重要性排序；规则要标注例外 |
| TimelineAgent | `prompts.py:285` | 追踪因果事件链 | cause/effect 用 event_id 建立闭环 |
| EpisodePlanner | `prompts.py:307` | 拆分剧集 | 每集完整三幕；A/B/C 线必须有交集 |
| ScenePlanner | `prompts.py:331` | 设计拍摄场景 | 每场有明确冲突；beats 带 subtext |
| DialogueWriter | `prompts.py:355` | 撰写角色对白 | 每句体现 voice_style；不能是水词 |
| CriticAgent | `prompts.py:379` | 质量评审 | critical 级问题必须修复 |
| RepairAgent | `prompts.py:404` | 修复问题 | 不引入新元素；长度增减 <20% |
| ConsistencyChecker | `prompts.py:427` | 一致性验证 | 矛盾必须引用两个位置 |
| Preprocessor | `prompts.py:450` | 预处理小说 | 摘要 <10% 篇幅；覆盖所有章节 |

## V1 vs V2 提示词

- **V1** (第 1-201 行): 简洁英文提示词，适用于英文小说输入
- **V2** (第 209-513 行): 完整中文提示词，含结构化 ROLE/SCHEMA/CONSTRAINTS/STEPS/EXAMPLE

系统根据输入语言自动选择版本。中文输入 → V2 中文 prompt → 中文输出；英文输入 → V1 英文 prompt → 英文输出。

## 关键设计决策

### 1. Few-Shot Example（少样本示例）

每个 V2 prompt 都包含完整的手写示例。以 CharacterAgent 为例：

```json
{
  "id": "li_wen",
  "name": "李文",
  "role": "protagonist",
  "voice_style": "直白简洁，喜欢用短句，压力大时用反问句",
  "voice_example": "他们说得都对——我就是不行。但不行也得行。"
}
```

这不是简单的格式示范——**示例本身就是 in-context learning**，模型会模仿示例的风格和深度。

### 2. Anti-Hallucination（反幻觉设计）

多条约束直指 LLM 最大的问题——编造：

```
"每个转折点必须明确对应原文中的具体事件或章节"
"只提取有明确出场和描写的角色，不要臆造角色"
"不能引入新的人物或情节元素"
"角色弧线必须基于原文实际发展，不要推测未发生的变化"
```

加上输出验证阶段的 Hallucination Detection（比对原文角色名/地名），形成双重防护。

### 3. Chain-of-Thought（思维链）

每个 Agent 的 THINKING_STEPS 指导 LLM "怎么想"，而不是只告诉它"要什么结果"。例如 ScenePlanner：

```
1. 理解本集的核心冲突和情感轨迹
2. 将冲突分解为 2-4 个关键场景
3. 确定每场戏的进场点（in media res）和出场点
4. 逐场设计节拍（beats），确保每个节拍推动冲突升级
5. 添加视觉和声音提示，增强导演可读性
6. 检查场景间的情感起伏是否有节奏感
```

### 4. Must-Preserve 注入

预处理阶段提取的**关键节点**（对话、时间地点对、开头/结尾句）会作为 `must_preserve` 注入到后续所有 Agent 的 prompt 中，确保：
- 核心对话不被改写
- 关键场景不被遗漏
- 原文情感基调不被扭曲

### 5. 骨架校验 + 重试

Full 模式的 EpisodePlanner 输出后，CriticAgent 先对照 `must_preserve` 打分。分数 < 阈值（50 分）则自动重试，直到合格或达到最大重试次数。

## 加载机制

提示词通过 `backend/core/prompt_loader.py` 加载：

```python
# 根据语言自动选择 V1/V2
def get_prompt(agent_name: str, lang: str = "zh") -> dict:
    if lang == "zh":
        return V2_PROMPTS.get(agent_name, V1_PROMPTS[agent_name])
    return V1_PROMPTS[agent_name]
```

所有提示词集中在 `prompts.py` 一个文件中，避免散落在各 Agent 代码里——方便非开发人员（编剧/导演）参与调优。
