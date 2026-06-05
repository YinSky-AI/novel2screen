# Novel2Screen YAML Schema 规范

> 版本：2.0.0 | 最后更新：2025-06-05

---

## 1. 概述

Novel2Screen 将小说转化为机器可读的 YAML 剧本文件。该 Schema 定义了剧本的完整数据结构，涵盖角色、分集、场景、节拍等层级，同时兼顾人类可读性与编程解析的严谨性。

---

## 2. 设计原则

### 2.1 影视优先的层级模型

剧本不是扁平文本，而是多级嵌套结构。Schema 采用 **剧本 → 分集 → 场景 → 节拍** 的四层树形模型，映射真实的影视制作流程：

```
Screenplay (剧本)
  ├── Character[] (角色库)
  └── Episode[] (分集)
        └── Scene[] (场景)
              └── Beat[] (节拍)
```

**设计原因**：每层对应一个独立的生产环节——剧本统筹→分集规划→分镜设计→逐拍编写。层级分离后，任何一层都可独立修改而不影响其他层，也便于不同的 Agent 各司其职。

### 2.2 角色集中管理

所有角色定义在剧本根级的 `characters` 数组中，场景和节拍通过 `character_id` 引用角色。

**设计原因**：
- **避免冗余**：角色信息只维护一份，修改角色属性（如弧光、目标）后全局生效
- **一致性校验**：评审 Agent 可通过 ID 交叉校验角色的出场频率、弧光完整性
- **导出灵活性**：可将 `characters` 单独导出为角色表供选角使用

### 2.3 Beat 作为最小粒度

每个场景由若干个 `Beat`（节拍）组成。Beat 是剧本的最小原子单元，类型包括：
- `dialogue` — 对话
- `action` — 动作 / 场景描述
- `reaction` — 反应镜头
- `silence` — 沉默 / 停顿

**设计原因**：
- **镜头参考**：每个 Beat 包含 `emotion` 和隐含的节奏信息，导演可直接据此设计镜头
- **时长估算**：场景级 `duration_estimate` 由 Beat 数量推算，辅助排期
- **对话平衡检测**：Critic Agent 可统计 dialogue Beat 与 action Beat 的比例，自动检测"对话过多"或"动作过多"的问题

### 2.4 Pydantic 驱动的校验层

所有 Schema 同步定义了 Pydantic 模型（`backend/schemas/models.py`），提供：
- 字段类型校验（`str`, `int`, `Enum`, `Optional`）
- 正则约束（`id` 字段必须匹配 `char_\d+`、`sc_\d+`、`ep_\d+` 格式）
- 列表最小长度约束（`characters`、`episodes`、`scenes`、`beats` 至少包含 1 个元素）

**设计原因**：LLM 生成的 YAML 不可靠，Pydantic 作为最后一道防线在序列化前拦截格式错误。

---

## 3. 完整 Schema

### 3.1 Screenplay（剧本根对象）

```yaml
title: string         # 剧本标题
logline: string       # 一句话梗概（logline）
genre: string         # 类型标签：xuanhuan|dushi|xianxia|kehuan|xuanyi|yanqing|lishi
theme: string         # 主题概括
characters:           # 角色列表（≥ 1 个）
  - Character
episodes:             # 分集列表（≥ 1 个）
  - Episode
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | `string` | ✅ | 剧本标题，与小说标题对应 |
| `logline` | `string` | ✅ | 一句话梗概，用于快速了解故事核心 |
| `genre` | `string` | ✅ | 类型标签 |
| `theme` | `string` | ✅ | 主题概括，指导统一的创作方向 |
| `characters` | `Character[]` | ✅ | 角色列表，至少 1 个 |
| `episodes` | `Episode[]` | ✅ | 分集列表，至少 1 集 |

### 3.2 Character（角色）

```yaml
id: char_001          # 角色 ID，格式 char_\d+
name: string          # 角色名称
role: string          # protagonist | antagonist | supporting
goal: string          # 角色目标
fear: string          # 角色恐惧（可选）
arc: string           # 角色弧光
voice_style: string   # 说话风格（可选）
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | ✅ | 格式 `char_数字`，如 `char_001` |
| `name` | `string` | ✅ | 角色名 |
| `role` | `enum` | ✅ | 主角 / 反派 / 配角 |
| `goal` | `string` | ✅ | 角色在故事中的驱动目标 |
| `fear` | `string` | ❌ | 内心恐惧，丰富角色深度 |
| `arc` | `string` | ✅ | 角色成长轨迹描述 |
| `voice_style` | `string` | ❌ | 说话风格提示，指导对话 Agent |

### 3.3 Episode（分集）

