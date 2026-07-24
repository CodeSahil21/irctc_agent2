# IRCTC AI Agent

A full-stack AI-powered travel assistant for Indian Railways. Users chat in natural language to search trains, check availability, compare fares, book and cancel tickets, set reminders, and manage passenger profiles — all through a conversational interface backed by live IRCTC data.

---

## Services at a Glance

| Service            | Tech                                              | Port | Role              |
| ------------------ | ------------------------------------------------- | ---- | ----------------- |
| `client`           | Next.js 16 · React 19 · Redux Toolkit · Socket.IO | 3000 | Chat UI           |
| `ai-service`       | FastAPI · LangGraph · OpenAI · MongoDB            | 8000 | AI orchestration  |
| `auth-service`     | Express 5 · Prisma · PostgreSQL · Redis · JWT     | 4000 | Auth & sessions   |
| `mcp_server_irctc` | Node.js · MCP SDK · Prisma · PostgreSQL           | 3001 | IRCTC tool server |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client (Next.js)                           │
│            REST  (/api/v1/agent)   ·   Socket.IO (real-time stream)     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────────┐
│                           ai-service  :8000                             │
│                                                                         │
│   FastAPI HTTP  ──►  LangGraph StateGraph  ──►  MCP Registry            │
│   Socket.IO     ──►  (4-node agent loop)   ──►  (tool execution)        │
│                              │                                          │
│           ┌──────────────────┼──────────────────┐                      │
│           │                  │                  │                      │
│      OpenAI LLM         MongoDB               LangSmith                │
│      (gpt-4o-mini)   (Motor + pymongo)        (tracing)                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  JSON-RPC 2.0  (Streamable HTTP)
┌──────────────────────────────▼──────────────────────────────────────────┐
│                       mcp_server_irctc  :3001                           │
│                                                                         │
│   19 MCP tools  ──►  PostgreSQL (Prisma)  ──►  Redis (session cache)   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         auth-service  :4000                             │
│                                                                         │
│   Express 5  ──►  Prisma / PostgreSQL  ──►  Redis  ──►  JWT (HS256)    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## LangGraph Agent Workflow

The core of `ai-service` is a 4-node `StateGraph` compiled in `app/graph/builder.py`. Every user message travels through this loop until a final answer is produced.

```mermaid
flowchart TD
    START([▶ START]) --> A

    A["🧠 agent_node\n─────────────────\n• Builds system prompt\n  with user context\n• Loads all live MCP\n  tool schemas\n• Calls OpenAI LLM\n• Emits tool_calls or\n  plain-text answer\n• Loop guard: MAX=8"]

    A -- "pending_tool_calls\n+ any destructive?" --> H

    A -- "pending_tool_calls\nnone destructive" --> T

    A -- "no tool calls\n+ reflection_required" --> R

    A -- "no tool calls\nno reflection" --> END1([⏹ END])

    H["🔐 human_approval_node\n─────────────────\n• Calls LangGraph interrupt()\n• Suspends graph &\n  checkpoints to MongoDB\n• Awaits Command(resume=…)\n• Normalises: yes/y/ok/\n  confirm → True"]

    H -- "confirmed = True" --> T

    H -- "confirmed = False\n(injects cancelled\nToolMessages)" --> A

    T["⚙️ tool_executor_node\n─────────────────\n• asyncio.gather all\n  pending_tool_calls\n• 15s per-tool timeout\n• Inline train ranking\n  (cheapest/fastest/\n  best_avail)\n• Persists history &\n  saved passengers\n• Appends to tool_history"]

    T -- "always" --> A

    R["🔍 reflection_node\n─────────────────\n• Fast path: skip LLM\n  if any tool failed\n• LLM quality check\n  (temp=0, max 300 tok)\n• reflect_on_results\n  function tool\n• Hard cap: 1 retry"]

    R -- "passed OR\nretries ≥ 1" --> END2([⏹ END])

    R -- "failed +\nretries < 1\n(injects feedback\ninto system prompt)" --> A

    style START fill:#22c55e,color:#fff,stroke:none
    style END1 fill:#ef4444,color:#fff,stroke:none
    style END2 fill:#ef4444,color:#fff,stroke:none
    style A fill:#3b82f6,color:#fff,stroke:#1d4ed8
    style H fill:#f59e0b,color:#fff,stroke:#b45309
    style T fill:#8b5cf6,color:#fff,stroke:#6d28d9
    style R fill:#06b6d4,color:#fff,stroke:#0e7490
```

