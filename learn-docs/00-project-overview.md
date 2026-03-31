# DeepAgentForce 项目概览

## 项目定位

DeepAgentForce 是一个**多租户 AI 智能体平台**（v2.0.0），基于 FastAPI 构建，提供企业级的 AI 对话、知识库检索（RAG）、用户画像挖掘和可扩展的 Skill（技能）系统。核心亮点是**多租户数据隔离**——不同租户的会话、知识库、配置、用户画像等完全隔离。

## 技术栈

| 层级 | 技术 |
|---|---|
| **Web 框架** | FastAPI + Uvicorn |
| **前端** | 原生 HTML/CSS/JS（无框架），静态文件托管 |
| **AI Agent** | `deepagents` + `langgraph` + `langchain` |
| **LLM** | OpenAI 兼容接口（通过 `LLM_URL` / `LLM_API_KEY` 配置） |
| **向量数据库** | Milvus Lite（本地嵌入式） |
| **关系数据库** | MySQL（SQLAlchemy ORM，同步 + 异步） |
| **认证** | JWT（PyJWT + bcrypt） |
| **用户画像** | NetworkX 知识图谱 + PageRank 算法 |
| **搜索** | Tavily API + Firecrawl |
| **文档处理** | pdfplumber、python-docx、reportlab |

## 核心架构

```
DeepAgentForce/
├── main.py                    # 应用入口，FastAPI 实例 + 路由挂载
├── config/
│   ├── settings.py            # 全局配置（Pydantic Settings，支持 .env + JSON）
│   └── prompts.py             # 提示词模板（任务规划/综合分析/搜索总结等）
├── src/
│   ├── api/
│   │   ├── routes.py          # 核心 API（对话/历史/RAG/配置/文件输出）
│   │   ├── websocket.py       # WebSocket 流式对话 + 会话历史管理
│   │   ├── skills_routes.py   # Skill 管理 API（CRUD/导入导出/验证）
│   │   └── auth_routes.py     # 认证 API（注册/登录/刷新Token）
│   ├── services/
│   │   ├── conversational_agent.py  # 核心 Agent（基于 deepagents + langgraph）
│   │   ├── rag.py             # RAG Pipeline（Milvus 向量检索）
│   │   ├── person_like_service.py   # 用户偏好挖掘（知识图谱 + 图算法）
│   │   ├── skill_manager.py   # Skill 管理器（内置 + 用户自定义）
│   │   ├── auth_service.py    # 认证服务（JWT/密码哈希/用户管理）
│   │   └── skills/            # 内置 Skills
│   │       ├── pdf-processing/    # PDF 处理（提取文本/表格/生成PDF）
│   │       ├── rag-query/         # 内部知识库查询
│   │       └── web-search/        # 网络搜索（Tavily）
│   ├── models/
│   │   └── user.py            # 数据模型（User/Tenant/TenantApiKey）
│   ├── database/
│   │   └── connection.py      # 数据库连接（MySQL 同步 + 异步）
│   ├── workflow/
│   │   └── callbacks.py       # 状态回调（Agent 事件 -> WebSocket）
│   └── utils/
│       ├── content_parse.py   # 文件内容解析
│       └── setting_utils.py   # 配置工具
├── static/                    # 前端静态文件
│   ├── index.html             # 主聊天页面
│   ├── login.html             # 登录页面
│   ├── register.html          # 注册页面
│   ├── skills.html            # Skill 管理页面
│   └── *.js                   # 前端逻辑
└── requirements.txt           # 依赖（270+ 包）
```

## 核心组件详解

### 1. DeepAgentForce 引擎

位于 [`main.py`](../main.py)，是整个应用的**核心调度器**：

- **多租户会话管理**：`sessions` 字典，key = `{tenant_uuid}_{session_id}`
- **多租户 RAG 引擎**：`_rag_engines` 字典，按需创建
- **SkillManager**：管理内置 Skills + 用户自定义 Skills
- **UserPreferenceMining**：用户偏好挖掘服务
- **ConversationHistoryManager**：会话历史持久化

关键方法：
- `get_or_create_session()` — 获取或创建租户会话
- `get_rag_engine()` — 获取租户专属 RAG pipeline
- `init_service()` — 重新初始化服务（租户切换时）

### 2. 对话 Agent（ConversationalAgent）

位于 [`src/services/conversational_agent.py`](../src/services/conversational_agent.py)：

