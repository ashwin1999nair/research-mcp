import os
import httpx2
from dotenv import load_dotenv
from pathlib import Path
from mcp.server.mcpserver import MCPServer

load_dotenv(Path(__file__).parent / ".env")

TAVILY_URL = "https://api.tavily.com/search"
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
API_BASE = os.getenv("RESEARCH_API_URL", "http://localhost:8000")

mcp=MCPServer("research-mcp")

@mcp.tool()
def ping(name: str) -> str:
    """Health check for the research server. Returns a greeting
    confirming the server is reachable."""
    return f"research-mcp is alive, {name}"

@mcp.tool()
async def search_web(topic:str, max_results: int=5) -> str:
    """Search the web for pages about a topic and return their titles
    and URLs. Use this to find sources before reading them. Returns a
    numbered list, or an error message if the search fails."""

    if not TAVILY_KEY:
        return "Error: TAVILY_API_KEY is not set in the server environment."

    max_results = max(1, min(max_results, 10))

    payload={"query": topic, "max_results": max_results}
    headers = {"Authorization": f"Bearer {TAVILY_KEY}"}

    try:
        async with httpx2.AsyncClient(timeout=15.0) as client:
            response=await client.post(TAVILY_URL, json=payload, headers=headers)
            response.raise_for_status()
            data=response.json()

    except httpx2.TimeoutException:
        return "Error: the search request timed out after 15 seconds."
    except httpx2.HTTPStatusError as e:
        return f"Error: search API returned {e.response.status_code}."
    except Exception as e:
        return f"Error: search failed ({type(e).__name__})."

    results=data.get("results", [])
    if not results:
        return f"No results found for '{topic}'."
    
    lines = [
        f"{i}. {r.get('title', 'Untitled')}\n   {r.get('url', '')}"
        for i, r in enumerate(results, start=1)
    ]
    return f"Found {len(results)} results for '{topic}':\n\n" + "\n".join(lines)


@mcp.tool()
async def research_topic(topic: str, n_urls: int = 5) -> str:
    """Run a full multi-agent research pipeline on a topic: searches the
    web, scrapes the pages, retrieves the most relevant passages, and
    writes a synthesised report grounded in those sources. Takes 20-40
    seconds. Use this when the user wants an actual report, not just
    links. For a quick list of sources, use search_web instead."""

    n_urls = max(1, min(n_urls, 10))
    payload = {"topic": topic, "n_urls": n_urls}

    try:
        async with httpx2.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{API_BASE}/research", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx2.ConnectError:
        return (
            f"Error: could not reach the research API at {API_BASE}. "
            "Is the Research Assistant running?"
        )
    except httpx2.TimeoutException:
        return "Error: the research pipeline took longer than 120 seconds."
    except httpx2.HTTPStatusError as e:
        return f"Error: research API returned {e.response.status_code}."
    except Exception as e:
        return f"Error: research failed ({type(e).__name__})."

    report = data.get("report", "")
    urls = data.get("urls", [])
    cached = data.get("cached", False)

    if not report:
        return f"The pipeline returned no report for '{topic}'."

    out = [report]
    if urls:
        out.append("\nSources:")
        out.extend(f"- {u}" for u in urls)
    if cached:
        out.append("\n(served from cache)")
    return "\n".join(out)

if __name__=="__main__":
    mcp.run(transport="stdio")

