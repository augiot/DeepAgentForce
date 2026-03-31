# 学习笔记

## 主题：FastAPI 静态文件服务

**日期**: 2026-03-31

### 学到的内容

在 [`main.py`](../main.py) 中，项目使用 FastAPI 的 `StaticFiles` 来提供前端静态资源：

```python
from fastapi.staticfiles import StaticFiles

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
```

### 关键点

1. `app.mount()` 用于挂载一个完整的路由应用
2. `StaticFiles` 自动处理文件查找、MIME 类型、缓存头等
3. 路径映射：`/static/index.html` → `static/index.html`

### 相关代码位置

- 静态文件挂载：[`main.py:37`](../main.py#L37)
- 页面路由（返回 HTML）：[`main.py:40-62`](../main.py#L40-L62)

---

## 主题：多租户会话管理

**日期**: 2026-03-31

### 学到的内容

DeepAgentForce 使用复合键来实现多租户会话隔离：

```python
# 会话 key 生成
session_key = f"{tenant_uuid}_{session_id}" if tenant_uuid else session_id

# 会话存储
self.sessions: dict[str, ConversationalAgent] = {}
```

### 设计要点

1. **命名空间隔离**: 使用 `tenant_uuid` 前缀避免会话冲突
2. **按需创建**: `get_or_create_session()` 懒加载会话对象
3. **回调更新**: 支持动态更新 `status_callback`

### 相关代码位置

- [`main.py:92-111`](../main.py#L92-L111)

---
*新学习笔记请追加到此处*