### Routing Rules

| From                  | Condition                                | To                    |
| --------------------- | ---------------------------------------- | --------------------- |
| `agent_node`          | pending tool calls + any destructive     | `human_approval_node` |
| `agent_node`          | pending tool calls, none destructive     | `tool_executor_node`  |
| `agent_node`          | no pending calls + `reflection_required` | `reflection_node`     |
| `agent_node`          | no pending calls                         | `END`                 |
| `human_approval_node` | `confirmed = True`                       | `tool_executor_node`  |
| `human_approval_node` | `confirmed = False`                      | `agent_node`          |
| `tool_executor_node`  | always                                   | `agent_node`          |
| `reflection_node`     | `reflection_passed = True`               | `END`                 |
| `reflection_node`     | failed + `retries >= 1`                  | `END`                 |
| `reflection_node`     | failed + `retries < 1`                   | `agent_node`          |

---

## Agent State (`TravelState`)

`app/graph/state.py` — the full TypedDict that flows through every node.

```mermaid
classDiagram
    class TravelState {
        +List~BaseMessage~ messages
        +str conversation_id
        +int turn_count

        +str user_email
        +str user_name

        +UserPreferences user_preferences

        +List~Dict~ pending_tool_calls
        +int agent_loop_count

        +List~ToolCall~ tool_history
        +Dict persistent_results

        +bool reflection_required
        +bool reflection_passed
        +str reflection_feedback
        +int reflection_retries

        +bool confirmation_required
        +str confirmation_prompt
        +bool confirmed

        +List~str~ errors
        +str pending_intent
        +Dict collected_slots

        +ExecutionMetrics execution_metrics

        +List search_results
        +List ranked_results
        +Dict selected_train
        +Dict availability
        +Dict fare
        +Dict booking
        +List passengers
    }

    class UserPreferences {
        +str preferred_class
        +str preferred_quota
        +str berth_preference
        +bool senior_citizen
    }

    class ToolCall {
        +str id
        +str tool
        +Dict args
        +Any result
        +str status
        +float latency_ms
    }

    class ExecutionMetrics {
        +float turn_start_time
        +int tools_called
        +float total_latency_ms
        +int llm_calls
    }

    TravelState --> UserPreferences
    TravelState --> ToolCall
    TravelState --> ExecutionMetrics
```

---

## MCP Tool Catalogue

The `mcp_server_irctc` exposes **19 tools** over the MCP Streamable HTTP protocol. The `ai-service` discovers them at startup and feeds their OpenAI-formatted schemas directly to the LLM every turn.

```mermaid
graph LR
    subgraph PUBLIC["📖 Public Tools (read-only)"]
        ST[search_trains]
        CA[check_availability]
        GF[get_fare]
        GSM[get_seat_map]
        GBP[get_boarding_points]
        GLS[get_live_status]
        GP[get_platform]
        GTD[get_train_details]
        GRD[get_reference_data]
        FS[find_station]
        RT[recommend_trains]
    end

    subgraph USER["🔐 User Tools (require auth)"]
        BT[book_ticket 🔴]
        CT[cancel_ticket 🔴]
        TB[track_booking]
        GBH[get_booking_history]
        UB[update_booking 🔴]
        MR[manage_reminder 🔴*]
        ASP[add_saved_passenger 🔴]
        GSP[get_saved_passengers]
    end

    subgraph AGENT["🤖 ai-service"]
        MCPReg[MCP Registry]
    end

    MCPReg --> ST
    MCPReg --> CA
    MCPReg --> GF
    MCPReg --> GSM
    MCPReg --> GBP
    MCPReg --> GLS
    MCPReg --> GP
    MCPReg --> GTD
    MCPReg --> GRD
    MCPReg --> FS
    MCPReg --> RT
    MCPReg --> BT
    MCPReg --> CT
    MCPReg --> TB
    MCPReg --> GBH
    MCPReg --> UB
    MCPReg --> MR
    MCPReg --> ASP
    MCPReg --> GSP
```

