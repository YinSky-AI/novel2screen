# 模块 11：DialogueWriter（对话写作）

> 为每个场景填充对话与动作节拍，确保符合角色说话风格。

## 子任务

- [x] `dialogue.py` — AgentBase 继承，`run()` 方法实现
- [x] `dialogue.py` — `validate()` 方法（beats ≥ 2）
- [x] 节拍类型：dialogue / action / silence / reaction
- [x] 每条对话匹配角色的 `voice_style`
- [x] 对话推动剧情或揭示角色
- [x] 每场最多 3 行连续 exposition
- [ ] 解决完整流水线中场景组装逻辑的脆弱性（`scenes_in_episode` 键缺失问题）
