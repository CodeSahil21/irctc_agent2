# ai-service

FastAPI + LangGraph orchestration layer for the IRCTC AI assistant. This service owns the AI runtime: tool planning, MCP tool execution, train ranking, human approval interrupts, reflection, conversation persistence, and Socket.IO streaming.

> **Stack:** OpenAI (`gpt-4o-mini`) · LangGraph · MCP Streamable HTTP · MongoDB · Socket.IO

---

## Mental model

> OpenAI decides **what** to do. Python decides **how** to do it. MCP provides the live tool capabilities. LangGraph keeps the whole interaction stateful, resumable, and observable.

---

## Tech stack

| Layer | Technology |
|---|---|
| HTTP API | FastAPI |
| Realtime | python-socketio (AsyncServer, ASGI-mounted) |
| Orchestration | LangGraph (`StateGraph` + `MongoDBSaver` checkpointer) |
| LLM | OpenAI via `openai` SDK (`gpt-4o-mini` default) |
| Tool protocol | MCP Streamable HTTP (JSON-RPC 2.0) |
| Database | MongoDB (Motor async driver + pymongo for checkpointer) |
| Tracing | LangSmith (`wrap_openai`) |
| Logging | Loguru |

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          ai-service                             │
│                                                                 │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────────┐   │
│  │ Socket.IO│   │  FastAPI HTTP │   │   LangGraph agent     │   │
│  │  server  │──▶│  /api/v1     │──▶│   (4-node graph)      │   │
│  └──────────┘   └──────────────┘   └───────────┬───────────┘   │
│                                                 │               │
│                  ┌──────────────────────────────┼──────────┐    │
│                  │                              │          │    │
│          ┌───────▼──────┐              ┌────────▼──────┐   │    │
│          │  MCP Registry │              │  MongoDB      │   │    │
│          │  (discovery + │              │  (motor +     │   │    │
│          │   execution)  │              │  checkpointer)│   │    │
│          └───────┬───────┘              └───────────────┘   │    │
│                  │                                           │    │
└──────────────────┼───────────────────────────────────────────┘   │
                   │                                               │
           ┌───────▼────────┐     ┌──────────────────┐            │
           │ IRCTC MCP server│     │  LangSmith        │            │
           │  (port 3000)   │     │  (tracing)        │            │
           └────────────────┘     └──────────────────┘            │
```

---

## LangGraph flow

Built in [`app/graph/builder.py`](app/graph/builder.py). Every user message runs through this 4-node graph.

```
START
  │
  ▼
agent_node ──── has tool calls? ────────────────────────────┐
  │                                                         │
  │ destructive tool?          non-destructive tool?        │
  ▼                                  │                      │
human_approval_node                  │                      │
  │                                  ▼                      │
  │ confirmed?           tool_executor_node ◀───────────────┘
  │     ▼                      │
  │  tool_executor_node         │ (always returns to agent_node)
  │                             ▼
  │ declined?              agent_node
  │     ▼
  │  agent_node (relays cancellation)
  │
  │ no tool calls + reflection needed?
  ▼
reflection_node
  │ passed / retries exhausted?  ──▶ END
  │ failed, retries < 1          ──▶ agent_node (one retry with feedback)
  │
  └── (no tool calls, no reflection) ──▶ END
