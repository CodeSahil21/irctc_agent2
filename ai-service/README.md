# AI Service

Python orchestration layer for the IRCTC stack.

## Layout

- `app/api` - HTTP and WebSocket entrypoints
- `app/auth` - JWT and authorization helpers
- `app/config` - app settings and constants
- `app/graph` - LangGraph state, routing, and nodes
- `app/llm` - model clients, prompts, streaming, structured output
- `app/tools` - tool registry, execution, and normalization
- `app/mcp` - MCP client/session/transport wrappers
- `app/memory` - conversation, preferences, checkpoints, cache
- `app/telemetry` - tracing, metrics, and logging
- `app/websocket` - connection and event management

## Run

```bash
uvicorn app.main:app --reload
```
