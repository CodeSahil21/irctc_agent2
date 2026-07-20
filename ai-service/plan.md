# AI Service Build Plan

This document is the implementation roadmap for the Python AI service. The goal is to build a real orchestration layer, not another business-logic service. The AI service should stay focused on conversation, planning, tool execution, streaming, memory, and human approval.

## Core Principles

1. Keep authentication in the Node auth service.
2. Keep IRCTC business logic in the Node MCP service.
3. Keep the Python service as the orchestration layer only.
4. Verify the user identity before any planning or tool use.
5. Let the graph decide control flow, not the LLM alone.
6. Let the planner decide what is missing and what tool is needed next.
7. Let the scheduler decide sequential vs parallel execution.
8. Make tool execution generic and transport-agnostic.
9. Add human approval for destructive or money-moving actions.
10. Prefer small, testable slices over a large one-shot agent.

## Target Behavior

The AI service should:

- accept chat requests and WebSocket sessions from the frontend,
- verify the JWT from the auth service,
- create and maintain per-user conversation state,
- classify the user intent,
- extract entities and determine missing parameters,
- decide whether to ask a clarifying question or continue,
- build an execution plan,
- execute MCP tools through a generic MCP wrapper,
- stream progress updates and final answers,
- checkpoint state for resume/retry flows,
- request human approval when required,
- keep memory and preferences separate from short-lived chat state.

## Build Order

Follow this order. Do not skip ahead unless the earlier step is stable and covered by a test or a manual check.

### Phase 1: Chat and transport foundation

1. Finish the FastAPI app entrypoint.
2. Make `/health` return a simple service status.
3. Add `/chat` for normal HTTP requests.
4. Add `/ws` for streaming and interactive sessions.
5. Define a shared event format for the WebSocket layer.
6. Decide the minimal request shape for chat input and session resume.

What this phase should prove:

- the service starts,
- the frontend can connect,
- a message can enter the system,
- a simple response can leave the system.

### Phase 2: Authentication and user context

1. Read the JWT from the incoming request.
2. Verify the token locally using the auth service signing strategy.
3. Convert the verified claims into a small `CurrentUser` object.
4. Reject requests with missing or invalid tokens before any AI work.
5. Pass only minimal user context into the rest of the system.

What this phase should prove:

- no planning happens for an unauthenticated user,
- the user identity is stable across the request,
- the AI service never needs to call auth repeatedly during a single flow.

### Phase 3: Conversation state and checkpoints

1. Define the graph state shape.
2. Separate conversation state, user preferences, checkpoints, and tool cache.
3. Add checkpoint save and restore behavior.
4. Store message history in the conversation layer, not in the transport layer.
5. Make resume flows deterministic from saved state.

What this phase should prove:

- a conversation can continue after interruption,
- the current step is recoverable,
- state updates are explicit and inspectable.

### Phase 4: Planner and intent routing

1. Build a simple router that decides the next node.
2. Add a planner node that answers:
    - what is the user trying to do,
    - what inputs are missing,
    - which tool or tool group is needed next,
    - whether the flow needs human approval.
3. Keep the planner focused on decisions, not execution.
4. Add a slot-filling path for missing parameters.
5. Add a question-generation step for clarifying follow-ups.

What this phase should prove:

- the system can ask for missing station, date, train, quota, or class details,
- the planner can distinguish search, availability, fare, booking, cancellation, and reminder flows,
- the graph can pause and wait for the user instead of forcing a bad guess.

### Phase 5: Execution planner and scheduler

1. Convert planner output into a concrete execution plan.
2. Split the plan into sequential steps and parallel groups.
3. Add timeout and retry rules.
4. Add cancellation support for user aborts.
5. Keep concurrency decisions in code, not in free-form LLM output.

What this phase should prove:

- independent lookups can run in parallel,
- dependent steps stay sequential,
- the system can recover from transient tool failures.

### Phase 6: Generic MCP execution layer

1. Build a single `execute_tool` path.
2. Add session handling for the Node MCP server.
3. Inject user headers required by the MCP server.
4. Normalize responses into one internal shape.
5. Keep the AI service unaware of Node internals.

What this phase should prove:

- the AI service can call train search, fare, availability, booking, and reminder tools through one interface,
- the MCP layer can be swapped later without rewriting the graph,
- tool calls can be traced and replayed.

