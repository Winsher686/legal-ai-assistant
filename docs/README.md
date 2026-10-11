# 项目设计文档索引

本项目严格遵循《项目B：企业法务知识库与法规制度智能问答系统》11 阶段规划实现。

## 阶段与代码对应关系

| 阶段 | 内容 | 对应代码 |
| ---- | ---- | -------- |
| 阶段二 | 系统总体架构 | `docs/02-系统架构.md` |
| 阶段三 | 数据模型与数据库 | `backend/app/models/`、`backend/app/rag/vector_store.py`、`backend/app/graph/graph_store.py` |
| 阶段四 | 文档解析与知识库构建 | `backend/app/document/` |
| 阶段五 | RAG 检索链路 | `backend/app/rag/` |
| 阶段六 | GraphRAG 知识图谱 | `backend/app/graph/` |
| 阶段七 | 问答生成与引用溯源 | `backend/app/llm/` |
| 阶段八 | 后端 API 与工程化 | `backend/app/api/`、`backend/app/services/` |
| 阶段九 | 项目代码结构 | 本仓库目录结构 |
| 阶段十 | 测试评估优化 | `tests/` |
| 阶段十一 | 部署与展示 | `docker-compose.yml`、`docs/12-部署指南.md` |
