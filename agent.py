import asyncio
import json
import os
import logging
from typing import Dict, Any, Optional, AsyncIterable, List
import sys
from datetime import datetime, timedelta

# MCP Client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as mcp_types

# 设置 Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# MCP Server 脚本路径
MCP_SERVER_SCRIPT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "mcp_server.py"
))
logger.info(f"MCP Server script path: {MCP_SERVER_SCRIPT_PATH}")

class SearchAPIAgent:
    """SearchAPI Agent 通过 MCP 与 SearchAPI 服务通信"""
    
    # 支持的内容类型
    SUPPORTED_CONTENT_TYPES = ["text/plain", "application/json"]
    
    def __init__(self):
        """初始化SearchAPI Agent"""
        # 检查必要的环境变量
        self._check_api_keys()
        # 初始化工具定义缓存
        self._tool_definitions = None
        # 加载工具定义的锁，防止并发获取工具定义
        self._tool_definitions_lock = asyncio.Lock()
        logger.info("SearchAPI Agent initialized")
        
    def _check_api_keys(self):
        """检查必要的API密钥是否存在"""
        searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        if not searchapi_key:
            logger.warning("SEARCHAPI_API_KEY not set. API calls may fail.")
            
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            logger.warning("GOOGLE_API_KEY not set. LLM routing may fail.")
    
    async def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        从MCP服务器获取可用工具及其参数要求的列表
        
        Returns:
            包含工具定义的列表
        """
        # 如果已有缓存的工具定义，直接返回
        if self._tool_definitions is not None:
            return self._tool_definitions
        
        # 使用锁防止多个请求同时尝试获取工具定义
        async with self._tool_definitions_lock:
            # 再次检查缓存（可能在等待锁的过程中已被其他请求填充）
            if self._tool_definitions is not None:
                return self._tool_definitions
            
            logger.info("Fetching tool definitions from MCP server...")
            
            # 检查 mcp_server.py 是否存在
            if not os.path.exists(MCP_SERVER_SCRIPT_PATH):
                error_msg = f"MCP Server script not found at: {MCP_SERVER_SCRIPT_PATH}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # 配置连接参数
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[MCP_SERVER_SCRIPT_PATH],
                env=os.environ.copy()
            )

            try:
                async with stdio_client(server_params) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        logger.info("MCP Session initialized. Listing available tools...")
                        
                        # 初始化会话
                        await session.initialize()
                        
                        # 获取工具列表
                        tools_list_result = await session.list_tools()
                        
                        # 处理结果
                        tool_definitions = []
                        for tool in tools_list_result.tools:
                            tool_def = {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            }
                            # 检查属性是否存在再访问
                            if hasattr(tool, 'annotations') and tool.annotations:
                                tool_def["annotations"] = tool.annotations
                            tool_definitions.append(tool_def)
                        
                        logger.info(f"Found {len(tool_definitions)} tools from MCP server")
                        
                        # 缓存工具定义
                        self._tool_definitions = tool_definitions
                        return tool_definitions
                        
            except Exception as e:
                error_msg = f"Error fetching tool definitions from MCP server: {str(e)}"
                logger.exception(error_msg)
                # 发生错误时，返回一个默认的工具定义
                self._tool_definitions = [
                    {
                        "name": "get_current_time",
                        "description": "获取当前系统时间和日期信息。可以指定格式(iso, slash, chinese, timestamp, full)和日期偏移量(days_offset)。",
                        "inputSchema": {"type": "object", "properties": {}, "required": []}
                    },
                    {
                        "name": "search_google",
                        "description": "执行 Google 搜索。需要提供查询字符串(q)，可以指定国家(gl)和语言(hl)。",
                        "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}
                    },
                    {
                        "name": "search_google_flights",
                        "description": "搜索 Google 航班信息。需要提供出发地ID(departure_id)、目的地ID(arrival_id)和出发日期(outbound_date)。",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "departure_id": {"type": "string"},
                                "arrival_id": {"type": "string"},
                                "outbound_date": {"type": "string"},
                                "flight_type": {"type": "string", "enum": ["round_trip", "one_way"]},
                                "return_date": {"type": "string"}
                            }, 
                            "required": ["departure_id", "arrival_id", "outbound_date"]
                        }
                    },
                    {
                        "name": "search_google_maps",
                        "description": "在 Google 地图上搜索地点或服务。需要提供查询字符串(query)，可以提供经纬度坐标(location_ll)。",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "query": {"type": "string"},
                                "location_ll": {"type": "string"}
                            }, 
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "search_google_hotels",
                        "description": "搜索酒店信息。需要提供查询地点(q)、入住日期(check_in_date)和退房日期(check_out_date)。日期格式为YYYY-MM-DD。",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "q": {"type": "string", "description": "搜索查询，如目的地、酒店名称等"},
                                "check_in_date": {"type": "string", "description": "入住日期，格式为YYYY-MM-DD"},
                                "check_out_date": {"type": "string", "description": "退房日期，格式为YYYY-MM-DD"},
                                "adults": {"type": "string", "description": "成人数量"},
                                "children_ages": {"type": "string", "description": "儿童年龄，以逗号分隔"},
                                "price_min": {"type": "string", "description": "最低价格"},
                                "price_max": {"type": "string", "description": "最高价格"}
                            }, 
                            "required": ["q", "check_in_date", "check_out_date"]
                        }
                    },
                    {
                        "name": "search_google_maps_reviews",
                        "description": "查找地点的评论信息。需要提供place_id或data_id。",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "place_id": {"type": "string"},
                                "data_id": {"type": "string"}
                            }
                        }
                    },
                    {
                        "name": "search_google_videos",
                        "description": "执行 Google 视频搜索。需要提供查询字符串(q)。",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {
                                "q": {"type": "string"}
                            }, 
                            "required": ["q"]
                        }
                    }
                ]
                logger.warning("Using default tool definition due to error")
                return self._tool_definitions
    
    async def get_tool_required_parameters(self, tool_name: str) -> List[str]:
        """
        获取指定工具的必填参数列表
        
        Args:
            tool_name: 工具名称
            
        Returns:
            必填参数名称列表
        """
        tool_definitions = await self.get_tool_definitions()
        
        # 找到指定的工具
        tool_def = next((t for t in tool_definitions if t["name"] == tool_name), None)
        if not tool_def:
            logger.warning(f"Tool '{tool_name}' not found in definitions")
            return []
        
        # 提取必填参数
        input_schema = tool_def.get("inputSchema", {})
        required_params = input_schema.get("required", [])
        
        logger.info(f"Tool '{tool_name}' requires parameters: {required_params}")
        return required_params
    
    async def validate_tool_parameters(self, tool_name: str, parameters: Dict) -> Dict:
        """
        验证工具参数并添加缺少的必填参数的默认值
        
        Args:
            tool_name: 工具名称
            parameters: 要验证的参数字典
            
        Returns:
            补充默认值后的参数字典
        """
        # 获取工具定义
        tool_definitions = await self.get_tool_definitions()
        tool_def = next((t for t in tool_definitions if t["name"] == tool_name), None)
        
        if not tool_def:
            logger.warning(f"Tool '{tool_name}' not found in definitions, skipping validation")
            return parameters
        
        # 获取工具的输入模式
        input_schema = tool_def.get("inputSchema", {})
        required_params = input_schema.get("required", [])
        properties = input_schema.get("properties", {})
        
        # 补充的参数
        validated_params = parameters.copy()
        
        # 检查是否缺少必填参数
        missing_params = [p for p in required_params if p not in parameters]
        if missing_params:
            logger.warning(f"Missing required parameters for '{tool_name}': {missing_params}")
            
        # 返回验证后的参数
        return validated_params
    
    async def invoke(self, tool_name: str, parameters: Dict, session_id: str = None) -> Dict[str, Any]:
        """
        异步调用指定的工具并返回结果
        
        Args:
            tool_name: 要调用的工具名称
            parameters: 工具参数
            session_id: 可选的会话ID，用于跟踪相关请求
            
        Returns:
            工具调用结果字典
        """
        # 验证参数
        validated_params = await self.validate_tool_parameters(tool_name, parameters)
        
        try:
            logger.info(f"Invoking tool '{tool_name}' with parameters: {validated_params}")
            
            # 调用MCP工具
            mcp_result = await self._call_mcp_tool(tool_name, validated_params)
            
            # 处理结果
            result = self._process_mcp_result(mcp_result)
            logger.info(f"Successfully invoked tool '{tool_name}'")
            
            return result
            
        except Exception as e:
            error_message = f"Error invoking tool '{tool_name}': {str(e)}"
            logger.exception(error_message)
            return {"error": error_message}
    
    async def stream(self, tool_name: str, parameters: Dict, session_id: str = None) -> AsyncIterable[Dict[str, Any]]:
        """
        流式调用指定的工具并逐步返回结果
        
        Args:
            tool_name: 要调用的工具名称
            parameters: 工具参数
            session_id: 可选的会话ID，用于跟踪相关请求
            
        Yields:
            工具调用的部分结果
        """
        # 由于MCP目前不支持流式响应，我们先执行完整调用，然后模拟流式返回
        try:
            logger.info(f"Stream invocation of tool '{tool_name}' with parameters: {parameters}")
            
            # 验证参数
            validated_params = await self.validate_tool_parameters(tool_name, parameters)
            
            # 调用MCP工具并获取完整结果
            mcp_result = await self._call_mcp_tool(tool_name, validated_params)
            result = self._process_mcp_result(mcp_result)
            
            # 这里简单地一次性返回完整结果
            yield result
            
        except Exception as e:
            error_message = f"Error streaming tool '{tool_name}': {str(e)}"
            logger.exception(error_message)
            yield {"error": error_message}
    
    async def _call_mcp_tool(self, tool_name: str, parameters: Dict) -> Any:
        """
        通过MCP调用指定的工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            MCP工具调用结果
        """
        # 检查 mcp_server.py 是否存在
        if not os.path.exists(MCP_SERVER_SCRIPT_PATH):
            error_msg = f"MCP Server script not found at: {MCP_SERVER_SCRIPT_PATH}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # 配置连接参数
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER_SCRIPT_PATH],
            env=os.environ.copy()
        )
        
        logger.info(f"Calling MCP tool '{tool_name}' with parameters: {parameters}")
        
        try:
            # 连接到MCP服务器并调用工具
            async with stdio_client(server_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    logger.info("MCP Session initialized")
                    
                    # 初始化会话
                    await session.initialize()
                    
                    # 准备参数（确保是字符串化值）
                    string_params = {}
                    for k, v in parameters.items():
                        if v is not None:
                            string_params[k] = str(v) if not isinstance(v, str) else v
                    
                    # 调用工具
                    logger.info(f"Calling MCP tool with stringified parameters: {string_params}")
                    result = await session.call_tool(tool_name, string_params)
                    
                    # 完成会话并返回结果
                    return result
                    
        except Exception as e:
            error_msg = f"Error calling MCP tool '{tool_name}': {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg)
    
    def _process_mcp_result(self, mcp_result: mcp_types.CallToolResult) -> Any:
        """
        处理MCP工具调用结果
        
        Args:
            mcp_result: MCP工具调用结果
            
        Returns:
            处理后的结果
        """
        logger.info(f"Processing MCP result of type: {type(mcp_result)}")
        
        # 获取结果的媒体类型和内容
        media_type = mcp_result.mediaType
        content = mcp_result.content
        
        # 根据媒体类型处理内容
        if media_type == "application/json":
            try:
                # 解析JSON内容
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                if isinstance(content, str):
                    parsed_content = json.loads(content)
                else:
                    parsed_content = content
                
                return parsed_content
            except Exception as e:
                logger.exception(f"Error parsing JSON content: {e}")
                return {"error": "Failed to parse JSON content", "raw_content": str(content)}
        
        elif media_type.startswith("text/"):
            # 处理文本内容
            if isinstance(content, bytes):
                try:
                    return {"text": content.decode('utf-8')}
                except Exception as e:
                    logger.exception(f"Error decoding text content: {e}")
                    return {"error": "Failed to decode text content"}
            return {"text": str(content)}
        
        else:
            # 处理其他类型的内容
            if isinstance(content, bytes):
                return {"binary_content": "<binary data>", "media_type": media_type}
            return {"content": str(content), "media_type": media_type} 