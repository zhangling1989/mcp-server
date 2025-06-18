from fastmcp import Client



from fastmcp.client import StdioTransport,SSETransport,StreamableHttpTransport # 使用SSETransport



import asyncio

sse_url = "http://localhost:5050/sse"
streamablehttp_url = "http://localhost:5051/streamable"
sse_client = Client(SSETransport(sse_url))
streamablehttp_client = Client(StreamableHttpTransport(streamablehttp_url))



async def sse():
    # Connection is established here
    async with sse_client:
        print(f"Client connected: {sse_client.is_connected()}")

        tools = await sse_client.list_tools()
        for tool in tools:
            print("-" * 20)
            print(f"工具名称: {tool.name}")
            print(f"工具描述: {tool.description}")
            print(f"工具参数: {tool.inputSchema["required"]}")
            print("-" * 20)
        use = input("请输入要使用的工具名称: ")  # 输入工具名称
        tools = await sse_client.list_tools()
        if any(tool.name == use for tool in tools):  # 判断add工具是否存在
            for tool in tools:
                if tool.name == use:
                    required = tool.inputSchema["required"]
                    break
            input_required = {}
            for i in required:
                input_required[i] = input(f"请输入{i}的值: ")
                if tool.inputSchema["properties"][i]["type"] == "int":
                    input_required[i] = int(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "boolean":
                    input_required[i] = bool(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "number":
                    input_required[i] = float(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "string":
                    pass
                else:
                    print(f"未知类型：{tool.inputSchema['properties'][i]['type']}")
            result = await sse_client.call_tool(tool.name, input_required)
            print(f"返回结果: {result}")

    # Connection is closed automatically here
    print(f"Client状态: {sse_client.is_connected()}")

async def streamablehttp():
    # Connection is established here
    async with streamablehttp_client:
        print(f"Client connected: {streamablehttp_client.is_connected()}")

        tools = await streamablehttp_client.list_tools()
        for tool in tools:
            print("-" * 20)
            print(f"工具名称: {tool.name}")
            print(f"工具描述: {tool.description}")
            print(f"工具参数: {tool.inputSchema["required"]}")
            print("-" * 20)
        use = input("请输入要使用的工具名称: ")  # 输入工具名称
        tools = await streamablehttp_client.list_tools()
        if any(tool.name == use for tool in tools):  # 判断add工具是否存在
            for tool in tools:
                if tool.name == use:
                    required = tool.inputSchema["required"]
                    break
            input_required = {}
            for i in required:
                input_required[i] = input(f"请输入{i}的值: ")
                if tool.inputSchema["properties"][i]["type"] == "int":
                    input_required[i] = int(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "boolean":
                    input_required[i] = bool(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "number":
                    input_required[i] = float(input_required[i])
                elif tool.inputSchema["properties"][i]["type"] == "string":
                    pass
                else:
                    print(f"未知类型：{tool.inputSchema['properties'][i]['type']}")
            result = await streamablehttp_client.call_tool(tool.name, input_required)
            print(f"返回结果: {result}")

    # Connection is closed automatically here
    print(f"Client状态: {streamablehttp_client.is_connected()}")





if __name__ == '__main__':
    asyncio.run(streamablehttp())