- 基于 `deepagents` 库创建智能体，使用 `langgraph` 的 `MemorySaver` 做检查点
- 通过 `ShellTool` 执行 Python 脚本（即 Skill 的 scripts）
- **流式输出**：逐 token 通过 `StatusCallback` 推送到 WebSocket
- 系统提示词中注入了**用户画像摘要**，让 Agent 了解用户偏好
- 支持多租户：每个租户使用独立的 LLM 配置（通过 `get_tenant_settings()` 加载）

Agent 工作流程：
1. 接收用户消息
2. 判断意图（闲聊 vs 工具调用）
3. 如需工具：读取 SKILL.md → ShellTool 执行脚本
4. 流式返回 token → StatusCallback → WebSocket → 前端

### 3. RAG 知识库（MilvusRAGPipeline）

位于 [`src/services/rag.py`](../src/services/rag.py)：

| 步骤 | 实现 |
|---|---|
| 文档解析 | 支持 PDF / DOCX / TXT / CSV / MD |
| 文本分块 | tiktoken（cl100k_base），600 tokens/块，100 overlap |
| 向量化 | OpenAI 兼容的 Embedding API |
| 向量存储 | Milvus Lite，每个租户独立 collection |
| 检索 | 余弦相似度 top-k |

多租户隔离：
- Collection 命名：`rag_chunks_{tenant_uuid_safe}`
- 元数据文件：`data/rag_storage/doc_metadata_{tenant_uuid}.json`
- 按需初始化：首次访问时自动创建 collection 和索引

### 4. 用户偏好挖掘（UserPreferenceMining）

位于 [`src/services/person_like_service.py`](../src/services/person_like_service.py)，这是一个特色模块：

| 步骤 | 说明 |
|---|---|
| 1. 实体提取 | LLM 从对话历史中提取实体和关系 |
| 2. 图谱构建 | NetworkX 构建有向知识图谱 |
| 3. 偏好挖掘 | PageRank + 中心性分析 + 提及频率 → 综合偏好评分 |
| 4. 画像生成 | LLM 生成用户画像侧写（150字以内） |

触发时机：WebSocket 断开连接时自动触发挖掘。

偏好评分公式：
```
score = PageRank × 40% + 邻居权重 × 30% + 提及频率 × 30%
```

### 5. Skill 系统（SkillManager）

位于 [`src/services/skill_manager.py`](../src/services/skill_manager.py)：

**内置 Skills**（`src/services/skills/`，所有用户可见，不可删除）：

| Skill | 功能 | 脚本 |
|---|---|---|
| `pdf-processing` | PDF 读取 / 表格提取 / PDF 生成 | `extract_text.py`, `extract_tables.py`, `write_pdf.py` |
| `rag-query` | 内部知识库查询（按租户隔离） | `query.py` |
| `web-search` | Tavily 网络搜索 | `web_search.py` |

**用户自定义 Skills**（`data/user_skills/{user_id}/`，按用户隔离）：
- 前端可动态上传/安装/卸载/导出 Skill
- 每个 Skill 包含 `SKILL.md`（元数据 + 使用说明）和 `scripts/` 目录（Python 脚本）
- 支持语法验证和规范校验

Skill 目录结构：
```
skill-name/
├── SKILL.md          # 技能描述、使用说明、执行命令
└── scripts/
    └── main.py       # 技能脚本
```

### 6. 认证系统（AuthService）

位于 [`src/services/auth_service.py`](../src/services/auth_service.py)：

- JWT Token 认证（access_token + refresh_token）
- bcrypt 密码哈希
- 多租户支持：Token 中携带 `tenant_uuid`
- 支持创建新租户或加入已有租户

### 7. 数据模型

位于 [`src/models/user.py`](../src/models/user.py)：

| 模型 | 说明 |
|---|---|
| `Tenant` | 租户表（组织/公司），含 uuid、名称、代码、配额限制 |
| `User` | 用户表，关联 tenant_id + tenant_uuid，含角色、状态 |
| `TenantApiKey` | 租户 API Key 表，含使用限制和统计 |

### 8. 状态回调（StatusCallback）

位于 [`src/workflow/callbacks.py`](../src/workflow/callbacks.py)：

Agent 执行过程中的事件类型：
- `init` — 开始处理（🤔）
- `tool_start` — 调用工具（🔧）
- `tool_end` — 执行完成（✅）
- `finish` — 处理结束（🎯）
- `token` — 流式 token
- `error` — 错误

## 多租户体系

多租户是贯穿整个项目的核心设计：

### 认证层
- JWT Token 中携带 `tenant_uuid`
- 所有 API 路由通过 `get_tenant_uuid_from_request()` 提取
- WebSocket 通过 query_params 中的 token 提取

### 数据隔离

