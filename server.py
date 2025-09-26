from typing import Any
import httpx
import sys
import logging
from mcp.server.fastmcp import FastMCP

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

# Initialize FastMCP server
mcp = FastMCP("rag")

API_URL = "http://localhost:8000/query"

async def call_rag_api(payload: dict[str, Any]) -> Any:
    """Make a request to the RAG API with error handling."""
    logger.info(f"Making API request to {API_URL} with payload: {payload}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            logger.info("API request successful")
            return result
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return {"error": str(e)}

@mcp.tool()
async def get_answer(query: str, top_k: int = 5, min_score: float = 0.5) -> Any:
    """Retrieve an answer from the RAG API.

    Args:
        query: The user query.
        top_k: Number of top results to consider.
        min_score: Minimum similarity score to accept.
    """
    # Print to stderr for immediate visibility
    print(f"🔍 TOOL CALLED: get_answer with query='{query}', top_k={top_k}, min_score={min_score}", file=sys.stderr)
    
    logger.info(f"Tool 'get_answer' called with query: '{query}', top_k: {top_k}, min_score: {min_score}")
    
    payload = {
        "query": query,
        "top_k": top_k,
        "min_score": min_score
    }
    
    result = await call_rag_api(payload)
    
    # Log success or failure based on the result
    if "error" in result:
        print(f"❌ TOOL FAILED: {result['error']}", file=sys.stderr)
        logger.error(f"Tool 'get_answer' failed: {result['error']}")
    else:
        print("✅ TOOL SUCCESS: get_answer completed successfully", file=sys.stderr)
        logger.info("Tool 'get_answer' completed successfully")
    
    return result

if __name__ == "__main__":
    # Print startup message to stderr (so it doesn't interfere with stdio transport)
    print("🚀 RAG MCP Server starting up...", file=sys.stderr)
    print(f"📡 Connecting to RAG API at: {API_URL}", file=sys.stderr)
    print("📝 Logging enabled - logs will appear in terminal and rag_server.log", file=sys.stderr)
    print("✅ Server ready - waiting for client connections", file=sys.stderr)
    
    # Initialize and run the server
    mcp.run(transport="stdio")
