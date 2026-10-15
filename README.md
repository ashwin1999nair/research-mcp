# research-mcp

An MCP server that exposes a multi-agent RAG research pipeline as tools
any MCP client can call.

It is a thin protocol adapter: it talks MCP over stdio to the client, and
plain HTTP to the
[AI Research Assistant](https://github.com/ashwin1999nair/research-assistant)
backend. No shared code between the two — the pipeline could be rewritten
in another language and this would still work.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `ping` | `name` | Health check |
| `search_web` | `topic`, `max_results` | Titles, URLs from Tavily |
| `research_topic` | `topic`, `n_urls` | Full synthesised report with sources (20–40s) |

## How it fits together

```
MCP client  ──stdio──>  server.py  ──HTTP──>  Research Assistant API
                                                 │
                                       LangGraph: search → scrape → synthesis
```

## Running it

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # then add your Tavily key
```

`research_topic` needs the Research Assistant running:

```bash
uvicorn main:app    # in the research-assistant repo
```

Test with the MCP Inspector:

```bash
mcp dev server.py
```

## Registering with an MCP client

Add to the client's MCP config. Absolute paths, and the **venv's** Python —
clients don't activate your virtualenv:

```json
{
  "mcpServers": {
    "research-mcp": {
      "command": "C:\\path\\to\\research-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\research-mcp\\server.py"]
    }
  }
}
```

## Notes

- Built against **MCP Python SDK 2.x**, where `FastMCP` was renamed
  `MCPServer`. Examples using `from mcp.server.fastmcp import FastMCP`
  are for 1.x and will not run here.
- The dependency is **`httpx2`**, not `httpx` — that is what the 2.x SDK
  pulls in.
- `.env` is loaded relative to the script, not the working directory,
  because MCP clients launch the server from an arbitrary location.
- Tools return error strings rather than raising, so a failure lands in
  the model's context where it can react, instead of surfacing as a
  protocol error.
- Verified with the MCP Inspector and in Claude Desktop.