```

### Routing rules summary

| From node | Condition | To node |
|---|---|---|
| `agent_node` | pending tool calls + any destructive | `human_approval_node` |
| `agent_node` | pending tool calls, none destructive | `tool_executor_node` |
| `agent_node` | no pending calls + reflection needed | `reflection_node` |
| `agent_node` | no pending calls | `END` |
| `human_approval_node` | `confirmed=True` | `tool_executor_node` |
| `human_approval_node` | `confirmed=False` | `agent_node` |
| `tool_executor_node` | always | `agent_node` |
| `reflection_node` | `reflection_passed=True` | `END` |
| `reflection_node` | failed + `retries >= 1` | `END` |
| `reflection_node` | failed + `retries < 1` | `agent_node` |

---

## Node reference

### `agent_node`
**File:** `app/graph/nodes/agent_node.py`

The single decision-making node. Replaces the previous multi-node pipeline (intent → slot filler → planner → response).

On each invocation it:
1. Builds a system prompt with user context (preferences, fetched booking count, saved passengers).
2. Passes the full conversation history + all live MCP tool schemas to the LLM.
3. If the model emits **tool calls** → stores them as `pending_tool_calls` and returns to the router.
4. If the model emits **plain text** → that is the final answer; graph routes to `reflection_node` or `END`.

Key behaviours:
- **Loop guard:** `agent_loop_count` increments on every entry. At `MAX_LOOP=8` a safe fallback message is emitted and the loop resets.
- **Parallel tool calls:** When the user asks to compare fares/availability across multiple trains, the model emits multiple tool calls in a single turn. `tool_executor_node` runs them concurrently via `asyncio.gather` — no special tagging required.
- **PNR grounding:** `_ground_response()` scans the reply for 10-digit numbers and replaces any PNR not present in state data with `[PNR unavailable]`.
- **Reflection gate:** Sets `reflection_required=True` when the answer contains real data worth cross-checking.

---

### `tool_executor_node`
**File:** `app/graph/nodes/tool_executor_node.py`

Executes all `pending_tool_calls` concurrently via `asyncio.gather`, then returns `ToolMessage` results so the model can see them on the next loop.

Key behaviours:
- Per-tool timeout of 15 seconds.
- Applies inline train ranking (cheapest/fastest/best_avail) when `search_trains` or `recommend_trains` returns results.
- Long-lived results (`get_booking_history`, `get_saved_passengers`) are written to `persistent_results` and survive across turns.
- Populates backward-compat top-level state fields (`search_results`, `fare`, `availability`, `booking`) that the `/agent` response serialiser reads.
- Appends a `ToolCall` record to `tool_history` for reflection and metrics.

**Long-lived result persistence:**

| Tool | State target | Persists? |
|---|---|---|
| `get_booking_history` | `persistent_results["get_booking_history"]` | Across turns (slimmed to 9 key fields) |
| `get_saved_passengers` | `persistent_results["get_saved_passengers"]` | Across turns |
| `search_trains`, `recommend_trains` | `search_results` (ranked inline) | Current turn only |
| `check_availability` | `availability` | Current turn only |
| `get_fare` | `fare` | Current turn only |
| `book_ticket`, `cancel_ticket`, etc. | `booking` | Current turn only |
| everything else | `tool_results[tool_name]` | Cleared next turn |

---

### `human_approval_node`
**File:** `app/graph/nodes/human_approval_node.py`

Pauses graph execution using LangGraph's `interrupt()`. The checkpoint is saved to MongoDB — the graph survives process restarts and resumes when the caller sends `Command(resume=<value>)`.

Destructive tools that trigger this node:

| Tool | Condition |
|---|---|
| `book_ticket` | Always |
| `cancel_ticket` | Always |
| `update_booking` | When changing `status` or `newBoardingStation` |
| `manage_reminder` | When `action == "delete"` |

Resume value normalisation: `bool` is used directly; strings like `"yes"`, `"y"`, `"confirm"`, `"ok"`, `"proceed"` resolve to `True`. Anything else resolves to `False`.

---

### `reflection_node`
**File:** `app/graph/nodes/reflection_node.py`

Optional quality-check pass. Only runs when `reflection_required=True` and `reflection_retries < 1` (hard cap at one retry).

- **Fast path (deterministic):** If any tool failed (`errors` list or `tool_history` has `status=failed`), marks `reflection_passed=False` without calling the LLM.
- **LLM path:** Calls `reflect_on_results` function tool (`temperature=0`, `max_tokens=300`). Returns `{satisfied, feedback}`.
- `satisfied=False` → sets `reflection_feedback` → routes back to `agent_node` for one retry with the feedback injected into the system prompt.
- Any exception → fails open (`reflection_passed=True`) — reflection never blocks a response.

---

## Graph state (`TravelState`)

**File:** `app/graph/state.py`

```
TravelState
├── Conversation
│   ├── messages              List[BaseMessage]  — append-only via add_messages reducer
│   ├── conversation_id       str
│   └── turn_count            int
│
├── User Identity
│   ├── user_email            str
│   └── user_name             str
│
├── User Preferences (long-lived, persisted to MongoDB)
│   └── user_preferences: UserPreferences
│       ├── preferred_class, preferred_quota
│       ├── berth_preference
│       └── senior_citizen (bool)
│
├── Agent loop
│   ├── pending_tool_calls    List[dict]   — tool calls emitted by agent_node
│   └── agent_loop_count      int          — reset to 0 on final answer / new turn
│
├── Tool Execution
│   ├── tool_history          List[ToolCall]   — accumulated this turn
│   └── persistent_results    Dict[str, Any]   — survives across turns
│       ├── get_booking_history  → slimmed booking list
│       └── get_saved_passengers → passenger list
│
├── Reflection
│   ├── reflection_required   bool
│   ├── reflection_passed     bool
│   ├── reflection_feedback   str
│   └── reflection_retries    int
│
├── Human Approval
│   ├── confirmation_required bool
│   ├── confirmation_prompt   str
│   └── confirmed             bool
│
├── Error tracking
│   └── errors                List[str]
│
├── Execution Metrics
│   └── execution_metrics: ExecutionMetrics
│       ├── turn_start_time, tools_called
│       ├── total_latency_ms, llm_calls
│
└── Backward-compat fields (read by /agent response serialiser)
    ├── intent, travel
    ├── search_results, ranked_results
    ├── selected_train, availability, fare
    ├── booking, passengers
