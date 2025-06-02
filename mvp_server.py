from typing import Any
import  httpx

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="mcp-server",
    host="0.0.0.0",
    port=5050,
    stateless_http=False,
    json_response=False,
    streamable_http_path="/mcp"
)



@mcp.tool()
async  def see() -> str:
    """获取用户的姓名
    返回：
        用户姓名
    """
    return "张领"

@mcp.tool()
async  def stdio(name: str) -> str:
    """获取用户的性别

    参数:
        name: 用户的姓名

    返回：
        用户性别
    """
    return f"{name}：男"


if __name__ == '__main__':
    # mcp.run(transport="streamable-http")  # uv --dir E:\dev\ai\mcp_demo  run mcp_server.py
    print("已注册的工具:")
    for tool_info in mcp._tool_manager.list_tools():  # 这个方法是同步的
        print(f"- {tool_info.name}: {tool_info.description}")
    # mcp.run(transport='stdio')
    mcp.run(transport="streamable-http")