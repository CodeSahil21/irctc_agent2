# IRCTC Assist — AI Agent Chat UI

A Next.js 14 (App Router) + TypeScript chat interface for an IRCTC AI agent,
wired to a Socket.IO backend for real-time, streaming responses.

## Folder structure

```
irctc-ai-agent/
├─ app/                        # Next.js App Router
│  ├─ layout.tsx               # Root layout, fonts, metadata
│  ├─ page.tsx                 # Mounts <ChatWindow />
│  └─ globals.css              # Theme tokens, base styles
│
├─ components/
│  ├─ chat/
│  │  ├─ ChatWindow.tsx         # Composition root: wires useChat -> UI
│  │  ├─ ChatHeader.tsx         # Route/title bar + connection status
│  │  ├─ ConnectionStatus.tsx   # Signal-light socket state indicator
│  │  ├─ MessageList.tsx        # Scroll container + auto-scroll
│  │  ├─ MessageBubble.tsx      # Single message (ticket-stub styling)
│  │  ├─ MessageInput.tsx       # Composer + quick-prompt chips
│  │  ├─ TypingIndicator.tsx    # Agent "typing" state
│  │  └─ attachments/
│  │     ├─ PnrStatusCard.tsx   # Structured PNR status render
│  │     └─ TrainListCard.tsx   # Structured train search render
│  └─ ui/
│     ├─ Avatar.tsx
│     └─ Badge.tsx
│
├─ hooks/
│  ├─ useSocket.ts              # Connection lifecycle + connection state
│  ├─ useChat.ts                # Message state, send/receive orchestration
│  └─ useAutoScroll.ts          # Pins list to bottom unless user scrolls up
│
├─ lib/
│  ├─ socket/
│  │  ├─ socketClient.ts        # Typed singleton socket.io-client instance
│  │  └─ events.ts              # Event name constants
│  └─ utils/
│     ├─ cn.ts                  # classnames helper
│     └─ formatTime.ts          # Timestamp formatting
│
├─ types/
│  ├─ chat.ts                   # ChatMessage, attachments, roles
│  └─ socket.ts                 # Client<->Server event contract
│
├─ server/
│  └─ socket-server.ts          # Mock agent backend (swap for your real one)
│
├─ .env.example
├─ tailwind.config.ts
└─ package.json
```

## Design notes

- **Theme**: dark "departure board" aesthetic — deep navy background, amber
  signal accent, monospace display type for headers/labels, dashed/perforated
  edges on message bubbles evoking a ticket stub.
- **Signature element**: messages render as ticket stubs; PNR/train results
  render as structured attachment cards rather than plain text, so the agent
  reads like a real booking assistant, not a generic chatbot.
- **Connection state** is always visible (top-right signal light) since a
  real-time agent app should never leave the user guessing if it's live.

## Architecture

- `types/socket.ts` defines the **only** contract between frontend and
  backend (`ClientToServerEvents` / `ServerToClientEvents`). Swap
  `server/socket-server.ts` for a real agent backend without touching the UI,
  as long as it honors that contract.
- `useSocket` owns connection lifecycle (connect/reconnect/disconnect).
- `useChat` owns message state and translates socket events into
  `ChatMessage[]`, including token-by-token streaming via `message:chunk`.
- All components are presentational and receive data/handlers as props —
  no component reaches into the socket directly except via the hooks.

## Running locally

```bash
npm install

# terminal 1 — mock agent backend (Socket.IO on :4000)
npm run server

# terminal 2 — Next.js app (on :3000)
npm run dev
```

Copy `.env.example` to `.env.local` and adjust `NEXT_PUBLIC_SOCKET_URL` if
your backend runs elsewhere.

## Wiring a real agent backend

Implement a Socket.IO server (or a thin adapter in front of your existing
agent/LLM service) that:

1. Listens for `query:send` → `{ id, content }`
2. Emits `query:ack` → `{ id }` once received
3. Emits `agent:typing` → `{ isTyping: true }` while working
4. Streams `message:chunk` → `{ id, delta }` per token/segment (optional —
   skip straight to step 5 if you don't stream)
5. Emits `message:complete` → `{ message: ChatMessage }` with the final
   message, optionally including a `pnr_status` or `train_list` attachment
6. Emits `message:error` → `{ id, error }` on failure

No other frontend changes are required.