```

---

## Memory layers

### Conversation window (`app/memory/conversation_memory.py`)
`format_messages()` applies a 20-message sliding window before every LLM call. Always anchors the first `HumanMessage` and trims from the middle. `ToolMessage` entries are excluded — they surface through the tool context block instead.

### Conversation persistence (`app/services/conversation_manager.py`)

| Method | What it does |
|---|---|
| `open(conversation_id, user_email)` | Load or create conversation doc; load `UserPreferences` from DB |
| `save_turn(...)` | Upsert conversation, increment turn, persist messages and `ExecutionLogDoc`; triggers rolling summary every 10 turns |
| `summarize(conversation_id)` | LLM-generated rolling summary (max 200 words) |
| `build_context(conversation_id)` | Returns `{summary, messages, turn_count}` for resume flows |
| `close(user_email, prefs)` | Persist updated `UserPreferences` back to MongoDB |

### User preferences (`app/memory/preference_memory.py`)
Loaded at `open()`, seeded into `state["user_preferences"]`. Merged into agent context each turn. Persisted at `close()`.

### Checkpointing (`app/memory/checkpoints.py`)
`MongoDBSaver` (from `langgraph-checkpoint-mongodb`) backed by a sync `pymongo` client. LangGraph offloads blocking pymongo calls to a thread executor. The same `thread_id` (conversation ID) is used on every `ainvoke` call, so LangGraph automatically loads the full prior state and saves after each turn — enabling `interrupt()` / `Command(resume=...)` across process restarts.

### Context builder (`app/memory/context_builder.py`)
- `build_tool_context(state)` — assembles the `[Tool Results]` block for the response node.
- `build_planner_context(state, tools_summary)` — surfaces carried-forward booking history and saved passengers so the LLM can extract train numbers and PNRs without asking the user.

---

## MCP layer

### Transport (`app/mcp/transport.py`)
`MCPTransport` — async HTTP client over `httpx`. Sends JSON-RPC 2.0 `POST /mcp` with per-user headers (`x-user-email`, `x-user-name`, `mcp-session-id`). Handles SSE response parsing and maps HTTP/network errors to typed MCP exceptions.

### Sessions (`app/mcp/session.py`)
One `MCPSession` is maintained per user email. Tracks the MCP session ID, call counts, and health metrics.

### Client (`app/mcp/client.py`)
`MCPClient` — manages per-user sessions and executes tool calls with up to 3 retries and exponential backoff (`[0.5s, 1.0s, 2.0s]`). Resets sessions automatically on `MCPSessionError`. Exposes `list_tools()` for startup discovery.

### Discovery (`app/mcp/discovery.py`)
`MCPDiscovery.discover()` fetches `tools/list` at startup. Tools are normalised to **OpenAI function-calling format**: `{"type": "function", "function": {"name", "description", "parameters"}}`. The registry refreshes lazily if an unknown tool is called at runtime.

### Registry (`app/mcp/registry.py`)
`MCPToolRegistry.execute()` is the single call point from the graph:
1. Checks `is_known(tool_name)` — triggers refresh if unknown.
2. Strips hallucinated args not in the schema's `properties`.
3. Validates required fields — returns an `INVALID_PARAMETERS` error without calling MCP if any are missing.
4. Calls `MCPClient.call_tool()` and returns `json.dumps(result.to_dict())`.

### Train ranking (`app/graph/ranking.py`)
Pure Python, no LLM. Called inline in `tool_executor_node` after any search result arrives.

| Mode | Trigger keywords | Sort key |
|---|---|---|
| `fastest` | fast, quick, shortest, direct | `durationMins` ascending |
| `best_avail` | available, seats, confirm | seats descending → fare ascending |
| `cheapest` (default) | cheap, budget, low fare (or no keyword) | fare ascending |

---

## API reference

Base path: `/api/v1`

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — returns `{status, environment}` |

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Non-streaming LLM completion. Returns `ChatResponse`. |
| `POST` | `/chat/stream` | Token-by-token SSE stream. Emits `{"content": token}` chunks and a final `{"done": true}`. |
| `POST` | `/agent` | Run the full LangGraph agent. Returns the structured agent response (see below). |

**`POST /agent` request body (`AgentRequest`):**

```json
{
  "message": "Find trains from Delhi to Mumbai tomorrow",
  "conversation_id": "conv_abc123",
  "user_email": "user@example.com",
  "user_name": "Alice",
  "resume": false,
  "resume_value": null,
  "search_results": null,
  "selected_train": null,
  "availability": null,
  "fare": null,
  "passengers": null,
  "booking": null
}
```

Set `"resume": true` with `"resume_value": "yes"` (or `false`) to resume a graph interrupted at a human approval gate.

**`POST /agent` response:**

```json
{
  "message": "Here are the trains I found...",
  "intent": "search_trains",
  "travel_context": { "from_station": "NDLS", "to_station": "BCT", "date": "2026-07-24" },
  "search_results": [...],
  "selected_train": null,
  "availability": null,
  "fare": null,
  "booking": null,
  "confirmation_required": false,
  "confirmation_prompt": null,
  "interrupted": false,
  "errors": []
}
```

When `"interrupted": true`, the graph is paused. Re-send with `"resume": true` and the user's confirmation string.

### Conversations

| Method | Path | Description |
|---|---|---|
| `GET` | `/conversations/{conversation_id}/messages` | Fetch message history (default limit: 50) |
| `GET` | `/conversations/{conversation_id}/context` | Fetch summary + recent messages for resume flows |
| `GET` | `/conversations/user/{user_email}` | List recent conversations for a user (default limit: 20) |
| `POST` | `/conversations/{conversation_id}/summarize` | Manually trigger a rolling LLM summary |

### Real-time (Socket.IO)

Mounted at the ASGI root alongside FastAPI. Clients connect and emit `query:send` (new message) or `query:resume` (confirmation response). The server streams back tokens and final structured results.

---

## Auth

JWT verification is shared with the auth-service. The `JWT_SECRET` and `JWT_ALGORITHM` settings must match. Tokens are read from the `Authorization: Bearer` header or a cookie.

---

## Error handling

**Exception hierarchy** (`app/core/exceptions.py`):

| Exception | HTTP status | When raised |
|---|---|---|
| `ValidationException` | 400 | Malformed request (non-billing) |
| `AuthenticationException` | 401 | OpenAI API key invalid |
| `RateLimitException` | 429 | OpenAI rate limit hit |
| `ModelProviderException` | 502 | Generic OpenAI API error |
| `ServiceUnavailableException` | 503 | Connection error, timeout, or quota/billing issue |

All exceptions are sanitised — raw SDK messages, stack traces, and account info never reach clients.

---

## Configuration

All settings in `app/config/settings.py` via `pydantic-settings`. Copy `.env.example` to `.env` and fill in the required values.

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | — | **Yes** | Must start with `sk-` |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o-mini` | No | OpenAI model name |
| `APP_NAME` | `ai-service` | No | Application name |
| `APP_ENV` | `development` | No | `development` / `production` |
| `DEBUG` | `false` | No | Enables uvicorn reload and API docs |
| `LOG_LEVEL` | `INFO` | No | Loguru log level |
| `MCP_SERVER_URL` | `http://localhost:3000` | No | IRCTC MCP server base URL |
| `MCP_SERVER_TIMEOUT` | `30.0` | No | Per-request MCP timeout in seconds |
| `MONGO_URL` | `mongodb://localhost:27017` | No | MongoDB connection string |
| `MONGO_DB` | `irctc_ai` | No | MongoDB database name |
| `JWT_SECRET` | `change-me` | **Yes** | Shared secret with auth-service |
| `JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `LANGSMITH_TRACING` | `false` | No | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | — | No | Required if tracing is enabled |
| `LANGSMITH_PROJECT` | `default` | No | LangSmith project name |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | No | LangSmith endpoint |

> **Note:** A warning is emitted at startup if `JWT_SECRET` is still set to `"change-me"`.

---

## Local development

### Prerequisites

- Python 3.11+
- MongoDB running locally (or update `MONGO_URL`)
- IRCTC MCP server running at `MCP_SERVER_URL`

### Setup

```bash
# Clone and enter the service directory
cd ai-service

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package in editable mode (all dependencies)
pip install -e .

