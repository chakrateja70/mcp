from mcp.server.fastmcp import FastMCP
from typing import Any
import httpx
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Log to stderr to avoid interfering with stdio transport
        logging.FileHandler('rag_server.log', mode='a')  # Also log to file
    ]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("newrag")

login_api = "http://localhost:8000/login"
query_api = "http://localhost:8000/query"
asyncclient = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

async def call_login_api(payload: dict[str, Any]) ->Any:
    """call login api and send request payload for successful login"""
    try:
        response = await asyncclient.post(login_api, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result
    except httpx.HTTPStatusError as e:
        logger.error("RAG API returned an error status", exc_info=True)
        raise
    except httpx.RequestError as e:
        logger.error("Network error while calling Login API", exc_info=True)
        raise
    except ValueError as e:  # JSON decode error
        logger.error("Invalid JSON in Login API response", exc_info=True)
        raise

async def call_query_api(payload: dict[str, Any]) -> Any:
    """call query api and send request payload for successful query"""
    try:
        response = await asyncclient.post(query_api, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result
    except httpx.HTTPStatusError as e:
        logger.error("RAG API returned an error status", exc_info=True)
        raise
    except httpx.RequestError as e:
        logger.error("Network error while calling Query API", exc_info=True)
        raise
    except ValueError as e:  # JSON decode error
        logger.error("Invalid JSON in Query API response", exc_info=True)
        raise

@mcp.tool()
async def login_tool(name: str = None, age: int = None) -> Any:
    """
        Use this tool when the user asks about registration, login, sign in, sign off, or authentication related to Lomaa IT Solutions 
        (including variations like 'Lomaa', 'lomaa it solutions', or simply 'lomaa').  

        This tool requires two input parameters:
        - name
        - age  

        If the user mentions any of these actions but does not provide both name and age, ask them to supply the missing information.
    """
    payload = {"name": name, "age": age}
    logger.info(f"Calling login API with payload: {payload}")
    response = await call_login_api(payload)
    print("Tool response:", response)
    return response

@mcp.tool()
async def query_tool(query: str) -> Any:
    """Use this tool when the user asks questions related to 'lomma', 'lomaa', 'lomaa it', 'lomaa it solutions', or any general information queries. This tool searches the RAG system to provide relevant answers based on the stored knowledge base."""
    payload = {"query": query}
    return await call_query_api(payload)

if __name__ == "__main__":
    mcp.run(transport="stdio")