> 🔴 = **destructive** — requires human approval via `human_approval_node` before execution.  
> \* `manage_reminder` is only destructive when `action = "delete"`.

### Typical Booking Flow

```mermaid
sequenceDiagram
    actor User
    participant Agent as agent_node
    participant Exec as tool_executor_node
    participant Appr as human_approval_node
    participant MCP as mcp_server_irctc

    User->>Agent: "Book a ticket from Delhi to Mumbai tomorrow in 3A"
    Agent->>Exec: find_station("Delhi"), find_station("Mumbai")
    Exec->>MCP: find_station x2 (concurrent)
    MCP-->>Exec: NDLS, BCT
    Exec-->>Agent: station codes

    Agent->>Exec: recommend_trains(NDLS, BCT, date, 3A)
    Exec->>MCP: recommend_trains
    MCP-->>Exec: ranked train list
    Exec-->>Agent: trains (ranked by cheapest)

    Agent->>User: "Here are the top trains. Which one?"
    User->>Agent: "12951 Rajdhani"

    Agent->>Exec: check_availability(12951, 3A, GN, date)
    Exec->>MCP: check_availability
    MCP-->>Exec: AVBL-42
    Exec-->>Agent: available

    Note over Agent: All slots collected — call book_ticket
    Agent->>Appr: book_ticket(12951, date, NDLS, BCT, 3A, GN, passengers)
    Note over Appr: interrupt() — graph suspends, checkpoint saved

    Appr->>User: "Confirm booking Rajdhani on 2026-07-25, 3A, ₹1850? (yes/no)"
    User->>Appr: "yes"
    Note over Appr: Command(resume="yes") — graph resumes

    Appr->>Exec: book_ticket (confirmed)
    Exec->>MCP: book_ticket
    MCP-->>Exec: PNR 1234567890
    Exec-->>Agent: booking confirmed

    Agent->>User: "Booked! PNR 1234567890, Rajdhani, 25 Jul, 3A."
```

---

## Memory Architecture

```mermaid
flowchart TD
    subgraph TURN["Per-Turn (cleared each new user message)"]
        TH[tool_history\nList of ToolCall records]
        PTH[pending_tool_calls\nEmitted by agent_node]
        ERR[errors\nFailed tool messages]
        ALC[agent_loop_count\nReset to 0 on final answer]
    end

    subgraph CONV["Per-Conversation (survives turns via LangGraph checkpoint)"]
        MSG["messages\nfull conversation history\n(add_messages reducer)"]
        CS[collected_slots\nMid-booking slot values]
        PI[pending_intent\ne.g. book_ticket]
        PR["persistent_results\n├─ get_booking_history\n└─ get_saved_passengers"]
        UP[user_preferences\npreferred class · quota · berth]
    end

    subgraph DB["MongoDB Collections"]
        CHK[(langgraph_checkpoints\nMongoDBSaver)]
        CONVD[(conversations)]
        MSGD[(messages)]
        PREFD[(user_preferences)]
        EXECD[(execution_logs)]
    end

    CONV -->|"ainvoke config\nthread_id = conversation_id"| CHK
    CHK -->|"auto-load on resume\nor interrupt"| CONV

    CONVD --- MSGD
    CONVD --- EXECD

    MSG -->|"ConversationManager\nsave_turn()"| CONVD
    UP -->|"ConversationManager\nclose()"| PREFD
    TH -->|"ConversationManager\nsave_turn()"| EXECD
```

### Sliding Window

