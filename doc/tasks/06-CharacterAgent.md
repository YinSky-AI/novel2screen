# 模块 06：CharacterAgent（角色提取）

> 抽取所有角色档案，包括 ID、姓名、角色类型、目标、恐惧、弧光、说话风格。

## 子任务

- [x] `character.py` — AgentBase 继承，`run()` 方法实现
- [x] `character.py` — `validate()` 方法（characters ≥ 1）
- [x] 输入：小说文本块
- [x] 输出：`{"characters": [{"id", "name", "role", "goal", "fear", "arc", "voice_style"}]}`
- [x] 角色 ID 格式：`char_001` / `char_002` ...
