from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.models import ConversationDoc, ExecutionLogDoc, MessageDoc
from app.db.repositories.conversation_repo import (
    get_conversation,
    get_messages,
    get_recent_conversations,
    increment_turn,
    save_message,
    update_summary,
    upsert_conversation,
)
from app.db.repositories.execution_repo import save_execution_log
from app.memory.preference_memory import load_preferences_from_db, persist_preferences
from app.telemetry.logging import app_logger

_SUMMARIZE_EVERY = 10


class ConversationManager:
    def __init__(self, db: AsyncIOMotorDatabase, claude_service=None):
        self._db = db
        self._claude = claude_service  # optional — only needed for summarization


    async def open(
        self,
        conversation_id: str,
        user_email: str,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load existing conversation or create a new one.
        Loads the user's preferences from DB and attaches them to the returned
        doc under `preferences` so the caller can seed graph state with them.
        """
        prefs = await load_preferences_from_db(self._db, user_email)

        existing = await get_conversation(self._db, conversation_id)
        if existing:
            app_logger.info(
                "Conversation loaded | id={id} | turns={turns}",
                id=conversation_id,
                turns=existing.get("turn_count", 0),
            )
            existing["preferences"] = prefs
            return existing

        # New conversation
        doc = ConversationDoc(
            conversation_id=conversation_id,
            user_email=user_email,
            user_name=user_name,
        )
        await upsert_conversation(self._db, doc)
        app_logger.info("Conversation created | id={id}", id=conversation_id)
        result = doc.model_dump()
        result["preferences"] = prefs
        return result

    async def close(self, user_email: str, prefs: Optional[Dict[str, Any]] = None) -> None:
        """Persist any updated preferences for this user. No-op when none changed."""
        if prefs:
            await persist_preferences(self._db, user_email, prefs)

    # ── Context Building ──────────────────────────────────────────────

    async def build_context(
        self,
        conversation_id: str,
        window: int = 20,
    ) -> Dict[str, Any]:
        """
        Build a structured context dict from DB for injecting into the graph
        on conversation resume (user returns after days away).

        Returns:
          summary      — rolling summary of older turns
          messages     — recent N messages as LangChain BaseMessage list
          turn_count   — total turns so far
        """
        conv = await get_conversation(self._db, conversation_id)
        if not conv:
            return {"summary": None, "messages": [], "turn_count": 0}

        raw_messages = await get_messages(self._db, conversation_id, limit=window)
        messages = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
            for m in raw_messages
        ]

        return {
            "summary": conv.get("summary"),
            "messages": messages,
            "turn_count": conv.get("turn_count", 0),
        }


    async def save_turn(
        self,
        conversation_id: str,
        user_email: str,
        user_message: str,
        assistant_reply: str,
        intent: Optional[str],
        result: Dict[str, Any],
    ) -> None:
        """
        Persist one complete turn:
          1. Upsert conversation (sets title on first turn)
          2. Increment turn counter
          3. Save user message
          4. Save assistant message
          5. Save execution log
          6. Trigger summarization if threshold reached
        """
        try:
            await upsert_conversation(
                self._db,
                ConversationDoc(
                    conversation_id=conversation_id,
                    user_email=user_email,
                    user_name=result.get("user_name"),
                    title=user_message[:80],
                ),
            )
            await increment_turn(self._db, conversation_id)

            await save_message(
                self._db,
                MessageDoc(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message,
                    intent=intent,
                ),
            )

            if assistant_reply:
                await save_message(
                    self._db,
                    MessageDoc(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=assistant_reply,
                    ),
                )

            metrics = result.get("execution_metrics") or {}
            await save_execution_log(
                self._db,
                ExecutionLogDoc(
                    conversation_id=conversation_id,
                    turn=result.get("turn_count") or 0,
                    intent=intent,
                    user_goal=result.get("user_goal"),
                    tool_history=[dict(t) for t in (result.get("tool_history") or [])],
                    errors=result.get("errors") or [],
                    turn_start_time=metrics.get("turn_start_time"),
                    total_latency_ms=metrics.get("total_latency_ms"),
                    claude_calls=metrics.get("claude_calls"),
                    tools_called=metrics.get("tools_called"),
                ),
            )

            turn_count = result.get("turn_count") or 0
            if turn_count > 0 and turn_count % _SUMMARIZE_EVERY == 0:
                await self.summarize(conversation_id)

        except Exception as e:
            # Persistence must never break the agent response
            app_logger.error("save_turn failed: {error}", error=str(e), exc_info=True)


    async def summarize(self, conversation_id: str) -> Optional[str]:
        """
        Generate a rolling summary of the conversation using Claude.
        Replaces the previous summary — keeps context compact across many turns.
        No-ops if claude_service is not available.
        """
        if not self._claude:
            return None

        conv = await get_conversation(self._db, conversation_id)
        if not conv:
            return None

        # Fetch all messages for summarization (no window limit here)
        raw_messages = await get_messages(self._db, conversation_id, limit=200)
        if not raw_messages:
            return None

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in raw_messages
        )
        previous_summary = conv.get("summary") or ""

        prompt = (
            f"Previous summary:\n{previous_summary}\n\n"
            f"New conversation turns:\n{history_text}\n\n"
            "Write a concise updated summary (max 200 words) covering: "
            "what the user wanted, what was searched or booked, key travel details "
            "(stations, dates, train, class), and any pending actions. "
            "Write in third person. Be factual, no filler."
        )

        try:
            response = await self._claude.chat_raw(
                messages=[{"role": "user", "content": prompt}],
                system="You are a conversation summarizer for an IRCTC travel agent.",
                temperature=0.0,
                max_tokens=300,
            )
            summary = "".join(
                b.text for b in response.content
                if getattr(b, "type", None) == "text"
            )
            await update_summary(self._db, conversation_id, summary)
            app_logger.info("Conversation summarized | id={id}", id=conversation_id)
            return summary
        except Exception as e:
            app_logger.error("Summarization failed: {error}", error=str(e), exc_info=True)
            return None

    # ── Queries ───────────────────────────────────────────────────────

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[dict]:
        return await get_messages(self._db, conversation_id, limit=limit)

    async def get_recent(self, user_email: str, limit: int = 20) -> List[dict]:
        return await get_recent_conversations(self._db, user_email, limit=limit)
