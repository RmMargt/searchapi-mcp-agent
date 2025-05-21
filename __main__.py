#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SearchAPI Agent with A2A protocol support
"""

import sys
import os
import logging
from pathlib import Path
import click
from dotenv import load_dotenv

# 设置logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 删除旧的导入路径设置
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../samples/python")))

# 从Common导入A2A服务器和相关类型
try:
    from common.server import A2AServer
    from common.types import (
        AgentCapabilities,
        AgentCard,
        AgentSkill,
        MissingAPIKeyError
    )
    logger.info("Successfully imported types from common")
except ImportError as e:
    logger.error(f"Failed to import necessary types from common: {e}")
    raise e

# 从当前项目导入agent和task_manager
try:
    from agent import SearchAPIAgent
    from task_manager import AgentTaskManager
    logger.info("Successfully imported SearchAPIAgent and AgentTaskManager")
except ImportError as e:
    logger.error(f"Failed to import SearchAPIAgent or AgentTaskManager: {e}")
    raise e


@click.command()
@click.option("--host", default="localhost", help="Host to run the server on")
@click.option("--port", default=8000, type=int, help="Port to run the server on")
def main(host, port):
    """启动 SearchAPI A2A 服务"""
    
    # 检查所需的API密钥
    google_api_key = os.getenv("GOOGLE_API_KEY")
    searchapi_api_key = os.getenv("SEARCHAPI_API_KEY")
    
    if not google_api_key:
        logger.error("缺少GOOGLE_API_KEY环境变量，LLM路由将无法工作")
        raise MissingAPIKeyError("GOOGLE_API_KEY is required for LLM routing")
    
    if not searchapi_api_key:
        logger.error("缺少SEARCHAPI_API_KEY环境变量，SearchAPI工具将无法工作")
        raise MissingAPIKeyError("SEARCHAPI_API_KEY is required for SearchAPI tools")
    
    # 定义Agent技能
    skills = [
        AgentSkill(
            id="get_current_time",
            name="当前时间和日期查询",
            description="获取当前系统时间和日期信息，可以指定格式和日期偏移量",
            tags=["时间", "日期"],
            examples=["现在几点了?", "今天是几号?"],
        ),
        AgentSkill(
            id="search_google",
            name="Google搜索",
            description="执行Google搜索并返回结果",
            tags=["搜索", "Google"],
            examples=["搜索人工智能最新进展"],
        ),
        AgentSkill(
            id="search_google_flights",
            name="Google航班搜索",
            description="搜索航班信息，包括价格、时间和可用性",
            tags=["航班", "旅行"],
            examples=["查找从北京到上海的航班"],
        ),
        AgentSkill(
            id="search_google_maps",
            name="Google地图搜索",
            description="在Google地图上搜索地点或服务",
            tags=["地图", "位置"],
            examples=["查找附近的咖啡店"],
        ),
        AgentSkill(
            id="search_google_hotels",
            name="Google酒店搜索",
            description="搜索酒店信息，包括价格、可用性和评价",
            tags=["酒店", "住宿"],
            examples=["查找东京的酒店"],
        ),
        AgentSkill(
            id="search_google_maps_reviews",
            name="Google地图评论搜索",
            description="查找Google地图上地点的评论信息",
            tags=["评论", "地点"],
            examples=["查看这家餐厅的评价"],
        ),
        AgentSkill(
            id="search_google_videos",
            name="Google视频搜索",
            description="搜索视频内容",
            tags=["视频", "媒体"],
            examples=["搜索烹饪教程视频"],
        ),
    ]
    
    # 定义Agent能力
    capabilities = AgentCapabilities(
        streaming=True,
        pushNotifications=False,
    )
    
    # 创建Agent卡片
    agent_card = AgentCard(
        name="SearchAPI MCP Agent",
        description="通过MCP (Model Context Protocol) 提供Google搜索、地图、航班、酒店、视频等搜索功能的代理",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain", "application/json"],
        capabilities=capabilities,
        skills=skills,
    )
    
    # 创建Agent实例
    agent = SearchAPIAgent()
    logger.info("SearchAPIAgent initialized")
    
    # 创建TaskManager实例，并传入Agent
    task_manager = AgentTaskManager(agent=agent)
    logger.info("AgentTaskManager initialized with SearchAPIAgent")
    
    # 启动A2A服务器
    server = A2AServer(
        agent_card=agent_card,
        task_manager=task_manager,
        host=host,
        port=port,
    )
    
    logger.info(f"Starting SearchAPI MCP A2A server on {host}:{port}")
    
    # 启动服务器
    server.start()


if __name__ == "__main__":
    main() 
