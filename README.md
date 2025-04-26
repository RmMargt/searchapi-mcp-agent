# SearchAPI MCP Agent with A2A 支持 | SearchAPI MCP Agent with A2A Support

一个基于 Agent-to-Agent (A2A) 协议的 SearchAPI 代理，通过 Model Context Protocol (MCP) 系统集成了多种搜索 API 工具。

An Agent-to-Agent (A2A) protocol based SearchAPI agent that integrates various search API tools through the Model Context Protocol (MCP) system.

## 概述 | Overview

SearchAPI-MCP-Agent 实现了 A2A 协议和 Model Context Protocol，将各种搜索操作封装为工具和资源。它作为 AI 助手和搜索服务之间的桥梁，支持地图搜索、航班查询、酒店预订等多种功能。

SearchAPI-MCP-Agent implements the A2A protocol and Model Context Protocol, encapsulating various search operations as tools and resources. It serves as a bridge between AI assistants and search services, supporting map search, flight queries, hotel bookings, and more.

## 功能特性 | Features

### Google 搜索 | Google Search
* 网页搜索结果 | Web search results
* 知识图谱集成 | Knowledge graph integration
* 相关问题推荐 | Related questions
* 搜索建议 | Search suggestions
* 多语言支持 | Multi-language support
* 地区特定结果 | Region-specific results
* 时间范围过滤 | Time range filtering
* 安全搜索选项 | Safe search options

### Google Video 搜索 | Google Video Search
* 视频内容搜索 | Video content search
* 视频列表获取 | Video list retrieval
* 视频轮播支持 | Video carousel support
* 短视频内容 | Short video content
* 按时长筛选 | Duration filtering
* 按来源过滤 | Source filtering
* 按上传时间排序 | Upload time sorting
* 高清预览支持 | HD preview support

### Google Maps 搜索 | Google Maps Search
* 搜索地点和服务 | Search places and services
* 获取地点详细信息 | Get place details
* 查看用户评论 | View user reviews
* 获取位置坐标 | Get location coordinates

### Google Flights 航班搜索 | Google Flights Search
* 单程/往返航班搜索 | One-way/round-trip flight search
* 多城市行程规划 | Multi-city itinerary planning
* 航班价格日历 | Flight price calendar
* 航班筛选和排序 | Flight filtering and sorting
* 行李额度查询 | Baggage allowance query
* 航空公司选择 | Airline selection

### Google Hotels 酒店搜索 | Google Hotels Search
* 酒店位置搜索 | Hotel location search
* 价格和可用性查询 | Price and availability query
* 设施和服务筛选 | Facilities and services filtering
* 用户评分和评论 | User ratings and reviews
* 特殊优惠查询 | Special offers query
* 房型选择 | Room type selection

## 安装说明 | Installation

### 环境要求 | Requirements
* Python 3.9 或更高版本 | Python 3.9 or higher
* pip 包管理器 | pip package manager

### 基础安装 | Basic Installation

```bash
# 克隆仓库 | Clone repository
git clone https://github.com/RmMargt/searchapi-mcp-agent.git
cd searchapi-mcp-agent

# 创建并激活虚拟环境 | Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 | or
.\venv\Scripts\activate  # Windows

# 安装依赖 | Install dependencies
pip install -r requirements.txt
```

### 配置环境变量 | Configure Environment Variables

创建 `.env` 文件并设置以下环境变量：
Create a `.env` file and set the following environment variables:

```
SEARCHAPI_API_KEY=your_searchapi_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## 使用方法 | Usage

### 启动服务器 | Start the Server
```bash
python -m searchapi-mcp-agent --host localhost --port 10001
```

### 发送请求 | Send Requests
可以通过以下方式发送请求：
You can send requests in the following ways:

1. **自然语言查询 | Natural Language Query**：
   ```json
   {
     "query": "查找从纽约到洛杉矶的航班"
   }
   ```
   Agent会使用LLM自动将查询路由到合适的工具。
   The agent will use LLM to automatically route the query to the appropriate tool.

2. **直接指定工具 | Direct Tool Specification**：
   ```json
   {
     "tool_name": "search_google_flights",
     "parameters": {
       "departure_id": "NYC",
       "arrival_id": "LAX",
       "outbound_date": "2024-12-01"
     }
   }
   ```

## A2A 集成 | A2A Integration

本项目已完全实现 A2A 协议，可以作为 AI 助手的服务端点。API 符合 A2A 规范，支持任务创建、状态查询和流式响应。

This project fully implements the A2A protocol and can serve as a service endpoint for AI assistants. The API complies with the A2A specification, supporting task creation, status queries, and streaming responses.

## MCP 配置 | MCP Configuration

### Claude for Desktop 配置示例 | Claude for Desktop Configuration Example

在 Claude for Desktop 的配置文件中添加以下内容：
Add the following to your Claude for Desktop configuration file:

```json
{
  "mcpServers": {
    "searchapi": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "/path/to/searchapi-mcp-agent/mcp_server.py"
      ],
      "env": {
        "SEARCHAPI_API_KEY": "your_api_key_here",
        "GOOGLE_API_KEY": "your_google_api_key_here"
      }
    }
  }
}
```

配置文件位置 | Configuration file location:
* macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
* Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## 许可证 | License

本项目采用 MIT 许可证 - 详见 LICENSE 文件
This project is licensed under the MIT License - see the LICENSE file for details

## 致谢 | Acknowledgments

* Model Context Protocol - 协议规范 | Protocol specification
* A2A Protocol - Agent-to-Agent 协议规范 | Agent-to-Agent protocol specification 
* FastMCP - Python MCP 实现 | Python MCP implementation
* SearchAPI.io - 搜索服务提供商 | Search service provider

---

_注意：本服务器会与外部 API 进行交互。在使用 MCP 客户端确认操作之前，请始终验证请求的操作是否合适。_
_Note: This server interacts with external APIs. Always verify that requested operations are appropriate before confirming them in MCP clients._ 