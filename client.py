import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv
import sys
import google.generativeai as genai  # Gemini SDK

load_dotenv()  # load environment variables from .env

# Initialize Gemini API key from environment
GEN_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEN_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY in your .env file")

genai.configure(api_key=GEN_API_KEY)

# Initialize the model
model = genai.GenerativeModel("gemini-2.5-pro")
class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    # Initialize model globally (so it's reused)
    

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and MCP tools"""
        try:
            # List tools from MCP
            response = await self.session.list_tools()
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]

            # Create a context-aware prompt that includes available tools
            tools_context = "\n".join([
                f"- {tool['name']}: {tool['description']}" 
                for tool in available_tools
            ])
            
            enhanced_query = f"""
                You are given the following information:
                Available MCP Tools:
                {tools_context}
                User Query:
                {query}
                Instructions:
                1. First, decide if the user query can be answered directly without using any tool.
                2. If a tool is required, identify the most suitable tool from the list above.
                3. Clearly specify:
                - The tool name
                - The exact parameters/inputs to use
                4. If no tool is needed, provide a concise and accurate answer directly.
                Now determine the best response.
            """

            # Start a chat with the Gemini model
            chat = model.start_chat(history=[])
            gemini_reply = chat.send_message(enhanced_query)
            
            # Get the text response
            response_text = gemini_reply.text
            
            for tool in available_tools:
                tool_name = tool['name']
                if tool_name.lower() in response_text.lower():
                    # Try to extract or ask for parameters
                    print(f"\nGemini suggested using tool: {tool_name}")
                    # print(f"Tool description: {tool['description']}")
                    
                    try:
                        if 'search' in tool['input_schema'].get('properties', {}):
                            # If tool has a 'search' parameter, use the query
                            result = await self.session.call_tool(tool_name, {"search": query})
                            return f"Used tool {tool_name}:\n{result.content[0].text}"
                        else:
                            # Try with the most common parameter names
                            common_params = ['query', 'text', 'input', 'prompt']
                            for param in common_params:
                                if param in tool['input_schema'].get('properties', {}):
                                    result = await self.session.call_tool(tool_name, {param: query})
                                    return f"Used tool {tool_name}:\n{result.content[0].text}"
                    except Exception as tool_error:
                        print(f"Error calling tool {tool_name}: {tool_error}")
                        continue
            return response_text  
        except Exception as e:
            return f"Error processing query: {str(e)}"


    async def chat_loop(self):
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
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())