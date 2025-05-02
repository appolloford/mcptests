import os
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# from anthropic import Anthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama, OllamaLLM
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # need a larger context window to process the document fetched by the tools
        self.model = ChatOllama(model="llama3.2", num_ctx=16384)

    async def connect_to_server(self, server: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """

        # Check if the server is a URL or a local script
        if server.startswith("http://") or server.startswith("https://"):
            url = server
            server_script_path = None
            transport = await self.exit_stack.enter_async_context(sse_client(url))
        else:
            url = None
            server_script_path = server

            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=os.environ.copy()
            )
            transport = await self.exit_stack.enter_async_context(stdio_client(server_params))

        self.stdio, self.write = transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query with available tools"""
        messages = {
            "messages": query,
        }

        response = await self.session.list_tools()
        available_tools = await load_mcp_tools(self.session)
        # resource is not supported yet?
        # response = await self.session.list_resources()
        # available_reousrces = await load_mcp_resources(self.session)

        # Create Ollama agent
        agent = create_react_agent(self.model, available_tools)
        response = await agent.ainvoke(messages)
        final_text = []

        for chunk in response["messages"]:
            # chunk.pretty_print()
            if isinstance(chunk, AIMessage):
                final_text.append(chunk.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <mcp_server_url/path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
