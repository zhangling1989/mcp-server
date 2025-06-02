from typing import Any
import  httpx

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="mcp-server",
    port=5050,
    stateless_http=False,
    json_response=True,
    streamable_http_path="/mcp"
)



@mcp.tool()
async  def see() -> str:
    """获取用户名

    """
    return "张领"

@mcp.tool()
async  def stdio(name: str) -> str:
    """获取用户的性别

    Args:
        name: 用户的姓名
    """
    return "男"


if __name__ == '__main__':
    mcp.run(transport="streamable-http")  # uv --dir E:\dev\ai\mcp_demo  run mcp_server.py