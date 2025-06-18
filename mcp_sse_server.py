from typing import Any
import  httpx

# from mcp.server.fastmcp import FastMCP

from fastmcp import FastMCP

mcp_sse = FastMCP(
    name="mcp-sse-server",
    host="0.0.0.0",
    port=5050
)



@mcp_sse.tool()
async  def name(first_name: str) -> str:
    """获取用户姓名
    Args:
        first_name: 用户的姓
    return:
        用户姓名
    """
    return f"{first_name} 领"

@mcp_sse.tool()
async  def sex(name: str) -> str:
    """获取用户性别

    Args:
        name: 用户姓名

    return:
        用户性别
    """
    return f"{name} 性别: 男"



if __name__ == '__main__': # 指令启动 uv run mcp_sse_server.py
    # mcp.run(transport="streamable-http")  # uv --dir E:\dev\ai\mcp_demo  run mcp_server.py
    print("sse已注册的工具:")
    for tool_info in mcp_sse._tool_manager.list_tools():  # 这个方法是同步的
        print(f"- {tool_info.name}: {tool_info.description}")
    # mcp.run(transport='stdio')
    mcp_sse.run(transport="sse")
    # mcp_streamable.run(transport="streamable-http",host="0.0.0.0",port="5050",path="/mcp")