`conversation_memory.py` applies a **20-message sliding window** before every LLM call.  
The first `HumanMessage` is always anchored; `ToolMessage` entries are excluded from the window (they surface via the context block in the system prompt instead).

### Rolling Summary

`ConversationManager.summarize()` runs an LLM call (max 200 words) every 10 turns and stores it in the `conversations` collection. It is prepended to the context for long-running conversations.

---

## MCP Layer Internals

```mermaid
flowchart LR
    subgraph AISERVICE["ai-service"]
        TEN[tool_executor_node]
        REG[MCPToolRegistry\n• validate args\n• strip hallucinated fields\n• check required fields]
        CLI[MCPClient\n• per-user sessions\n• 3 retries\n• exp. backoff 0.5→1→2s]
        TRANS[MCPTransport\n• httpx async\n• JSON-RPC 2.0\n• POST /mcp\n• SSE response]
        DISC[MCPDiscovery\n• tools/list at startup\n• 5 retry attempts\n• OpenAI schema format]
        SESS[MCPSession\n• per-user email\n• mcp-session-id header\n• health metrics]
    end

    subgraph MCPSRV["mcp_server_irctc :3001"]
        MCP_EP["POST /mcp\n(MCP SDK StreamableHTTP)"]
        TOOLS[19 Tool Handlers]
        PG[(PostgreSQL\nPrisma)]
        REDIS[(Redis\nsession cache)]
    end

    TEN --> REG --> CLI --> TRANS
    CLI --> SESS
    TRANS -->|"x-user-email\nx-user-name\nmcp-session-id"| MCP_EP
    DISC -->|"tools/list\nat startup"| MCP_EP
    MCP_EP --> TOOLS
    TOOLS --> PG
    TOOLS --> REDIS
```

---

## Train Ranking (`app/graph/ranking.py`)

Applied inline in `tool_executor_node` after every `search_trains` or `recommend_trains` response. Pure Python — no LLM involved.

```mermaid
flowchart TD
    UT[User message text] --> DM{detect_mode}

    DM -->|"fast · quick · shortest\ndirect · less time"| F["fastest\n→ sort by durationMins ASC"]
    DM -->|"available · seats\nconfirm · confirmed"| B["best_avail\n→ sort by seats DESC\n   then fare ASC"]
    DM -->|"cheap · budget\nlow fare · economical\n(or no keyword)"| C["cheapest (default)\n→ sort by fare ASC"]

    F --> OUT[Ranked train list\nstored in ranked_results]
    B --> OUT
    C --> OUT
```

Fields parsed from MCP responses: `durationMins` / `duration` (string `"2h30m"` or `"2:30"`), `fare.amount` / `fare.total` / `fare.breakdown.total`, `availability.count` / `availability.available`.

---

## Destructive Tool Gate

Six tools require explicit human confirmation. The decision is codified in `app/graph/tool_meta.py` — the **only file** in the codebase where tool names are hardcoded.

```mermaid
flowchart TD
    AT["agent_node emits tool_call(s)"] --> ID{is_destructive?}

    ID -->|"No"| TE[tool_executor_node\nruns immediately]
    ID -->|"Yes"| HA[human_approval_node\ninterrupt → suspend graph\nsave checkpoint to MongoDB]

    HA --> CP["Show confirmation prompt\ne.g. Confirm booking Rajdhani\non 2026-07-25, 3A, ₹1850?"]
    CP --> UR{User reply}

    UR -->|"yes · y · confirm\nok · proceed · sure\ngo ahead · yep · yeah"| RUN[Resume → tool_executor_node\nrun the tool]
    UR -->|"anything else"| CAN["Resume → agent_node\ninject cancelled ToolMessages\nrelay cancellation to user"]

    subgraph DT["Destructive Tools"]
        BK["book_ticket — always"]
        CX["cancel_ticket — always"]
        UB["update_booking — when status\nor newBoardingStation present"]
        MR["manage_reminder — when action='delete'"]
        AP["add_saved_passenger — always"]
        DP["delete_saved_passenger — always"]
    end
```

