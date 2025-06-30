from typing import Any
import  httpx

# from mcp.server.fastmcp import FastMCP

from fastmcp import FastMCP

mcp_streamable = FastMCP(
    name="mcp-streamable-server"
)


@mcp_streamable.tool()
async  def contractsByProjectName(project_name: str) -> str:
    """获取合同列表
    Args:
        project_name: 项目名称
    return:
        合同列表的文本数据
    """

    sql = f'''
    SELECT contract_code, contract_name,
    CASE
    WHEN contract_type = 1 THEN 'MC-总包'
    WHEN contract_type = 2 THEN 'NSC-专业分包'
    WHEN contract_type = 3 THEN 'DS-独立供应'
    WHEN contract_type = 4 THEN 'DC-独立承包'
    WHEN contract_type = 5 THEN '顾问'
    WHEN contract_type = 7 THEN '其他类型'
    WHEN contract_type = 8 THEN '无合同'
    ELSE contract_type
    END AS contract_type,
    amount, tax_amount, approval_status, approval_date
    FROM cost_contract
    WHERE project_name = {project_name} AND del_flag = 0
    ORDER BY created_date DESC
    LIMIT 10;
    '''

    return f"{sql}"

@mcp_streamable.tool()
async  def contractsByProjectNameAndcontractType(project_name: str,contract_type: str) -> str:
    """获取合同列表
    Args:
        project_name: 项目名称
        contract_type: 合同类型
    return:
        合同列表的文本数据
    """

    sql = f'''
    SELECT contract_code, contract_name, contract_type, amount 
    FROM cost_contract 
    WHERE project_name = {project_name} 
      AND contract_type = {contract_type} 
      AND del_flag = 0 
    ORDER BY created_date DESC 
    LIMIT 10;
    '''

    return f"{sql}"


if __name__ == '__main__': # 指令启动 uv run mcp_streamable_server.py
    # mcp.run(transport="streamable-http")  # uv --dir E:\dev\ai\mcp_demo  run mcp_server.py
    print("streamable已注册的工具:")
    for tool_info in mcp_streamable._tool_manager.list_tools():  # 这个方法是同步的
        print(f"- {tool_info.name}: {tool_info.description}")
    mcp_streamable.run(transport="streamable-http",host="0.0.0.0",port="5055",path="/streamable")