import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .config import get_settings


def _db() -> sqlite3.Connection:
    settings = get_settings()
    connection = sqlite3.connect(settings.vector_db)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(connection)
    return connection


def _ensure_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_facts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            category TEXT NOT NULL DEFAULT 'general',
            fact_key TEXT NOT NULL,
            fact_value TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL DEFAULT 'conversation',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'default',
            summary TEXT NOT NULL,
            key_topics TEXT NOT NULL DEFAULT '[]',
            message_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preferences_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS learned_patterns (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            pattern_type TEXT NOT NULL DEFAULT 'query',
            pattern TEXT NOT NULL,
            response_hint TEXT NOT NULL DEFAULT '',
            frequency INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_facts(user_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_facts(category)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_summary_chat ON conversation_summaries(chat_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_patterns_user ON learned_patterns(user_id)")


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class ConversationMemory:
    def __init__(self, user_id: str = "default", chat_id: str = ""):
        self.user_id = user_id
        self.chat_id = chat_id

    def store_fact(self, category: str, key: str, value: str, confidence: float = 1.0, source: str = "conversation") -> None:
        fact_id = uuid4().hex
        now = utc_now()
        with _db() as conn:
            existing = conn.execute(
                "SELECT id FROM memory_facts WHERE user_id = ? AND category = ? AND fact_key = ?",
                (self.user_id, category, key),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE memory_facts SET fact_value = ?, confidence = ?, updated_at = ? WHERE id = ?",
                    (value, confidence, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO memory_facts (id, user_id, category, fact_key, fact_value, confidence, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (fact_id, self.user_id, category, key, value, confidence, source, now, now),
                )

    def recall_facts(self, category: str = "", limit: int = 20) -> list[dict]:
        with _db() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM memory_facts WHERE user_id = ? AND category = ? ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                    (self.user_id, category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memory_facts WHERE user_id = ? ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                    (self.user_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def search_facts(self, query: str, limit: int = 10) -> list[dict]:
        query_words = set(re.findall(r"\w{3,}", query.lower()))
        if not query_words:
            return []
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_facts WHERE user_id = ? ORDER BY updated_at DESC LIMIT 200",
                (self.user_id,),
            ).fetchall()
        results = []
        for row in rows:
            text = f"{row['fact_key']} {row['fact_value']}".lower()
            matches = sum(1 for w in query_words if w in text)
            if matches > 0:
                score = matches / len(query_words)
                results.append((score, dict(row)))
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:limit]]

    def store_summary(self, summary: str, key_topics: list[str], message_count: int) -> None:
        summary_id = uuid4().hex
        with _db() as conn:
            conn.execute(
                "INSERT INTO conversation_summaries (id, chat_id, user_id, summary, key_topics, message_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (summary_id, self.chat_id, self.user_id, summary, json.dumps(key_topics), message_count, utc_now()),
            )

    def get_recent_summaries(self, limit: int = 5) -> list[dict]:
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_summaries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (self.user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def store_preference(self, key: str, value: str) -> None:
        with _db() as conn:
            row = conn.execute("SELECT preferences_json FROM user_preferences WHERE user_id = ?", (self.user_id,)).fetchone()
            prefs = json.loads(row["preferences_json"]) if row else {}
            prefs[key] = value
            conn.execute(
                "INSERT INTO user_preferences (user_id, preferences_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET preferences_json = excluded.preferences_json, updated_at = excluded.updated_at",
                (self.user_id, json.dumps(prefs), utc_now()),
            )

    def get_preferences(self) -> dict:
        with _db() as conn:
            row = conn.execute("SELECT preferences_json FROM user_preferences WHERE user_id = ?", (self.user_id,)).fetchone()
        return json.loads(row["preferences_json"]) if row else {}

    def learn_pattern(self, pattern_type: str, pattern: str, response_hint: str = "") -> None:
        with _db() as conn:
            existing = conn.execute(
                "SELECT id, frequency FROM learned_patterns WHERE user_id = ? AND pattern = ?",
                (self.user_id, pattern),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE learned_patterns SET frequency = frequency + 1 WHERE id = ?",
                    (existing["id"],),
                )
            else:
                conn.execute(
                    "INSERT INTO learned_patterns (id, user_id, pattern_type, pattern, response_hint, frequency, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                    (uuid4().hex, self.user_id, pattern_type, pattern, response_hint, utc_now()),
                )

    def get_learned_patterns(self, pattern_type: str = "", limit: int = 20) -> list[dict]:
        with _db() as conn:
            if pattern_type:
                rows = conn.execute(
                    "SELECT * FROM learned_patterns WHERE user_id = ? AND pattern_type = ? ORDER BY frequency DESC LIMIT ?",
                    (self.user_id, pattern_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learned_patterns WHERE user_id = ? ORDER BY frequency DESC LIMIT ?",
                    (self.user_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def extract_and_store_facts(self, user_message: str, ai_response: str) -> None:
        name_patterns = [
            (r"(?:my name is|i'm|i am|mera naam|मेरा नाम)\s+([A-Z][a-zA-Z\s]{1,30})", "personal", "name"),
            (r"(?:i live in|i'm from|i stay in|mein|मैं)\s+([A-Z][a-zA-Z\s]{1,25})", "personal", "location"),
            (r"(?:i work at|i work for|i'm a|main|hoon)\s+(developer|engineer|designer|manager|student|teacher|doctor|freelancer)", "personal", "profession"),
            (r"(?:i like|i love|i prefer|i enjoy|मुझे|mujhe)\s+(.{3,50})", "preferences", "likes"),
            (r"(?:my project|i'm building|mera project|मेरा project)\s+(.{5,80})", "projects", "current_project"),
            (r"(?:i use|i prefer|main use|मैं use)\s+(python|javascript|typescript|java|rust|go|react|vue|angular|node)", "preferences", "tech_stack"),
        ]
        for pattern, category, key in name_patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if len(value) > 3:
                    self.store_fact(category, key, value, confidence=0.9)

    def build_memory_context(self) -> str:
        parts = []
        prefs = self.get_preferences()
        if prefs:
            pref_items = ", ".join(f"{k}: {v}" for k, v in list(prefs.items())[:10])
            parts.append(f"User preferences: {pref_items}")

        facts = self.recall_facts(limit=15)
        if facts:
            fact_items = []
            for f in facts:
                fact_items.append(f"{f['fact_key']}: {f['fact_value']}")
            parts.append("Known facts about user: " + "; ".join(fact_items))

        summaries = self.get_recent_summaries(3)
        if summaries:
            summary_items = [s["summary"][:200] for s in summaries]
            parts.append("Recent conversation themes: " + " | ".join(summary_items))

        patterns = self.get_learned_patterns(limit=5)
        if patterns:
            pattern_items = [p["pattern"] for p in patterns if p["frequency"] > 1]
            if pattern_items:
                parts.append("Frequent user patterns: " + "; ".join(pattern_items[:5]))

        return "\n".join(parts) if parts else ""


class GlobalMemoryStore:
    def __init__(self):
        self._instances: dict[str, ConversationMemory] = {}

    def get(self, user_id: str = "default", chat_id: str = "") -> ConversationMemory:
        key = f"{user_id}:{chat_id}"
        if key not in self._instances:
            self._instances[key] = ConversationMemory(user_id, chat_id)
        return self._instances[key]

    def extract_global_facts(self, user_id: str, messages: list[dict]) -> None:
        memory = self.get(user_id)
        for msg in messages:
            if msg.get("role") == "user":
                memory.extract_and_store_facts(msg.get("content", ""), "")
            elif msg.get("role") == "assistant":
                user_msg = next(
                    (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
                    "",
                )
                memory.extract_and_store_facts(user_msg, msg.get("content", ""))


memory_store = GlobalMemoryStore()