| 数据类型 | 存储路径/Key |
|---|---|
| 会话历史 | `data/history/{tenant_uuid}/session_*.json` |
| 知识库向量 | Milvus collection `rag_chunks_{tenant_uuid}` |
| 知识库元数据 | `data/rag_storage/doc_metadata_{tenant_uuid}.json` |
| 用户画像 | `data/person_like_{tenant_uuid}.json` |
| 配置文件 | `data/saved_config_{tenant_uuid}.json` |
| 上传文件 | `data/uploads/{tenant_uuid}/` |
| 输出文件 | `data/outputs/{tenant_uuid}/` |
| 用户 Skills | `data/user_skills/{user_id}/` |

### 数据库层
- `User` 表通过 `tenant_id` + `tenant_uuid` 关联 `Tenant` 表
- `TenantApiKey` 表通过 `tenant_id` + `tenant_uuid` 关联 `Tenant` 表

## API 端点总览

### 认证

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/api/auth/register` | 用户注册（支持创建/加入租户） |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 对话

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/api/chat` | 同步对话 |
| POST | `/api/chat/upload` | 带附件的对话 |
| WS | `/ws/stream` | WebSocket 流式对话 |

### 对话历史

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/history/saved` | 获取会话列表 |
| GET | `/api/history/session/{id}` | 获取会话详情 |
| DELETE | `/api/history/session/{id}` | 删除会话 |

### RAG 知识库

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/api/rag/documents/upload` | 上传文档到知识库 |
| GET | `/api/rag/documents` | 列出文档 |
| DELETE | `/api/rag/documents/{id}` | 删除文档 |
| POST | `/api/rag/query` | 查询知识库 |
| GET | `/api/rag/index/status` | 获取索引状态 |

### Skill 管理

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/skills` | 列出 Skills |
| GET | `/api/skills/{id}` | 获取 Skill 详情 |
| GET | `/api/skills/{id}/content` | 获取 Skill 内容 |
| POST | `/api/skills/validate` | 验证 Skill 规范 |
| POST | `/api/skills/install` | 安装 Skill |
| DELETE | `/api/skills/{id}` | 卸载 Skill |
| GET | `/api/skills/{id}/export` | 导出 Skill |
| GET | `/api/skills/template` | 获取 Skill 模板 |

### 配置管理

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/config` | 读取当前租户配置 |
| POST | `/api/config` | 更新当前租户配置 |

## 数据流

```
用户消息 → WebSocket → ConversationalAgent.chat()
  → deepagents (langgraph)
    → 判断意图（闲聊 vs 工具调用）
    → 如需工具：ShellTool 执行 Skill 脚本
    → 流式返回 token → StatusCallback → WebSocket → 前端
  → 保存历史（含思考过程）→ ConversationHistoryManager
  → 断开连接时 → UserPreferenceMining 挖掘用户画像
```

## 关键配置项

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `HOST` / `PORT` | 后端服务监听地址 | `0.0.0.0` / `8000` |
| `LLM_MODEL` | LLM 模型名称 | — |
| `LLM_URL` / `LLM_API_KEY` | LLM API 地址和密钥 | — |
| `EMBEDDING_MODEL` / `EMBEDDING_URL` / `EMBEDDING_API_KEY` | Embedding 模型配置 | — |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥 | — |
| `FIRECRAWL_API_KEY` | Firecrawl 爬虫 API 密钥 | — |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | MySQL 数据库配置 | `localhost` / `3306` / `deepagentforce` |
| `JWT_SECRET_KEY` | JWT 密钥 | — |
| `EMBEDDING_DIM` | 向量维度 | `1024` |
| `T_SCORE` | RAG 检索阈值 | `0.3` |
| `MAX_PLAN_STEPS` | 最大计划步骤数 | `10` |
| `CONVERSATION_HISTORY_LIMIT` | 保留的对话历史数量 | `10` |

配置加载优先级：`.env` 环境变量 → `data/saved_config.json`（或租户配置文件） → 默认值

## 项目特色

1. **多租户全链路隔离**：从认证、数据存储到 AI 推理配置，每个租户完全独立
2. **Skill 即插即用**：前端可动态上传/安装/卸载 Skill，Agent 自动发现和使用
3. **用户画像自动挖掘**：基于知识图谱 + 图算法，断开连接时自动分析用户偏好并注入 Agent 上下文
4. **流式 + 思考过程可视化**：WebSocket 实时推送 token 和 Agent 的思考步骤（init/tool_start/tool_end/finish）
5. **灵活的 LLM 配置**：支持任何 OpenAI 兼容接口，每个租户可独立配置

---
*文档更新：2026-04-01*