# Copy and fill in environment variables
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and JWT_SECRET at minimum
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs available at `http://localhost:8000/docs` (disabled in `production` env).

---

## Docker

```bash
# Build
docker build -t ai-service .

# Run
docker run --env-file .env -p 8000:8000 ai-service
```

The `Dockerfile` uses `python:3.11-slim`, exposes port `8000`, and runs:
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Startup sequence

On application startup (`app/core/lifespan.py`):

1. **LangSmith** — initialised if `LANGSMITH_TRACING=true` and API key is set; `wrap_openai` applied to the OpenAI client.
2. **OpenAIService** — `AsyncOpenAI` client wrapped and stored on `app.state`.
3. **MCP transport & client** — `MCPTransport` connects; `MCPClient` wraps it.
4. **MCP discovery** — `MCPDiscovery.discover()` called with 5 retry attempts; warns and continues if the MCP server is not yet available (lazy refresh kicks in at runtime).
5. **MCP registry** — `MCPToolRegistry` wired with the client and discovery cache.
6. **MongoDB** — Motor async client created; collection indexes set up (`conversations`, `preferences`, `executions`).
7. **Checkpointer** — `MongoDBSaver` initialised for LangGraph state persistence.
8. **Agent graph** — `create_agent_graph()` compiles the `StateGraph` with the checkpointer.
9. **ConversationManager** — wired with the DB and LLM service.
10. **Socket.IO manager** — `_make_manager()` wired with the agent graph and conversation manager.