### Phase 7: Human approval flows

1. Mark risky tools as interrupt points.
2. Pause before book, cancel, update boarding point, or delete reminder actions.
3. Send an approval event to the frontend.
4. Resume only after an explicit user approval.
5. Make approval a graph state transition, not a one-off special case.

What this phase should prove:

- the system never books or cancels silently,
- the frontend can render approval prompts clearly,
- paused flows can resume without losing context.

### Phase 8: LLM integration and Claude API usage

1. Add a dedicated LLM client wrapper.
2. Keep model calls behind one interface.
3. Make structured outputs explicit for planner and router decisions.
4. Stream tokens through a separate streaming path.
5. Do not let the model directly call HTTP or MCP services.
6. Use the Claude API for reasoning, summarization, and tool selection where helpful.

What this phase should prove:

- prompts are contained and versionable,
- structured decisions are more reliable than raw text parsing,
- streaming and final responses are separated cleanly.

### Phase 9: Observability and debugging

1. Add structured logging.
2. Add trace events for graph nodes and tool calls.
3. Add metrics for latency, failures, retries, approvals, and interruptions.
4. Include request IDs and session IDs in logs.
5. Make every tool call explainable after the fact.

What this phase should prove:

- you can understand why a response happened,
- you can see where the graph branched,
- you can debug bad planning or tool failures without guessing.

### Phase 10: Tests and quality gates

1. Add unit tests for JWT verification, routing, planning, tool normalization, and memory helpers.
2. Add integration tests for `/chat`, `/health`, and `/ws`.
3. Add mock MCP tests for tool execution.
4. Add approval-flow tests.
5. Add regression tests for common user journeys.

What this phase should prove:

- the service can be changed safely,
- key flows keep working as the agent grows,
- planning bugs are caught before deployment.

## Recommended Implementation Sequence

If you want the shortest path to a useful agent, build in this order:

1. `/health`
2. `/chat`
3. WebSocket streaming
4. JWT verification
5. Current user extraction
6. Graph state and checkpoints
7. Planner node
8. Clarifying question flow
9. MCP client wrapper
10. Search and availability tools
11. Fare and route tools
12. Booking approval flow
13. Cancellation and reminder flows
14. Logging and tracing
15. Full test suite

## Suggested Graph Milestones

### Milestone A: Chat skeleton

- accept a message,
- echo a safe response,
- stream one event over WebSocket.

### Milestone B: Authenticated session

- verify JWT,
- load current user,
- attach session state.

### Milestone C: Planning

- detect user intent,
- identify missing slots,
- ask the right follow-up question.

### Milestone D: Tool execution

- call MCP tools through a generic executor,
- normalize results,
- return a clean answer.

### Milestone E: Multi-step orchestration

- search trains,
- check availability,
- fetch fare,
- build one combined answer.

### Milestone F: Risky action flow

- pause for approval,
- resume safely,
- confirm the action result.

## Principles Learned From the Codebase

These are the design lessons that fit the current repository:

- The Node auth service already owns login and user identity, so the Python service should never duplicate that logic.
- The Node MCP service already owns IRCTC-specific behavior, so the Python service should only orchestrate those tools.
- The MCP server is session-based, so the AI service should manage its own MCP session adapter.
- The app is already split into controller/service/repository style on the Node side, so the Python service should use similarly clear layers.
- The AI service should favor typed state and explicit events, because agents become hard to debug when everything is hidden in prompt text.

## Definition of Done

The AI service is in a good place when:

- a user can authenticate through the Node auth service,
- the frontend can talk to the Python AI service over HTTP or WebSocket,
- the AI service can verify identity and restore state,
- the planner can ask for missing information,
- the executor can call MCP tools reliably,
- approval flows work for risky operations,
- logs and traces explain every important branch,
- tests cover the major journeys.

## Working Rule

When adding a new feature, ask this sequence first:

1. Is this auth, business logic, or orchestration?
2. If it is auth, does it belong in the Node auth service?
3. If it is IRCTC logic, does it belong in the Node MCP service?
4. If it is planning, streaming, memory, or coordination, it belongs in the Python AI service.

That rule will keep the architecture clean as the agent grows.
