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
model = genai.GenerativeModel("gemini-2.5-flash")

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # 🔹 New: Track pending tool calls waiting for missing params
        self.pending_tool_call = None  

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

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and MCP tools"""

        # 🔹 CASE 1: We are waiting for user to provide missing parameters
        if self.pending_tool_call:
            tool_name, collected_params, missing_params = self.pending_tool_call

            # For now assume user gives values in order separated by commas
            user_inputs = [val.strip() for val in query.split(",")]
            if len(user_inputs) != len(missing_params):
                return f"Expected {len(missing_params)} values: {', '.join(missing_params)}"

            # Merge into collected_params
            for key, val in zip(missing_params, user_inputs):
                collected_params[key] = val

            # Call tool now that we have everything
            try:
                result = await self.session.call_tool(tool_name, collected_params)
                self.pending_tool_call = None  # reset
                return f"✅ Used tool {tool_name}:\n{result.content[0].text}"
            except Exception as e:
                self.pending_tool_call = None
                return f"❌ Error calling tool {tool_name}: {e}"
        
        # 🔹 CASE 2: Normal flow (Gemini decides)
        try:
            response = await self.session.list_tools()
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]

            tools_context = "\n".join([
                f"- {tool['name']}: {tool['description']}" 
                for tool in available_tools
            ])
            
            enhanced_query = f"""
                Available MCP Tools:
                {tools_context}
                User Query:
                {query}
                Instructions:
                - Decide if a tool is needed.
                - If yes, give tool name and map query to inputs.
                - If required params are missing, just mention that.
            """

            chat = model.start_chat(history=[])
            gemini_reply = chat.send_message(enhanced_query)
            response_text = gemini_reply.text

            # Match tools Gemini suggested
            # Match tools Gemini suggested
            for tool in available_tools:
                tool_name = tool['name']
                if tool_name.lower() in response_text.lower():
                    required_props = list(tool['input_schema']['properties'].keys())
                    provided_params = {}

                    if tool_name == "query_tool":
                        # 🔹 Special case: always map user input as 'query'
                        provided_params["query"] = query
                        result = await self.session.call_tool(tool_name, provided_params)
                        return f"✅ Used tool {tool_name}:\n{result.content[0].text}"

                    # Default behavior for other tools
                    for param in required_props:
                        if param.lower() in query.lower():
                            provided_params[param] = query

                    missing_params = [p for p in required_props if p not in provided_params]

                    if missing_params:
                        # 🔹 Ask user for missing params and store state
                        self.pending_tool_call = (tool_name, provided_params, missing_params)
                        return f"To use {tool_name}, please provide information in this specific format: {', '.join(missing_params)}"
                    
                    # If all params found → call tool
                    result = await self.session.call_tool(tool_name, provided_params)
                    return f"✅ Used tool {tool_name}:\n{result.content[0].text}"
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
