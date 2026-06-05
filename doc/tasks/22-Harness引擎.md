# 模块 22：Harness 引擎（novel2screen）

> 基于阶段的 PipeLine 引擎、输出验证器、保真度（幻觉）检测、小说阅读器。

## 子任务

- [ ] 合并 `orchestrator.py` — 基于阶段的 PipeLine 引擎（6-stage Fast / 11-stage Full）
- [ ] 合并 `orchestrator.py` — `build_fast_pipeline()` 快速管线阶段组装
- [ ] 合并 `orchestrator.py` — `build_full_pipeline()` 完整管线阶段组装
- [ ] 合并 `orchestrator.py` — `_normalize_episodes()` LLM 输出深度标准化
- [ ] 合并 `orchestrator.py` — `state_to_response()` API 响应转换
- [ ] 合并 `output_validator.py` — 超越 Pydantic 的额外校验（情感标签、角色 ID、场景计数等）
- [ ] 合并 `output_validator.py` — 角色保真度检测（对照原文检查角色名）
- [ ] 合并 `fidelity.py` — 幻觉检测：虚构角色/地点检查
- [ ] 合并 `fidelity.py` — `validate_character_ids_in_episodes()`
- [ ] 合并 `fidelity.py` — `run_fidelity_check()` 完整保真度检查
- [ ] 合并 `novel_reader.py` — 语言检测（中文/英文）
- [ ] 合并 `novel_reader.py` — 章节解析多格式支持
- [ ] 合并 `novel_reader.py` — Token 估算与智能分块
