# DeepAgentForce 项目概览

## 🎯 项目定位

DeepAgentForce 是一个基于 FastAPI 构建的智能体（Agent）平台，支持多租户、RAG（检索增强生成）、技能扩展等核心功能。

## 🏗️ 核心架构

```
DeepAgentForce
├── main.py                 # 应用入口，FastAPI 实例与 DeepAgentForce 主类
├── config/                 # 配置管理
│   └── settings.py         # 配置加载与多租户配置
├── src/
│   ├── api/                # API 路由层
│   │   ├── routes.py       # 基础 API 路由
│   │   ├── skills_routes.py # 技能管理路由
│   │   ├── auth_routes.py  # 认证路由
│   │   └── websocket.py    # WebSocket 通信
│   ├── services/           # 业务服务层
│   │   ├── conversational_agent.py  # 会话代理
│   │   ├── rag.py          # RAG 管道（Milvus 向量数据库）
│   │   ├── skill_manager.py # 技能管理（内置 + 用户自定义）
│   │   └── person_like_service.py   # 用户偏好挖掘
│   └── database/           # 数据访问层
│       └── connection.py   # 数据库连接
├── static/                 # 前端静态资源
├── skills/                 # 技能插件目录
└── learn-docs/             # 学习与开发日志（本目录）
```

## 🔑 核心组件

### 1. DeepAgentForce 主类
位于 [`main.py`](../main.py)，负责：
- 多租户会话管理（`sessions` dict）
- 多租户 RAG 引擎管理（`_rag_engines` dict）
- 技能管理器初始化（内置 Skills + 用户自定义 Skills）
- 用户偏好挖掘服务

### 2. 多租户架构
- **Tenant UUID**: 每个租户有独立的配置、会话、RAG 引擎、技能
- **配置隔离**: `get_tenant_settings(tenant_uuid)` 从租户配置文件加载
- **会话隔离**: `session_key = f"{tenant_uuid}_{session_id}"`

### 3. RAG Pipeline
- 使用 Milvus 作为向量数据库
- 支持多租户独立向量索引
- 按需创建：`get_rag_engine(tenant_uuid)`

### 4. 技能系统
- **内置技能**: `SKILL_DIR` 下的预置技能（如 pdf-processing、rag-query、web-search）
- **用户自定义技能**: `USER_SKILL_DIR` 下运行时添加
- 技能管理器：`SkillManager` 负责加载、注册、执行

## 📊 数据流

```
用户请求 → FastAPI 路由 → DeepAgentForce 
                              ↓
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
  ConversationalAgent    RAG Pipeline      SkillManager
         ↓                    ↓                    ↓
  LLM 对话响应         向量检索/嵌入         技能发现/执行
```

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 通信协议 | WebSocket, HTTP/REST |
| 向量数据库 | Milvus |
| 关系数据库 | MySQL |
| 前端 | HTML/CSS/JS (静态文件) |

## 📋 关键配置项

- `CORS_ORIGINS`: 跨域允许的来源
- `HISTORY_DIR`: 会话历史存储目录
- `SKILL_DIR`: 内置技能目录
- `USER_SKILL_DIR`: 用户自定义技能目录
- `EMBEDDING_URL`: 嵌入模型服务地址

---
*文档创建：2026-03-31*