On shutdown: LangSmith traces are flushed, MCP client disconnects, MongoDB clients close cleanly.

---

## Project structure

```
ai-service/
├── app/
│   ├── api/
│   │   ├── chat.py              # POST /chat, /chat/stream, /agent
│   │   ├── conversations.py     # GET/POST /conversations/*
│   │   ├── health.py            # GET /health
│   │   ├── routes.py            # Router aggregator
│   │   └── dependencies.py      # FastAPI dependency providers
│   ├── auth/
│   │   ├── jwt.py               # JWT verification
│   │   └── current_user.py      # CurrentUser dataclass
│   ├── config/
│   │   ├── settings.py          # Pydantic settings (env var binding)
│   │   └── constants.py
│   ├── core/
│   │   ├── exceptions.py        # BaseAPIException hierarchy
│   │   ├── handlers.py          # Global FastAPI exception handlers
│   │   └── lifespan.py          # Startup / shutdown lifecycle
│   ├── db/
│   │   ├── models.py            # MongoDB document models
│   │   ├── mongo.py             # Motor client factory
│   │   └── repositories/
│   │       ├── conversation_repo.py
│   │       ├── execution_repo.py
│   │       └── preference_repo.py
│   ├── graph/
│   │   ├── builder.py           # create_agent_graph()
│   │   ├── edges.py             # Conditional routing functions
│   │   ├── ranking.py           # Deterministic train ranking
│   │   ├── state.py             # TravelState TypedDict
│   │   ├── tool_meta.py         # DESTRUCTIVE_TOOLS registry + prompt builders
│   │   └── nodes/
│   │       ├── agent_node.py         # LLM decision node
│   │       ├── tool_executor_node.py # Concurrent MCP tool execution
│   │       ├── human_approval_node.py# LangGraph interrupt gate
│   │       └── reflection_node.py    # Quality-check pass
│   ├── mcp/
│   │   ├── client.py            # MCPClient (retry, per-user sessions)
│   │   ├── discovery.py         # Tool schema discovery
│   │   ├── exceptions.py        # MCP error hierarchy
│   │   ├── normalizer.py        # ToolResult + response normalisation
│   │   ├── registry.py          # MCPToolRegistry (validate + execute)
│   │   ├── session.py           # Per-user MCPSession
│   │   └── transport.py         # HTTP POST /mcp over httpx
│   ├── memory/
│   │   ├── checkpoints.py       # MongoDBSaver factory
│   │   ├── context_builder.py   # Tool result / planner context assembly
│   │   ├── conversation_memory.py # 20-msg sliding window
│   │   └── preference_memory.py # User preference load/persist/merge
│   ├── services/
│   │   ├── chat.py              # ChatService (non-agent completions)
│   │   ├── conversation_manager.py # Turn persistence + summarisation
│   │   └── openai_service.py    # OpenAIService wrapper
│   ├── telemetry/
│   │   └── logging.py           # Loguru setup
│   ├── websocket/
│   │   └── manager.py           # Socket.IO event handlers
│   └── main.py                  # FastAPI + Socket.IO ASGI app entry point
├── .env.example
├── Dockerfile
└── pyproject.toml
```

---

## Dependencies

Full list in `pyproject.toml`. Key packages:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥0.115.0 | HTTP framework |
| `uvicorn[standard]` | ≥0.34.0 | ASGI server |
| `langgraph` | ≥1.2.9 | Agent graph orchestration |
| `langchain-core` | ≥1.5.0 | Message types, base abstractions |
| `langgraph-checkpoint-mongodb` | ≥0.4.0 | MongoDB-backed LangGraph checkpointer |
| `openai` | ≥1.12.0 | OpenAI Python SDK |
| `langsmith` | ≥0.2.0 | LLM tracing |
| `motor` | ≥3.6.0 | Async MongoDB driver |
| `pymongo` | ≥4.7.0 | Sync MongoDB driver (checkpointer) |
| `python-socketio[asyncio-client]` | ≥5.11.0 | Socket.IO server |
| `httpx` | ≥0.27.0 | Async HTTP (MCP transport) |
| `PyJWT` | ≥2.9.0 | JWT verification |
| `pydantic-settings` | ≥2.7.0 | Env var configuration |
| `loguru` | ≥0.7.3 | Structured logging |
