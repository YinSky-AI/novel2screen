# 模块 12：YAMLCompiler（YAML 编译）

> 将结构化数据组装为最终 YAML 剧本文件。

## 子任务

- [x] `validator.py` — `screenplay_to_yaml()` 序列化
- [x] `workflows/novel2screen.py` — `_build_screenplay()` 组装 Screenplay 对象
- [x] 输出格式符合设计方案 §5 YAML Schema
- [x] 字段：title, logline, genre, theme, characters, episodes
- [x] 场景字段：scene_id, location, time, visual_focus, sound_effect, voice_over, beats, transition, duration_estimate
- [ ] 集成 YAML 编译器提示（`YAML_COMPILER_SYSTEM` 已定义但未主动使用）
