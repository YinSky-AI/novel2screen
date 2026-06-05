# 模块 19：后端 API

> FastAPI 服务器、所有 REST 端点。

## 子任务

- [x] `main.py` — FastAPI 应用创建 + CORS
- [x] `POST /novels/upload` — 上传小说文件
- [x] `POST /generate/{task_id}` — 开始生成（Short/Long 模式）
- [x] `GET /tasks/{task_id}` — 获取任务状态和当前输出
- [x] `GET /export/yaml/{task_id}` — 下载最终 YAML
- [x] `POST /import-edits/{task_id}` — 上传编辑后的 YAML
- [x] `GET /alignment/{task_id}` — 获取一致性报告
- [x] `GET /health` — 健康检查
- [x] `POST /convert` — 主转换端点（Fast / Full 流水线 + Demo 模式）
- [x] `POST /convert/file` — 文件上传转换
- [x] `POST /validate` — YAML 验证
- [x] `GET /export/{title}` — 下载导出 YAML
- [x] `GET /usage` — LLM 用量统计
- [x] 演示模式固定 YAML 返回
- [ ] `_task_store` 从内存 dict 迁移到数据库持久化
- [ ] 合并 `POST /detect-language` 端点（来自 novel2screen）
- [ ] 合并 `GET /harness/pipelines` 端点
- [ ] 统一任务 ID 生命周期管理
- [ ] 添加速率限制与认证
- [ ] 限制 CORS `allow_origins` 为白名单
