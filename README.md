# ============================================================
# 企业法务知识库与法规制度智能问答系统
# ============================================================

基于 **RAG + GraphRAG** 架构构建的企业法务知识库与法规制度智能问答系统，实现企业制度、合同、法规文档的智能检索与问答，并支持答案引用溯源。

## 核心能力

- ✅ 企业法务知识库构建（PDF / Word / TXT / MD 文档解析）
- ✅ 法务文档智能切片（章节 + 条款优先级策略）
- ✅ Hybrid Retrieval 混合检索（向量 + BM25 + RRF 融合 + Reranker）
- ✅ GraphRAG 知识图谱增强（实体关系抽取 + Neo4j 多跳查询）
- ✅ 引用溯源（答案绑定文件 / 章节 / 条款 / 页码）
- ✅ 幻觉控制（Citation Checker + 可信度评分）
- ✅ 权限管理（JWT + RBAC）
- ✅ 异步任务（Celery + Redis）

## 技术栈

| 模块 | 技术 |
| ---- | ---- |
| 后端 | Python + FastAPI |
| LLM | DeepSeek / Qwen / OpenAI |
| RAG | LangChain 思想 + 自研检索链路 |
| Embedding | BGE / OpenAI |
| 向量数据库 | Milvus |
| 知识图谱 | Neo4j |
| 关系数据库 | PostgreSQL |
| 缓存/队列 | Redis + Celery |
| 部署 | Docker Compose |

## 架构

```
用户浏览器 → Nginx → FastAPI
                        ├── RAG 检索链路（Milvus + BM25 + RRF + Reranker）
                        ├── GraphRAG 链路（Neo4j 知识图谱）
                        ├── LLM 生成（引用溯源）
                        └── 异步任务（Celery + Redis）
```

## 快速开始

### 方式一：Docker Compose 一键部署（生产 / 服务器）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key

# 2. 一键启动所有服务
docker compose up -d --build

# 3. 查看服务状态
docker compose ps

# 4. 访问
#   API 文档: http://服务器IP/docs
#   健康检查: http://服务器IP/health
```

### 方式二：本地 Mock 模式（无服务器、无重组件验证）

```bash
# 无需 Milvus / Neo4j / LLM，端到端验证逻辑
cd scripts
USE_MOCK=true python demo.py
```

## API 接口

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| POST | /api/auth/login | 用户登录（获取 JWT） |
| GET | /api/auth/profile | 当前用户信息 |
| POST | /api/document/upload | 上传文档 |
| GET | /api/document/list | 文档列表 |
| DELETE | /api/document/{id} | 删除文档 |
| POST | /api/chat/query | 智能问答 |
| GET | /api/chat/history | 历史记录 |
| GET | /api/knowledge/status | 知识库状态 |

### 默认账号

| 用户名 | 密码 | 角色 |
| ------ | ---- | ---- |
| admin | admin123 | 管理员 |
| legal | legal123 | 法务 |
| employee | emp123 | 员工 |

## 前端 Demo 页面

部署后访问 `http://服务器IP/` 即可使用前端界面，包含四个页面：

| 页面 | 功能 |
| ---- | ---- |
| 首页概览 | 知识库状态统计 |
| 智能问答 | 输入问题 → 检索 → 生成答案 + 引用溯源 + 可信度 |
| 文档管理 | 上传 / 列表 / 删除知识文档 |
| 知识图谱 | 实体关系可视化（SVG 绘制） |

前端为纯静态 HTML/CSS/JS，无需构建，由 Nginx 直接托管并反向代理 `/api` 到后端。

## 项目结构

```
legal-ai-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── api/               # 接口层（auth/document/chat/knowledge）
│   │   ├── core/              # 配置/数据库/安全/日志
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应
│   │   ├── services/          # 业务逻辑层
│   │   ├── repositories/      # 数据访问层
│   │   ├── rag/               # RAG 检索（embedding/retriever/hybrid）
│   │   ├── graph/             # 知识图谱（extractor/graph_store/query）
│   │   ├── document/          # 文档处理（parser/cleaner/splitter/pipeline）
│   │   ├── llm/               # LLM 调用（client/prompt/answer_generator）
│   │   └── tasks/             # Celery 异步任务
│   └── requirements.txt
├── docker/                    # Dockerfile / nginx / entrypoint
├── frontend/                  # 前端 Demo 页面（静态 HTML/CSS/JS）
├── docker-compose.yml
├── knowledge_base/sample/     # 示例知识文档
├── scripts/demo.py            # Mock 验证脚本
├── tests/                     # 单元测试
├── docs/                      # 设计文档
└── .env.example
```

## 测试

```bash
USE_MOCK=true pytest tests/ -v
```

## 许可

仅供学习与面试展示使用。
