import logging
import asyncio
import json
import os
from typing import Any, AsyncIterable, Dict, List, Union

# Gemini NLU imports
import google.generativeai as genai

# 设置 logger
logger = logging.getLogger(__name__)

# 从 Common 导入基础类和类型
try:
    from common.server.task_manager import InMemoryTaskManager
    from common.types import (
        Artifact,
        Task, TaskStatus, TaskState, Message, 
        TextPart, DataPart, FilePart,
        SendTaskRequest, SendTaskResponse,
        SendTaskStreamingRequest, SendTaskStreamingResponse,
        TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
        InternalError, JSONRPCResponse
    )
    logger.info("Successfully imported types and InMemoryTaskManager from common.")
except ImportError as e:
    logger.error(f"Failed to import necessary types from common: {e}")
    raise e

# 定义默认的SearchAPI工具描述，实际运行时会从MCP服务器获取完整定义
DEFAULT_SEARCH_API_TOOLS_DEFINITION = [
    {
        "name": "get_current_time",
        "description": "获取当前系统时间和日期信息。可以指定格式(iso, slash, chinese, timestamp, full)和日期偏移量(days_offset)。",
    },
    {
        "name": "search_google",
        "description": "执行 Google 搜索。需要提供查询字符串(q)，可以指定国家(gl)和语言(hl)。",
    },
    {
        "name": "search_google_flights",
        "description": "搜索 Google 航班信息。需要提供出发地ID(departure_id)、目的地ID(arrival_id)和出发日期(outbound_date)。",
    },
    {
        "name": "search_google_maps",
        "description": "在 Google 地图上搜索地点或服务。需要提供查询字符串(query)，可以提供经纬度坐标(location_ll)。",
    },
    {
        "name": "search_google_hotels",
        "description": "搜索酒店信息。需要提供查询地点(q)、入住日期(check_in_date)和退房日期(check_out_date)。",
    },
    {
        "name": "search_google_maps_reviews",
        "description": "查找地点的评论信息。需要提供place_id或data_id。",
    },
    {
        "name": "search_google_videos",
        "description": "执行 Google 视频搜索。需要提供查询字符串(q)。",
    }
]

