# SearchAPI MCP Agent with A2A 支持 | SearchAPI MCP Agent with A2A Support

一个基于 Agent-to-Agent (A2A) 协议的 SearchAPI 代理，通过 Model Context Protocol (MCP) 系统集成了多种搜索 API 工具。

An Agent-to-Agent (A2A) protocol based SearchAPI agent that integrates various search API tools through the Model Context Protocol (MCP) system.

## 更新说明 | Update Notes

**2024 更新**: 
- 修复了导入路径问题：从 samples.python.agents 导入修改为直接从当前目录导入
- 修复了 a2a_common 导入问题：修改为从 common 模块导入
- 移除了 a2a_common 依赖安装需求

**2024 Updates**:
- Fixed import path issues: Changed from samples.python.agents imports to direct imports from the current directory
- Fixed a2a_common import issues: Changed to import from the common module
- Removed a2a_common dependency installation requirements

## 概述 | Overview

SearchAPI-MCP-Agent 实现了 A2A 协议和 Model Context Protocol，将各种搜索操作封装为工具和资源。它作为 AI 助手和搜索服务之间的桥梁，支持地图搜索、航班查询、酒店预订等多种功能。

SearchAPI-MCP-Agent implements the A2A protocol and Model Context Protocol, encapsulating various search operations as tools and resources. It serves as a bridge between AI assistants and search services, supporting map search, flight queries, hotel bookings, and more.

## SearchAPI Agent 核心特性 | Core Features

- **多MCP配置支持** - 作为MCP客户端，可以同时连接和配置多个MCP服务器，扩展可用的工具集
  **Multiple MCP Configuration** - As an MCP client, can connect to and configure multiple MCP servers simultaneously, expanding the available toolset
- **动态工具发现** - 自动发现和加载MCP服务器提供的工具列表，无需手动配置
  **Dynamic Tool Discovery** - Automatically discovers and loads tool lists provided by MCP servers without manual configuration
- **智能LLM路由** - 使用Gemini模型自动将自然语言查询路由到合适的工具并提取参数，确保调用成功
  **Intelligent LLM Routing** - Uses Gemini model to automatically route natural language queries to appropriate tools and extract parameters, ensuring successful invocation
- **实时状态反馈** - 通过A2A协议向Host Agent提供实时的工具执行状态更新和流式响应
  **Real-time Status Feedback** - Provides real-time tool execution status updates and streaming responses to the Host Agent via A2A protocol
- **错误处理和恢复** - 自动处理API调用错误，提供友好的错误信息和回退机制
  **Error Handling and Recovery** - Automatically handles API call errors, providing friendly error messages and fallback mechanisms

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
* UV 包管理器（推荐）| UV package manager (recommended)

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

### 启动 Google A2A 项目的 Host Agent 和 SearchAPI Agent

按照以下步骤启动完整的 A2A 环境，包括 Host Agent 和 SearchAPI Agent:

#### 1. 启动 SearchAPI Agent
```bash
# 在searchapi-mcp-agent目录下
python -m searchapi_mcp_agent --host localhost --port 10001
```

#### 2. 启动 Host Agent (基于 Google A2A 项目)
```bash
# 切换到 Google A2A 样例目录
cd path/to/A2A/samples/python

# 运行 Host Agent (选择一种)
uv run hosts/cli        # 命令行界面
# 或
uv run hosts/multiagent # 多代理环境
```

#### 3. 在本地浏览器中访问 Demo UI
如果你运行的是多代理环境，可以在浏览器中访问以下地址:
```
http://localhost:12000
```

在 UI 中，点击机器人图标添加 SearchAPI Agent，使用以下地址:
```
http://localhost:10001/agent-card
```

### 直接发送请求 | Send Requests
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

### A2A 协议特性实现 | A2A Protocol Implementation

- **动态工具路由** - 通过自然语言处理自动识别用户意图并选择合适的搜索工具
  **Dynamic Tool Routing** - Automatically identifies user intent through natural language processing and selects the appropriate search tool
- **流式响应** - 支持大型搜索结果的分块流式传输，提供实时反馈
  **Streaming Responses** - Supports chunked streaming of large search results, providing real-time feedback
- **任务状态更新** - 实时报告搜索任务的进度和状态变化
  **Task Status Updates** - Reports progress and status changes of search tasks in real-time
- **错误处理** - 优雅处理搜索API错误，提供有用的错误消息
  **Error Handling** - Gracefully handles search API errors, providing useful error messages

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
* Google A2A - Agent-to-Agent 协议参考实现 | A2A protocol reference implementation

---

_注意：本服务器会与外部 API 进行交互。在使用 MCP 客户端确认操作之前，请始终验证请求的操作是否合适。_
_Note: This server interacts with external APIs. Always verify that requested operations are appropriate before confirming them in MCP clients._ 
