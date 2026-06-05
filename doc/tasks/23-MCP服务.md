# 模块 23：MCP 服务

> Model Context Protocol 桥接服务，通过 stdin/stdout 接受外部调用。

## 子任务

- [x] `server.py` — 接收 JSON 请求，响应 stdout
- [x] 支持 `"convert"` 动作（完整流水线）
- [x] 支持 `"validate"` 动作（YAML 校验）
- [ ] 支持 `"convert"` 快速流水线（当前只使用 `workflow.run`）
- [ ] 添加错误处理（API 密钥缺失等情况）
- [ ] 修复相对导入路径问题（当前依赖 `..backend.workflows`）