---

## Auth Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Client as Next.js Client
    participant Auth as auth-service :4000
    participant AI as ai-service :8000

    Browser->>Client: Visit app
    Client->>Auth: POST /auth/login {email, password}
    Auth->>Auth: bcrypt verify password
    Auth->>Auth: Sign JWT (HS256, shared secret)
    Auth-->>Client: Set-Cookie: token=<jwt>  +  Redis session

    Client->>AI: POST /api/v1/agent\n{message, user_email, ...}\nAuthorization: Bearer <jwt>
    AI->>AI: verify_jwt(token, JWT_SECRET)
    AI->>AI: extract_user_from_token()
    AI-->>Client: Agent response
```

> The `JWT_SECRET` is shared between `auth-service` and `ai-service`. Both services must have identical values configured.

---

## Real-Time Streaming (Socket.IO)

```mermaid
sequenceDiagram
    participant UI as Next.js UI
    participant SIO as Socket.IO Manager\n(ai-service)
    participant Graph as LangGraph Agent

    UI->>SIO: connect()
    UI->>SIO: emit("query:send", {message, conversation_id, user_email})
    SIO->>Graph: agent_graph.ainvoke(initial_state, config)

    loop Token streaming
        Graph-->>SIO: stream event (token)
        SIO-->>UI: emit("response:token", {content})
    end

    alt Approval required
        Graph-->>SIO: interrupt — confirmation_prompt
        SIO-->>UI: emit("response:confirm", {prompt})
        UI->>SIO: emit("query:resume", {resume_value: "yes"})
        SIO->>Graph: ainvoke(Command(resume="yes"), config)
    end

    Graph-->>SIO: final state
    SIO-->>UI: emit("response:done", {message, search_results, booking, ...})
```

---

## Startup Sequence

```mermaid
flowchart TD
    S1["1. LangSmith\ninitialise tracing\nwrap OpenAI client"]
    S2["2. OpenAIService\nAsyncOpenAI client\ngpt-4o-mini default"]
    S3["3. MCPTransport + MCPClient\nhttpx async · connect()"]
    S4["4. MCPDiscovery\ntools/list · 5 retry attempts\nnormalise to OpenAI schema"]
    S5["5. MCPToolRegistry\nwire client + discovery cache"]
    S6["6. MongoDB\nMotor async client\nsetup indexes: conversations\npreferences · executions"]
    S7["7. MongoDBSaver\nLangGraph checkpoint store\npymongo sync (thread executor)"]
    S8["8. create_agent_graph()\nStateGraph compile\ncheckpointer wired"]
    S9["9. ConversationManager\nDB + LLM service"]
    S10["10. Socket.IO Manager\nwire agent graph\n+ conversation manager"]

    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8 --> S9 --> S10
    S10 --> READY["✅ Application ready\nFastAPI + Socket.IO ASGI"]