class AgentTaskManager(InMemoryTaskManager):
    """
    管理 SearchAPI Agent 任务。
    处理任务路由、执行和状态更新。
    """

    def __init__(self, agent=None):
        """
        初始化 AgentTaskManager
        
        Args:
            agent: SearchAPIAgent实例
        """
        super().__init__()
        
        # 初始化 SearchAPI Agent 
        if agent is None:
            # 如果未提供agent，动态导入并创建
            try:
                from agent import SearchAPIAgent
                self.agent = SearchAPIAgent()
                logger.info("Created new SearchAPIAgent instance")
            except ImportError as e:
                logger.error(f"Failed to import SearchAPIAgent: {e}")
                raise e
        else:
            # 使用提供的agent
            self.agent = agent
            logger.info("Using provided SearchAPIAgent instance")
        
        # 初始化 Gemini 模型
        self.llm = None
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("GOOGLE_API_KEY not found. LLM routing will not work.")
            else:
                genai.configure(api_key=api_key)
                model_name = 'gemini-2.5-pro-preview-03-25'
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"Gemini model '{model_name}' configured successfully.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini model: {e}")
            
        # 工具定义缓存
        self.tool_definitions = DEFAULT_SEARCH_API_TOOLS_DEFINITION
        # 工具定义是否已初始化标志
        self._tool_definitions_initialized = False

        logger.info("AgentTaskManager initialized successfully.")
        
    async def _initialize_tool_definitions(self):
        """异步加载并缓存工具定义"""
        # 避免重复初始化
        if self._tool_definitions_initialized:
            return
            
        try:
            if hasattr(self.agent, 'get_tool_definitions'):
                tool_defs = await self.agent.get_tool_definitions()
                if tool_defs:
                    self.tool_definitions = tool_defs
                    logger.info(f"Successfully loaded {len(tool_defs)} tool definitions from MCP server")
                else:
                    logger.warning("Failed to get tool definitions from MCP server, using defaults")
            self._tool_definitions_initialized = True
        except Exception as e:
            logger.error(f"Error initializing tool definitions: {e}")

    async def _get_tool_call_from_query(self, user_query: str, task_id: str) -> tuple[str | None, dict | None]:
        """
        使用 LLM 将用户查询路由到合适的工具并提取参数
        
        Args:
            user_query: 用户查询文本
            task_id: 任务ID
            
        Returns:
            元组 (工具名称, 参数字典)，若无匹配则返回 (None, None)
        """
        # 确保工具定义已初始化
        await self._initialize_tool_definitions()
        
        if not self.llm:
            logger.error(f"Task {task_id}: LLM not configured, cannot perform routing.")
            return None, None

        if not user_query:
            logger.warning(f"Task {task_id}: User query is empty, cannot route.")
            return None, None

        # 构建 Prompt，使用最新的工具定义
        prompt = f"""
        根据用户查询，从以下可用工具列表中选择最合适的工具并提取参数。请以 JSON 格式返回结果，包含 "tool_name" 和 "parameters" 两个键。
        如果找不到合适的工具，请返回包含 "tool_name": null 的 JSON。

        使用说明：
        1. 对于航班搜索（search_google_flights），必须提供 departure_id（出发地）、arrival_id（目的地）和 outbound_date（出发日期），可选参数包括 flight_type（航班类型："one_way"单程或"round_trip"往返）。
        2. 如果是往返航班（flight_type="round_trip"），则必须提供 return_date（返回日期）。
        3. 当用户查询明确表示"单程"或未明确往返性质时，将 flight_type 设置为 "one_way"。
        4. 若用户提到"往返"或"返程"，将 flight_type 设置为 "round_trip"。
        
        示例查询解析：
        - "查询从北京到上海的机票" → {{"tool_name": "search_google_flights", "parameters": {{"departure_id": "PEK", "arrival_id": "SHA", "outbound_date": "2025-04-20", "flight_type": "one_way"}}}}
        - "查询从北京到上海再返回的机票" → {{"tool_name": "search_google_flights", "parameters": {{"departure_id": "PEK", "arrival_id": "SHA", "outbound_date": "2025-04-20", "return_date": "2025-04-27", "flight_type": "round_trip"}}}}
        - "搜索7月19日从巴厘岛到东京的单程航班" → {{"tool_name": "search_google_flights", "parameters": {{"departure_id": "DPS", "arrival_id": "TYO", "outbound_date": "2025-07-19", "flight_type": "one_way"}}}}

        可用工具列表:
        ```json
        {json.dumps(self.tool_definitions, indent=2, ensure_ascii=False)}
        ```

        用户查询: "{user_query}"

        JSON 响应:
        """

        logger.info(f"Task {task_id}: Sending query to LLM for routing: {user_query}")

        try:
            # 调用 Gemini API
            response = await self.llm.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            
            llm_output_text = response.text.strip()
            logger.info(f"Task {task_id}: LLM response: {llm_output_text}")

            # 解析 JSON 响应
            try:
                # 清理可能的 Markdown 代码块标记
                if llm_output_text.startswith("```json"):
                    llm_output_text = llm_output_text[7:]
                if llm_output_text.endswith("```"):
                    llm_output_text = llm_output_text[:-3]
                llm_output_text = llm_output_text.strip()
                
                tool_call_data = json.loads(llm_output_text)
                tool_name = tool_call_data.get("tool_name")
                parameters = tool_call_data.get("parameters", {})
                
                if tool_name:
                    logger.info(f"Task {task_id}: Routed to tool '{tool_name}' with parameters: {parameters}")
                    return tool_name, parameters
                else:
                    logger.info(f"Task {task_id}: No suitable tool found for query")
                    return None, None
                
            except json.JSONDecodeError as e:
                logger.error(f"Task {task_id}: Failed to parse LLM response as JSON: {e}")
                return None, None
                
        except Exception as e:
            logger.error(f"Task {task_id}: Error in LLM routing: {e}")
            return None, None

    async def _extract_user_query(self, request_params) -> str:
        """
        从请求参数中提取用户查询
        
        Args:
            request_params: 请求参数字典
            
        Returns:
            用户查询文本
        """
        # 直接查询
        query = request_params.get("query")
        if query:
            return query
            
        # 从消息中提取查询
        messages = request_params.get("messages", [])
        if messages and isinstance(messages, list):
            # 获取最后一条用户消息
            user_messages = [m for m in messages if m.get("role") == "user"]
            if user_messages:
                last_user_message = user_messages[-1]
                
                # 尝试从消息的内容部分获取文本
                content = last_user_message.get("content", [])
                if isinstance(content, list):
                    text_parts = [part.get("text") for part in content 
                                 if isinstance(part, dict) and part.get("type") == "text" and "text" in part]
                    if text_parts:
                        return " ".join(text_parts)
                elif isinstance(content, str):
                    return content
        
        # 回退到直接工具调用
        tool_name = request_params.get("tool_name")
        if tool_name:
            tool_parameters = request_params.get("parameters", {})
            if tool_parameters:
                return f"请使用工具 {tool_name} 执行以下操作: {json.dumps(tool_parameters, ensure_ascii=False)}"
                
        # 无法提取查询
        return ""

    async def _normalize_parameters(self, tool_name: str, parameters: Dict) -> Dict:
        """
        规范化工具参数
        
        Args:
            tool_name: 工具名称
            parameters: 原始参数
            
        Returns:
            规范化后的参数
        """
        # 获取工具所需参数
        normalized = parameters.copy()
        
        # 特殊处理
        if tool_name == "search_google_maps" and "query" in parameters:
            # 将 query 参数规范化为 MCP 工具所需的格式
            normalized["query"] = parameters["query"]
            
        # 返回规范化后的参数
        return normalized

    async def _execute_tool(self, tool_name: str, parameters: Dict, session_id: str = None) -> Dict[str, Any]:
        """调用工具并获取结果"""
        normalized_params = await self._normalize_parameters(tool_name, parameters)
        return await self.agent.invoke(tool_name, normalized_params, session_id)

    async def _stream_tool_execution(self, tool_name: str, parameters: Dict, session_id: str = None) -> AsyncIterable[Dict[str, Any]]:
        """流式调用工具并获取结果"""
        normalized_params = await self._normalize_parameters(tool_name, parameters)
        async for result in self.agent.stream(tool_name, normalized_params, session_id):
            yield result

    async def check_tool_exists(self, tool_name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具是否存在
        """
        # 确保工具定义已初始化
        await self._initialize_tool_definitions()
        
        # 查找工具定义
        return any(t["name"] == tool_name for t in self.tool_definitions)

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """
        处理发送任务请求
        
        Args:
            request: 发送任务请求
            
        Returns:
            发送任务响应
        """
        # 验证请求
        validation_error = self._validate_request(request)
        if validation_error:
            return validation_error
            
        # 创建任务
        task_id = request.task_id if request.task_id else self._generate_task_id()
        task = Task(
            id=task_id,
            state=TaskState(
                status=TaskStatus.pending,
                last_updated=self._current_timestamp(),
            ),
            messages=[],
            artifacts=[],
        )
        
        # 获取参数
        params = request.parameters
        
        # 提取用户查询
        user_query = await self._extract_user_query(params)
        
        # 创建用户消息
        if user_query:
            task.messages.append(
                Message(
                    role="user",
                    content=[TextPart(text=user_query)],
                )
            )
        
        # 存储任务
        self._tasks[task_id] = task
        
        # 异步处理任务
        asyncio.create_task(self._process_task(task_id, params, user_query=user_query))
        
        # 返回响应
        return SendTaskResponse(task_id=task_id)
        
    async def _process_task(self, task_id: str, params: Dict, user_query: str = None):
        """
        处理任务
        
        Args:
            task_id: 任务ID
            params: 请求参数
            user_query: 用户查询文本
        """
        try:
            # 更新任务状态为处理中
            await self._update_task_status(task_id, TaskStatus.in_progress)
            
            # 处理结果变量
            result = None
            
            # 情况1: 直接指定工具
            if "tool_name" in params:
                tool_name = params["tool_name"]
                tool_params = params.get("parameters", {})
                
                # 检查工具是否存在
                if await self.check_tool_exists(tool_name):
                    logger.info(f"Task {task_id}: Directly invoking tool '{tool_name}' with parameters: {tool_params}")
                    result = await self._execute_tool(tool_name, tool_params, session_id=task_id)
                else:
                    error_msg = f"工具 '{tool_name}' 不存在"
                    logger.error(f"Task {task_id}: {error_msg}")
                    result = {"error": error_msg}
                    
            # 情况2: 使用LLM路由
            elif user_query:
                logger.info(f"Task {task_id}: Routing query: {user_query}")
                
                # 使用LLM路由到合适的工具
                tool_name, tool_params = await self._get_tool_call_from_query(user_query, task_id)
                
                if tool_name:
                    # 找到合适的工具，调用它
                    logger.info(f"Task {task_id}: Routed to tool '{tool_name}' with parameters: {tool_params}")
                    result = await self._execute_tool(tool_name, tool_params, session_id=task_id)
                else:
                    # 未找到合适的工具，返回错误
                    error_msg = "无法确定适合处理此查询的工具"
                    logger.warning(f"Task {task_id}: {error_msg}")
                    result = {"error": error_msg, "query": user_query}
            
            # 情况3: 无法处理的请求
            else:
                error_msg = "请求中缺少查询或工具规格"
                logger.error(f"Task {task_id}: {error_msg}")
                result = {"error": error_msg}
            
            # 将结果添加到任务消息
            if result:
                # 创建assistant消息
                content_parts = []
                
                if "error" in result:
                    # 错误结果
                    error_text = f"错误: {result['error']}"
                    content_parts.append(TextPart(text=error_text))
                    
                    # 更新任务状态为失败
                    await self._update_task_status(task_id, TaskStatus.failed,
                                                 error_message=result["error"])
                else:
                    # 成功结果
                    try:
                        # 尝试添加JSON结果
                        json_result = json.dumps(result, ensure_ascii=False, indent=2)
                        content_parts.append(TextPart(text=json_result))
                        content_parts.append(DataPart(data=result, mime_type="application/json"))
                        
                        # 更新任务状态为成功
                        await self._update_task_status(task_id, TaskStatus.complete)
                    except Exception as e:
                        # JSON序列化失败
                        logger.error(f"Task {task_id}: Error serializing result: {e}")
                        content_parts.append(TextPart(text=str(result)))
                        
                        # 更新任务状态为成功
                        await self._update_task_status(task_id, TaskStatus.complete)
                
                # 创建并添加消息
                if content_parts:
                    assistant_message = Message(
                        role="assistant",
                        content=content_parts,
                    )
                    await self._add_message_to_task(task_id, assistant_message)
                
        except Exception as e:
            # 出现异常，更新任务状态为失败
            logger.exception(f"Task {task_id}: Error processing task: {e}")
            error_message = f"处理任务时发生错误: {str(e)}"
            await self._update_task_status(task_id, TaskStatus.failed, error_message=error_message)
            
            # 添加错误消息
            error_msg = Message(
                role="assistant",
                content=[TextPart(text=error_message)],
            )
            await self._add_message_to_task(task_id, error_msg)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """
        处理发送任务订阅请求（流式响应）
        
        Args:
            request: 流式任务请求
            
        Returns:
            流式任务响应
        """
        # 验证请求
        validation_error = self._validate_request(request)
        if validation_error:
            return validation_error
            
        # 创建任务
        task_id = request.task_id if request.task_id else self._generate_task_id()
        task = Task(
            id=task_id,
            state=TaskState(
                status=TaskStatus.pending,
                last_updated=self._current_timestamp(),
            ),
            messages=[],
            artifacts=[],
        )
        
        # 获取参数
        params = request.parameters
        
        # 提取用户查询
        user_query = await self._extract_user_query(params)
        
        # 创建用户消息
        if user_query:
            task.messages.append(
                Message(
                    role="user",
                    content=[TextPart(text=user_query)],
                )
            )
        
        # 存储任务
        self._tasks[task_id] = task
        
        # 启动流式处理任务生成器
        return self._run_streaming_agent(request)

    async def _run_streaming_agent(self, request: SendTaskStreamingRequest):
        """
        运行流式代理（生成器）
        
        Args:
            request: 流式任务请求
            
        Yields:
            流式任务响应
        """
        task_id = request.task_id if request.task_id else self._generate_task_id()
        params = request.parameters
        
        # 提取用户查询
        user_query = await self._extract_user_query(params)
        
        try:
            # 首先发送任务状态更新
            yield SendTaskStreamingResponse(
                task_id=task_id,
                event=TaskStatusUpdateEvent(
                    status=TaskStatus.in_progress,
                    timestamp=self._current_timestamp(),
                )
            )
            
            # 处理结果变量
            result_iterator = None
            
            # 情况1: 直接指定工具
            if "tool_name" in params:
                tool_name = params["tool_name"]
                tool_params = params.get("parameters", {})
                
                # 检查工具是否存在
                if await self.check_tool_exists(tool_name):
                    logger.info(f"Task {task_id}: Directly streaming tool '{tool_name}' with parameters: {tool_params}")
                    result_iterator = self._stream_tool_execution(tool_name, tool_params, session_id=task_id)
                else:
                    error_msg = f"工具 '{tool_name}' 不存在"
                    logger.error(f"Task {task_id}: {error_msg}")
                    yield SendTaskStreamingResponse(
                        task_id=task_id,
                        event=TaskStatusUpdateEvent(
                            status=TaskStatus.failed,
                            error_message=error_msg,
                            timestamp=self._current_timestamp(),
                        )
                    )
                    return
                    
            # 情况2: 使用LLM路由
            elif user_query:
                logger.info(f"Task {task_id}: Routing query: {user_query}")
                
                # 使用LLM路由到合适的工具
                tool_name, tool_params = await self._get_tool_call_from_query(user_query, task_id)
                
                if tool_name:
                    # 找到合适的工具，调用它
                    logger.info(f"Task {task_id}: Routed to tool '{tool_name}' with parameters: {tool_params}")
                    result_iterator = self._stream_tool_execution(tool_name, tool_params, session_id=task_id)
                else:
                    # 未找到合适的工具，返回错误
                    error_msg = "无法确定适合处理此查询的工具"
                    logger.warning(f"Task {task_id}: {error_msg}")
                    yield SendTaskStreamingResponse(
                        task_id=task_id,
                        event=TaskStatusUpdateEvent(
                            status=TaskStatus.failed,
                            error_message=error_msg,
                            timestamp=self._current_timestamp(),
                        )
                    )
                    return
            
            # 情况3: 无法处理的请求
            else:
                error_msg = "请求中缺少查询或工具规格"
                logger.error(f"Task {task_id}: {error_msg}")
                yield SendTaskStreamingResponse(
                    task_id=task_id,
                    event=TaskStatusUpdateEvent(
                        status=TaskStatus.failed,
                        error_message=error_msg,
                        timestamp=self._current_timestamp(),
                    )
                )
                return
                
            # 流式处理结果
            if result_iterator:
                assistant_message = Message(
                    role="assistant",
                    content=[],
                )
                
                try:
                    async for result_chunk in result_iterator:
                        if isinstance(result_chunk, dict) and "error" in result_chunk:
                            # 错误结果
                            error_text = f"错误: {result_chunk['error']}"
                            assistant_message.content.append(TextPart(text=error_text))
                            
                            # 发送消息更新
                            yield SendTaskStreamingResponse(
                                task_id=task_id,
                                event=TaskArtifactUpdateEvent(
                                    artifact=Message(
                                        role="assistant",
                                        content=[TextPart(text=error_text)],
                                    ),
                                    timestamp=self._current_timestamp(),
                                )
                            )
                            
                            # 更新任务状态为失败
                            yield SendTaskStreamingResponse(
                                task_id=task_id,
                                event=TaskStatusUpdateEvent(
                                    status=TaskStatus.failed,
                                    error_message=result_chunk["error"],
                                    timestamp=self._current_timestamp(),
                                )
                            )
                            return
                        else:
                            # 成功结果
                            try:
                                # 尝试添加JSON结果
                                json_result = json.dumps(result_chunk, ensure_ascii=False, indent=2)
                                assistant_message.content.append(TextPart(text=json_result))
                                assistant_message.content.append(DataPart(data=result_chunk, mime_type="application/json"))
                                
                                # 发送消息更新
                                yield SendTaskStreamingResponse(
                                    task_id=task_id,
                                    event=TaskArtifactUpdateEvent(
                                        artifact=Message(
                                            role="assistant",
                                            content=[
                                                TextPart(text=json_result),
                                                DataPart(data=result_chunk, mime_type="application/json")
                                            ],
                                        ),
                                        timestamp=self._current_timestamp(),
                                    )
                                )
                            except Exception as e:
                                # JSON序列化失败
                                logger.error(f"Task {task_id}: Error serializing result chunk: {e}")
                                chunk_text = str(result_chunk)
                                assistant_message.content.append(TextPart(text=chunk_text))
                                
                                # 发送消息更新
                                yield SendTaskStreamingResponse(
                                    task_id=task_id,
                                    event=TaskArtifactUpdateEvent(
                                        artifact=Message(
                                            role="assistant",
                                            content=[TextPart(text=chunk_text)],
                                        ),
                                        timestamp=self._current_timestamp(),
                                    )
                                )
                    
                    # 完成流式处理，更新任务状态
                    yield SendTaskStreamingResponse(
                        task_id=task_id,
                        event=TaskStatusUpdateEvent(
                            status=TaskStatus.complete,
                            timestamp=self._current_timestamp(),
                        )
                    )
                    
                except Exception as e:
                    # 流式处理过程中出现异常
                    logger.exception(f"Task {task_id}: Error in streaming process: {e}")
                    error_message = f"流式处理过程中出现错误: {str(e)}"
                    
                    # 发送错误消息
                    yield SendTaskStreamingResponse(
                        task_id=task_id,
                        event=TaskArtifactUpdateEvent(
                            artifact=Message(
                                role="assistant",
                                content=[TextPart(text=error_message)],
                            ),
                            timestamp=self._current_timestamp(),
                        )
                    )
                    
                    # 更新任务状态为失败
                    yield SendTaskStreamingResponse(
                        task_id=task_id,
                        event=TaskStatusUpdateEvent(
                            status=TaskStatus.failed,
                            error_message=error_message,
                            timestamp=self._current_timestamp(),
                        )
                    )
                    
        except Exception as e:
            # 处理过程中出现异常
            logger.exception(f"Task {task_id}: Error setting up streaming task: {e}")
            error_message = f"设置流式任务时出现错误: {str(e)}"
            
            # 更新任务状态为失败
            yield SendTaskStreamingResponse(
                task_id=task_id,
                event=TaskStatusUpdateEvent(
                    status=TaskStatus.failed,
                    error_message=error_message,
                    timestamp=self._current_timestamp(),
                )
            )

    def _validate_request(self, request: SendTaskRequest) -> JSONRPCResponse:
        """验证请求有效性"""
        # 检查是否支持请求的模态
        if not self._are_modalities_compatible(request):
            return JSONRPCResponse(
                error=InternalError(
                    code=-32603,
                    message="Unsupported modality in request.",
                    data={"supported_modalities": ["text/plain", "application/json"]},
                )
            )
        return None

    def _are_modalities_compatible(self, request: SendTaskRequest) -> bool:
        """检查请求的模态是否兼容"""
        # 检查输入模态
        if hasattr(request, "input_modality") and request.input_modality:
            if request.input_modality not in ["text/plain", "application/json"]:
                return False

        # 检查输出模态
        if hasattr(request, "output_modality") and request.output_modality:
            if request.output_modality not in ["text/plain", "application/json"]:
                return False

        return True 