import mcp
from fastmcp import FastMCP

mcp_stdio = FastMCP(name="mcp-stdio-server")

@mcp_stdio.tool()
async  def name(first_name: str) -> str:
    """获取用户姓名
    Args:
        first_name: 用户的姓
    return:
        用户姓名
    """
    return f"{first_name} 领"

@mcp_stdio.tool()
async  def sex(name: str) -> str:
    """获取用户性别

    Args:
        name: 用户姓名

    return:
        用户性别
    """
    return f"{name} 性别: 男"

if __name__ == '__main__': # 指令启动 uv run mcp_sse_server.py
    # mcp.run(transport="streamable-http")  # uv --directory E:\dev\ai\mcp_demo  run mcp_stdio_server.py
    print("stdio已注册的工具:")
    for tool_info in mcp_stdio._tool_manager.list_tools():  # 这个方法是同步的
        print(f"- {tool_info.name}: {tool_info.description}")
    mcp_stdio.run(transport="stdio")