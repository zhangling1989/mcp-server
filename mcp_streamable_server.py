from typing import Any
import  httpx

# from mcp.server.fastmcp import FastMCP

from fastmcp import FastMCP

mcp_streamable = FastMCP(
    name="mcp-streamable-server"
)


@mcp_streamable.tool()
async  def name(first_name: str) -> str:
    """Get user name
    Args:
        first name：
    return:
        user name
    """
    return f"{first_name} ling"

@mcp_streamable.tool()
async  def sex(name: str) -> str:
    """get user sex

    Args:
        name: user name

    return:
        user sex
    """
    return f"{name} sex：male"


if __name__ == '__main__': # 指令启动 uv run mcp_streamable_server.py
    # mcp.run(transport="streamable-http")  # uv --dir E:\dev\ai\mcp_demo  run mcp_server.py
    print("streamable已注册的工具:")
    for tool_info in mcp_streamable._tool_manager.list_tools():  # 这个方法是同步的
        print(f"- {tool_info.name}: {tool_info.description}")
    # mcp.run(transport='stdio')
    # mcp_sse.run(transport="sse")
    mcp_streamable.run(transport="streamable-http",host="0.0.0.0",port="5051",path="/streamable")