# 模块 25：部署与 Docker

> Docker Compose 多服务编排、启动脚本、环境变量配置。

## 子任务

- [x] `docker-compose.yml` — 定义 5 个服务（backend, frontend, postgres, redis, qdrant）
- [x] `start_backend.ps1` — 本地启动脚本
- [ ] 更新 Docker Compose：Qdrant → ChromaDB（当前代码使用 ChromaDB）
- [ ] 更新 Docker Compose：PostgreSQL → SQLite（当前 ORM 使用 SQLite，或保持 PG 并补全集成）
- [ ] 添加 nginx 配置（设计方案中提到但未实现）
- [ ] 统一环境变量管理（backend/config.py 与 docker-compose 环境变量同步）