```

---

## Database Models

```mermaid
erDiagram
    ConversationDoc {
        string conversation_id PK
        string user_email
        string user_name
        string title
        string summary
        int    turn_count
        datetime created_at
        datetime updated_at
    }

    MessageDoc {
        string conversation_id FK
        string role
        string content
        string intent
        datetime created_at
    }

    UserPreferenceDoc {
        string user_email PK
        string preferred_class
        string preferred_quota
        string berth_preference
        bool   senior_citizen
        datetime updated_at
    }

    ExecutionLogDoc {
        string conversation_id FK
        int    turn
        string intent
        string user_goal
        list   tool_history
        list   errors
        float  total_latency_ms
        int    llm_calls
        int    tools_called
        datetime created_at
    }

    ConversationDoc ||--o{ MessageDoc : "has messages"
    ConversationDoc ||--o{ ExecutionLogDoc : "has execution logs"
    UserPreferenceDoc ||--o| ConversationDoc : "loaded at open()"
```

> MongoDB collections: `conversations`, `messages`, `user_preferences`, `execution_logs`, `langgraph_checkpoints` (LangGraph-managed).

---

## API Reference

Base path: `/api/v1`

### Health

| Method | Path      | Description                                      |
| ------ | --------- | ------------------------------------------------ |
| `GET`  | `/health` | Liveness probe — returns `{status, environment}` |

### Chat

| Method | Path           | Description                                                              |
| ------ | -------------- | ------------------------------------------------------------------------ |
| `POST` | `/chat`        | Non-streaming LLM completion via `ChatService`                           |
| `POST` | `/chat/stream` | Token-by-token SSE stream, emits `{"content": token}` + `{"done": true}` |
| `POST` | `/agent`       | Run the full LangGraph agent (see below)                                 |

**`POST /agent` — Request**

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

Send `"resume": true` with `"resume_value": "yes"` (or `"no"`) to resume a graph suspended at a human approval gate.

**`POST /agent` — Response**

```json
{
  "message":             "Here are trains on that route…",
  "intent":              "search_trains",
  "travel_context":      { "from_station": "NDLS", "to_station": "BCT", "date": "2026-07-25" },
  "search_results":      [...],
  "selected_train":      null,
  "availability":        null,
  "fare":                null,
  "booking":             null,
  "confirmation_required": false,
  "confirmation_prompt": null,
  "interrupted":         false,
  "errors":              []
}
```

When `"interrupted": true`, the graph is paused at a human approval gate. Re-send with `"resume": true`.

### Conversations

| Method | Path                            | Description                               |
| ------ | ------------------------------- | ----------------------------------------- |
| `GET`  | `/conversations/{id}/messages`  | Message history (default limit: 50)       |
| `GET`  | `/conversations/{id}/context`   | Summary + recent messages for resume      |
| `GET`  | `/conversations/user/{email}`   | List conversations for a user (limit: 20) |
| `POST` | `/conversations/{id}/summarize` | Trigger rolling LLM summary               |

### Socket.IO Events

| Direction       | Event              | Payload                                             |
| --------------- | ------------------ | --------------------------------------------------- |
| Client → Server | `query:send`       | `{message, conversation_id, user_email, user_name}` |
| Client → Server | `query:resume`     | `{conversation_id, resume_value}`                   |
| Server → Client | `response:token`   | `{content: "<token>"}`                              |
| Server → Client | `response:confirm` | `{prompt: "<confirmation question>"}`               |
| Server → Client | `response:done`    | Full structured agent response                      |
| Server → Client | `response:error`   | `{error: "<message>"}`                              |

---

## Error Handling

| Exception                     | HTTP Status | Trigger                           |
| ----------------------------- | ----------- | --------------------------------- |
| `ValidationException`         | 400         | Malformed request                 |
| `AuthenticationException`     | 401         | Invalid OpenAI API key            |
| `RateLimitException`          | 429         | OpenAI rate limit                 |
| `ModelProviderException`      | 502         | Generic OpenAI API error          |
| `ServiceUnavailableException` | 503         | Connection timeout, quota/billing |

Raw SDK messages and stack traces are never forwarded to clients.

---

## Project Structure

```
irctc_agent2/
├── client/                         # Next.js 16 chat UI
│   ├── app/                        # App Router pages
│   ├── components/                 # React components
│   ├── store/                      # Redux Toolkit slices
│   ├── hooks/                      # Custom React hooks
│   └── lib/                        # API clients, socket setup
│
├── ai-service/                     # FastAPI + LangGraph orchestration
│   └── app/
│       ├── api/                    # HTTP routes (chat, agent, conversations)
│       ├── auth/                   # JWT verification, CurrentUser
│       ├── config/                 # Pydantic settings, constants
│       ├── core/                   # Exceptions, handlers, lifespan
│       ├── db/                     # MongoDB models + repositories
│       ├── graph/
│       │   ├── builder.py          # StateGraph compilation
│       │   ├── edges.py            # Conditional routing functions
│       │   ├── ranking.py          # Deterministic train ranking
│       │   ├── state.py            # TravelState TypedDict
│       │   ├── tool_meta.py        # DESTRUCTIVE_TOOLS registry
│       │   └── nodes/
│       │       ├── agent_node.py            # LLM decision node
│       │       ├── tool_executor_node.py    # Concurrent MCP execution
│       │       ├── human_approval_node.py   # Interrupt/approval gate
│       │       └── reflection_node.py       # Quality-check pass
│       ├── mcp/                    # Transport, client, discovery, registry
│       ├── memory/                 # Checkpoints, context builder, preferences
│       ├── services/               # ChatService, ConversationManager, OpenAIService
│       ├── telemetry/              # Loguru logging
│       ├── websocket/              # Socket.IO event handlers
│       └── main.py                 # ASGI entry point
│
├── services/
│   ├── auth-service/               # Express 5 + Prisma + PostgreSQL + Redis
│   │   ├── src/
│   │   │   ├── controllers/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── middleware/
│   │   │   ├── routes/
│   │   │   └── utils/
│   │   └── prisma/
│   │
│   └── mcp_server_irctc/           # MCP SDK + 19 IRCTC tools
│       ├── src/
│       │   ├── tools/              # 19 MCP tool handlers
│       │   ├── services/
│       │   ├── repositories/
│       │   ├── types/
│       │   └── utils/
│       └── prisma/
```

---

## Tech Stack

```mermaid
mindmap
  root((IRCTC AI Agent))
    Client
      Next.js 16
      React 19
      Redux Toolkit
      Socket.IO Client
      Tailwind CSS 4
      TypeScript 5
    ai-service
      FastAPI 0.115+
      LangGraph 1.2.9+
      LangChain Core 1.5+
      OpenAI SDK 1.12+
      LangSmith 0.2+
      MongoDB Motor 3.6+
      pymongo 4.7+
      python-socketio 5.11+
      httpx 0.27+
      PyJWT 2.9+
      pydantic-settings 2.7+
      Loguru 0.7+
    auth-service
      Express 5
      Prisma 7 ORM
      PostgreSQL
      Redis ioredis
      bcrypt
      jsonwebtoken
      TypeScript 7
    mcp-server
      MCP SDK 1.29+
      Express 5
      Prisma 7 ORM
      PostgreSQL
      Redis ioredis
      TypeScript 5
      Zod 4
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB (local or `MONGO_URL` env)
- PostgreSQL (for auth-service and mcp_server_irctc)
- Redis (for auth-service and mcp_server_irctc)

### 1 — MCP Server

```bash
cd services/mcp_server_irctc
cp .env.example .env        # fill DATABASE_URL, REDIS_URL
npm install
npm run db:setup            # generate + migrate + seed
npm run dev                 # :3001
```

### 2 — Auth Service

```bash
cd services/auth-service
cp .env.example .env        # fill DATABASE_URL, REDIS_URL, JWT_SECRET
npm install
npm run db:setup
npm run dev                 # :4000
```

### 3 — AI Service

```bash
cd ai-service
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# Required: OPENAI_API_KEY (sk-...), JWT_SECRET (match auth-service)
# Optional: MCP_SERVER_URL, MONGO_URL, LANGSMITH_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: `http://localhost:8000/docs` (disabled in `production` env).

### 4 — Client

```bash
cd client
cp .env.example .env        # fill NEXT_PUBLIC_AI_SERVICE_URL
npm install
npm run dev                 # :3000
```

---

## Configuration

### ai-service (`ai-service/.env`)

| Variable               | Default                     | Required | Description                   |
| ---------------------- | --------------------------- | -------- | ----------------------------- |
| `OPENAI_API_KEY`       | —                           | **Yes**  | Must start with `sk-`         |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o-mini`               | No       | OpenAI model                  |
| `JWT_SECRET`           | `change-me`                 | **Yes**  | Shared with auth-service      |
| `JWT_ALGORITHM`        | `HS256`                     | No       | JWT algorithm                 |
| `MCP_SERVER_URL`       | `http://localhost:3001`     | No       | MCP server base URL           |
| `MCP_SERVER_TIMEOUT`   | `30.0`                      | No       | Per-request timeout (seconds) |
| `MONGO_URL`            | `mongodb://localhost:27017` | No       | MongoDB connection string     |
| `MONGO_DB`             | `irctc_ai`                  | No       | Database name                 |
| `APP_ENV`              | `development`               | No       | `development` / `production`  |
| `DEBUG`                | `false`                     | No       | Enables hot reload + API docs |
| `LOG_LEVEL`            | `INFO`                      | No       | Loguru level                  |
| `LANGSMITH_TRACING`    | `false`                     | No       | Enable LangSmith tracing      |
| `LANGSMITH_API_KEY`    | —                           | No       | Required if tracing enabled   |
| `LANGSMITH_PROJECT`    | `default`                   | No       | LangSmith project name        |

### Docker

Each service ships a `Dockerfile`. The MCP server also has a `docker-compose.yml` for running with PostgreSQL and Redis together.

```bash
# ai-service
docker build -t ai-service ./ai-service
docker run --env-file ai-service/.env -p 8000:8000 ai-service
```

---

## Key Design Decisions

**Single decision node** — `agent_node` replaces what used to be separate intent, slot-filler, planner, and response nodes. The LLM reads live MCP tool schemas every turn and decides entirely on its own what to call. This means adding a new read-only MCP tool requires zero changes to the Python code.

**Intent gate in the system prompt** — the prompt includes an explicit `INTENT GATE` section with labelled examples of what phrases should and should not trigger mutating tools. This prevents the model from pre-emptively booking or saving passengers when the user is just browsing.

**Slot-filling in state** — `pending_intent` and `collected_slots` survive in the LangGraph checkpoint across turns. When the user answers a follow-up question ("Kevin, 22, MALE"), `agent_node` re-reads those fields and continues from where it left off rather than starting over.

**Human approval via LangGraph interrupt** — destructive calls do not go through a custom gate node that polls a flag. They use `interrupt()`, which suspends the graph execution, serialises the full state to MongoDB, and returns control to the HTTP handler. The graph resumes on the next HTTP request with `Command(resume=value)`. This means the approval is durable across process restarts.

**Deterministic ranking** — train ranking happens in pure Python inside `tool_executor_node`, never by asking the LLM to sort. This keeps results consistent and avoids burning tokens on ordering.

**Persistent results** — `get_booking_history` and `get_saved_passengers` are cached in `persistent_results` and injected into the system prompt context block. The LLM is explicitly told not to call these tools again unless the user asks to refresh. This cuts round-trips on common follow-up questions.

**Reflection hard cap** — the reflection node is gated on `reflection_retries < 1`. At most one LLM quality-check call and one retry happen per turn. Reflection failures are always open — if the checker itself throws, `reflection_passed = True` so the original answer is returned.

---

## MCP Reference Values

| Class | Name                | Quota | Name            |
| ----- | ------------------- | ----- | --------------- |
| `SL`  | Sleeper             | `GN`  | General         |
| `3A`  | AC 3 Tier           | `LD`  | Ladies          |
| `2A`  | AC 2 Tier           | `TQ`  | Tatkal          |
| `1A`  | AC First Class      | `PT`  | Premium Tatkal  |
| `CC`  | AC Chair Car        | `HO`  | Higher Official |
| `EC`  | Executive Chair Car | `SS`  | Senior Citizen  |
| `2S`  | Second Sitting      |       |                 |
| `VS`  | Vistadome AC        |       |                 |

**Berth preferences:** `LB` Lower · `MB` Middle · `UB` Upper · `SL` Side Lower · `SUB` Side Upper · `WS` Window Seat

**Booking statuses:** `PENDING` · `BOOKED` · `RAC` · `WL` · `CANCELLED` · `FAILED`

**Reminder types:** `JOURNEY` · `PNR` · `BOOKING`

---
