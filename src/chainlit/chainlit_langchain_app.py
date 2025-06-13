# https://github.com/Zenulous/local-ai-mcp-chainlit/blob/main/app.py
# https://github.com/Chainlit/cookbook/blob/main/mcp/app.py#L130
# from openai import AsyncOpenAI
import chainlit as cl
from typing import Dict, Any, List
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, EmbeddedResource, ImageContent

from langchain_core.tools import StructuredTool, ToolException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama, OllamaLLM

NonTextContent = ImageContent | EmbeddedResource

@cl.on_chat_start
async def start():
    cl.user_session.set(
        "message_history",
        [
            # ("system", "You are a helpful AI assistant running locally via Ollama. You can access tools using MCP servers."),
            {
                "role": "system",
                "content": "You are a helpful AI assistant running locally via Ollama. You can access tools using MCP servers.",
            }
        ],
    )
    cl.user_session.set("model", ChatOllama(model="llama3.2", num_ctx=16384))

    await cl.Message(
        content="Welcome! I'm using a local model running in Ollama with MCP integration. \n"
    ).send()


@cl.on_mcp_connect
async def on_mcp_connect(connection, session: ClientSession):
    cl.Message(f"Connected to MCP server: {connection.name}").send()

    try:
        result = await session.list_tools()

        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in result.tools
        ]

        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection.name] = tools
        cl.user_session.set("mcp_tools", mcp_tools)

        await cl.Message(
            f"Found {len(tools)} tools from {connection.name} MCP server."
        ).send()
    except Exception as e:
        await cl.Message(f"Error listing tools from MCP server: {str(e)}").send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):

    mcp_tools = cl.user_session.get("mcp_tools", {})
    if name in mcp_tools:
        del mcp_tools[name]
        cl.user_session.set("mcp_tools", mcp_tools)

    await cl.Message(f"Disconnected from MCP server: {name}").send()


@cl.step(type="tool")
async def execute_tool(tool_name: str, tool_input: Dict[str, Any]):
    print("Executing tool:", tool_name)
    print("Tool input:", tool_input)
    mcp_name = None
    mcp_tools = cl.user_session.get("mcp_tools", {})

    for conn_name, tools in mcp_tools.items():
        if any(tool["name"] == tool_name for tool in tools):
            mcp_name = conn_name
            break

    if not mcp_name:
        return {"error": f"Tool '{tool_name}' not found in any connected MCP server"}

    mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name)

    try:
        result = await mcp_session.call_tool(tool_name, tool_input)
        return result
    except Exception as e:
        return {"error": f"Error calling tool '{tool_name}': {str(e)}"}

async def format_tools(tools: List[Dict[str, Any]]) -> StructuredTool:
    mcp_tools = cl.user_session.get("mcp_tools", {})

    available_tools = []
    for tool in tools:
        tool_name = tool["name"]
        mcp_name = None

        for conn_name, mtools in mcp_tools.items():
            if any(t["name"] == tool_name for t in mtools):
                mcp_name = conn_name
                break
        mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name)

        available_tools.extend(await load_mcp_tools(mcp_session))
        print(f"Available tools from {mcp_name}: {available_tools}")

    return available_tools


def format_calltoolresult_content(result):
    """Extract text content from a CallToolResult object.

    The MCP CallToolResult contains a list of content items,
    where we want to extract text from TextContent type items.
    """
    text_contents = []

    if isinstance(result, CallToolResult):
        for content_item in result.content:
            # This script only supports TextContent but you can implement other CallToolResult types
            if isinstance(content_item, TextContent):
                text_contents.append(content_item.text)

    if text_contents:
        return "\n".join(text_contents)
    return str(result)


@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    # message_history.append(("human", message.content))

    try:
        # Initial message for the first assistant response
        initial_msg = cl.Message(content="")
        await initial_msg.send()

        mcp_tools = cl.user_session.get("mcp_tools", {})
        all_tools = []
        for connection_tools in mcp_tools.values():
            all_tools.extend(connection_tools)

        if all_tools:
            langgraph_tools = await format_tools(all_tools)

        print("Formatted tools:", langgraph_tools)
        model = cl.user_session.get("model")
        agent = create_react_agent(model, langgraph_tools)
        print("Agent created:", agent)
        print("Message history:", message_history)
        await cl.Message(content="Processing your request...").send()

        response = await agent.ainvoke({"messages": message.content})
        final_text = []

        for chunk in response["messages"]:
            chunk.pretty_print()
            if isinstance(chunk, AIMessage):
                final_text.append(chunk.content)
        await cl.Message("".join(final_text)).send()

    except Exception as e:
        error_message = f"Error: {str(e)}"
        await cl.Message(content=error_message).send()

if __name__ == "__main__":
    print("Starting Chainlit app with LM Studio and MCP integration...")