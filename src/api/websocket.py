"""
WebSocket 处理模块
支持实时流式对话 + 会话级别的对话历史管理
新增：完整保存思考过程（thinking_steps）
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
from fastapi import WebSocket, WebSocketDisconnect, FastAPI
from fastapi.websockets import WebSocketState
from src.workflow.callbacks import StatusCallback, EventType

logger = logging.getLogger(__name__)

# 线程池用于处理耗时的偏好挖掘任务，避免阻塞事件循环
mining_executor = ThreadPoolExecutor(max_workers=1)

def safe_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "dict"): # 处理 Pydantic
        return obj.dict()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj) # 其他一切转字符串，保命要紧

def setup_websocket_routes(app: FastAPI):
    engine = app.state.engine

    @app.websocket("/ws/stream")
    async def websocket_stream_simple(websocket: WebSocket):
        await websocket.accept()
        session_id = None
        
        # 🆕 用于收集当前对话的思考过程
        current_thinking_steps = []
        
        try:
            # 1. 定义极其强壮的回调函数
            status_callback = StatusCallback()
            
            async def ws_callback(event_type: str, data: dict):
                # 🆕 收集思考过程
                if event_type == "step":
                    # 将每个 step 事件保存到当前对话的思考过程列表
                    current_thinking_steps.append({
                        "timestamp": datetime.now().isoformat(),
                        "event_type": event_type,
                        "data": data
                    })
                
                # 关键检查：如果连接已关闭，不要尝试发送
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.warning(f"WS已断开，跳过发送: {event_type}")
                    return

                try:
                    # 构造消息
                    payload = {
                        "type": event_type, 
                        "data": data, 
                        "ts": datetime.now().isoformat()
                    }
                    
                    # 使用自定义序列化，防止报错
                    json_str = json.dumps(payload, default=safe_json_serializer)
                    
                    # 发送文本而不是 send_json，控制权更强
                    await websocket.send_text(json_str)
                    
                except Exception as e:
                    # 捕获序列化错误，不要让它断开连接
                    logger.error(f"WS 发送失败 (序列化或网络问题): {str(e)}")

            status_callback.add_callback(ws_callback)
            
            # 2. 获取 Session
            req_sid = websocket.query_params.get("session_id")
            session_id, agent = engine.get_or_create_session(
                session_id=req_sid, 
                status_callback=status_callback
            )
            
            # 3. 发送历史记录
            history = engine.history_manager.get_session_history(session_id)
            if history:
                # 包装一下历史记录发送，防止这里也崩
                await ws_callback("history", history)

            # 4. 循环接收消息
            while True:
                data = await websocket.receive_json()
                message = data.get("message", "")
                if not message: continue
                
                # 🆕 从请求体获取 session_id（前端在 JSON 中发送）
                incoming_sid = data.get("session_id")
                if incoming_sid and incoming_sid != session_id:
                    # 前端指定了 session_id，切换会话
                    session_id = incoming_sid
                    session_id, agent = engine.get_or_create_session(
                        session_id=session_id,
                        status_callback=status_callback
                    )
                
                # 🆕 重置思考过程列表（每次新对话开始时清空）
                current_thinking_steps = []
                
                # 双重保险：确保 agent 里的 callback 是最新的
                agent.status_callback = status_callback
                
                # 执行对话
                # 注意："666" 这种闲聊不会触发 tool_start，所以没有思考框是正常的
                # 要测试思考框，请问 "查询一下目前DeepSeek的消息"
                response = await agent.chat(message, thread_id=session_id)
                
                # 🆕 保存历史（包含思考过程）
                engine.history_manager.add_conversation(
                    session_id=session_id, 
                    user_message=message, 
                    ai_response=response,
                    thinking_steps=current_thinking_steps,  # 传递思考过程
                    metadata={"source": "websocket"}
                )
                
                # 🆕 发送结束信号（包含 session_id）
                await ws_callback("done", {"message": response, "session_id": session_id})
        
        except WebSocketDisconnect:
            logger.info(f"客户端断开连接: {session_id}")
            if session_id:
                asyncio.get_running_loop().run_in_executor(
                    mining_executor, engine.user_preference.person_like_save
                )
        except Exception as e:
            logger.error(f"WS 主循环异常: {e}", exc_info=True)
            # 尝试发送错误给前端
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except:
                    pass

class ConversationHistoryManager:
    """会话级别的对话历史管理器"""
    
    def __init__(self, history_dir: Path):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_session_file_path(self, session_id: str) -> Path:
        return self.history_dir / f"session_{session_id}.json"
    
    def create_session(self, session_id: str) -> str:
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            return session_id

        session_data = {
            "session_id": session_id,
            "title": "新对话",  # 初始标题，后续会更新
            "created_at": datetime.now().isoformat(),
            "conversations": []
        }
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return session_id

    def _generate_title(self, user_message: str) -> str:
        """根据用户消息生成标题摘要"""
        if not user_message:
            return "新对话"
        # 移除换行符，取前30个字符
        clean_msg = user_message.replace('\n', ' ').strip()
        if len(clean_msg) > 30:
            return clean_msg[:30] + '...'
        return clean_msg
    
    def add_conversation(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        thinking_steps: Optional[list] = None,  # 🆕 新增参数
        metadata: Optional[dict] = None
    ):
        """
        添加对话记录，包含思考过程

        Args:
            session_id: 会话ID
            user_message: 用户消息
            ai_response: AI回复
            thinking_steps: 思考过程列表（包含所有 step 事件）
            metadata: 元数据
        """
        session_file = self._get_session_file_path(session_id)
        if not session_file.exists():
            self.create_session(session_id)

        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        conversation = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "user_content": user_message,
            "ai_content": ai_response
        }

        # 🆕 添加思考过程
        if thinking_steps:
            conversation["thinking_steps"] = thinking_steps

        if metadata:
            conversation["metadata"] = metadata

        session_data["conversations"].append(conversation)
        session_data["updated_at"] = datetime.now().isoformat()

        # 🆕 如果是第一条用户消息，更新会话标题
        if len(session_data["conversations"]) == 1:
            session_data["title"] = self._generate_title(user_message)

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    def get_session_history(self, session_id: str) -> Optional[dict]:
        session_file = self._get_session_file_path(session_id)
        if not session_file.exists():
            return None
        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_sessions(self) -> list:
        sessions = []
        for session_file in self.history_dir.glob("session_*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "title": data.get("title", "历史对话"),  # 🆕 返回标题
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "conversation_count": len(data.get("conversations", [])),
                        "conversation": data.get("conversations", [])
                    })
            except Exception as e:
                logger.error(f"Failed to read session {session_file}: {e}")
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话

        Args:
            session_id: 要删除的会话ID

        Returns:
            True 表示删除成功，False 表示会话不存在或删除失败
        """
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            try:
                session_file.unlink()
                logger.info(f"已删除会话: {session_id}")
                return True
            except Exception as e:
                logger.error(f"删除会话失败 {session_id}: {e}")
                return False
        return False