```yaml
id: ep_001            # 分集 ID，格式 ep_\d+
title: string         # 分集标题
summary: string       # 分集概要
scenes:               # 场景列表（≥ 1 个）
  - Scene
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | ✅ | 格式 `ep_数字` |
| `title` | `string` | ✅ | 本集标题 |
| `summary` | `string` | ✅ | 一句话概述本集内容 |
| `scenes` | `Scene[]` | ✅ | 场景列表，至少 1 场 |

### 3.4 Scene（场景）

```yaml
scene_id: sc_001      # 场景 ID，格式 sc_\d+
location: string      # 地点
time: string          # 时间（如 "夜"、"黄昏"、"清晨"）
visual_focus: string  # 视觉焦点描述（可选）
sound_effect: string  # 音效提示（可选）
voice_over: string    # 画外音（可选）
beats:                # 节拍列表（≥ 1 个）
  - Beat
transition: string    # 转场方式：cut | fade | dissolve | wipe
duration_estimate: string  # 预估时长，如 "120s"
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene_id` | `string` | ✅ | 格式 `sc_数字` |
| `location` | `string` | ✅ | 场景发生地点 |
| `time` | `string` | ✅ | 时间描述 |
| `visual_focus` | `string` | ❌ | 镜头焦点建议 |
| `sound_effect` | `string` | ❌ | 音效设计提示 |
| `voice_over` | `string` | ❌ | 画外音 / 内心独白 |
| `beats` | `Beat[]` | ✅ | 节拍列表，至少 1 个 |
| `transition` | `enum` | ❌ | 转场方式，默认 `cut` |
| `duration_estimate` | `string` | ❌ | 预估时长，默认 `120s` |

### 3.5 Beat（节拍）

```yaml
type: string          # dialogue | action | silence | reaction
character_id: char_001  # 说话/行动角色 ID（非 dialogue 时可选）
content: string       # 对话内容或动作描述
emotion: string       # 情感标记（可选）
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `enum` | ✅ | 节拍类型 |
| `character_id` | `string` | ❌ | 关联角色 ID，dialogue 场景必填 |
| `content` | `string` | ✅ | 对话台词或动作描述 |
| `emotion` | `string` | ❌ | 情感标签，如 "愤怒"、"平静" |

---

## 4. 完整示例

```yaml
title: "江湖风雨录"
logline: "少年剑客为查明师父死因，卷入一场席卷武林的阴谋"
genre: xuanhuan
theme: "复仇与正义的边界"
characters:
  - id: char_001
    name: "李剑飞"
    role: protagonist
    goal: "查明师父死因"
    fear: "辜负师父遗志"
    arc: "从复仇少年成长为守护江湖的大侠"
    voice_style: "沉稳内敛"

  - id: char_002
    name: "柳如烟"
    role: supporting
    goal: "保护李剑飞"
    fear: "再次失去重要的人"
    arc: "从旁观者到并肩作战的伙伴"
    voice_style: "温柔坚定"

  - id: char_003
    name: "暗影楼主"
    role: antagonist
    goal: "掌控武林"
    fear: "身份暴露"
    arc: "权力膨胀到自我毁灭"
    voice_style: "阴冷傲慢"

episodes:
  - id: ep_001
    title: "初入江湖"
    summary: "李剑飞离开师门，在客栈遇到神秘老人，得知师父之死另有隐情"
    scenes:
      - scene_id: sc_001
        location: "古道客栈大厅"
        time: "深夜"
        visual_focus: "雨夜客舍，烛光摇曳"
        sound_effect: "窗外淅沥雨声"
        beats:
          - type: action
            character_id: char_001
            content: "李剑飞推开门，雨水顺着斗笠滴落。他环顾大厅，在角落的空桌坐下"
            emotion: null

          - type: dialogue
            character_id: char_002
            content: "这位少侠，这么大的雨还在赶路？"
            emotion: "好奇"

          - type: dialogue
            character_id: char_001
            content: "赶路的人，顾不得天气。"
            emotion: "平静"

          - type: action
            character_id: char_001
            content: "角落里一个老人突然开口。李剑飞的手按上剑柄"
            emotion: null

          - type: dialogue
            character_id: char_003
            content: "你师父的死，另有隐情。"
            emotion: "低沉"

          - type: reaction
            character_id: char_001
            content: "李剑飞瞳孔骤缩，缓缓转过身"
            emotion: "震惊"
        transition: fade
        duration_estimate: "150s"
```

---

## 5. 验证规则

| 规则 | 位置 | 说明 |
|------|------|------|
| ID 格式校验 | Pydantic | `char_\d+` / `sc_\d+` / `ep_\d+` 正则匹配 |
| 非空列表 | Pydantic | `characters`、`episodes`、`scenes`、`beats` ≥ 1 |
| 类型枚举 | Pydantic | `role`、`beat_type`、`transition` 限值列表 |
| 角色引用完整性 | Critic Agent | 所有 `character_id` 需存在于 `characters` 中 |
| 连续性问题 | Critic Agent | 跨场景角色状态、时间线一致性 |
| 对话/动作平衡 | Critic Agent | 每场景 dialogue Beat 不超过 80% |

---

## 6. 扩展预留

Schema 支持通过 `metadata` 字段扩展（不在核心模型中，但 YAML 导出时可由 `exclude_none=False` 包含），未来可添加：

- `target_audience` — 目标观众
- `budget_tier` — 预算级别
- `camera_notes` — 摄影指导
- `casting_hints` — 选角建议
