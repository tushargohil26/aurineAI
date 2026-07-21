"""
Per-device identity and data isolation.
Each device/user gets a unique ID and separate storage.
"""
import hashlib
import json
import os
import platform
import sqlite3
import uuid
from pathlib import Path


DATA_DIR = Path.home() / ".aurine-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_device_id() -> str:
    """Generate a unique, stable device ID based on hardware info."""
    id_file = DATA_DIR / ".device_id"
    if id_file.exists():
        return id_file.read_text().strip()

    parts = [
        platform.node(),
        platform.machine(),
        str(uuid.getnode()),
        os.getenv("USERNAME", os.getenv("USER", "unknown")),
    ]
    raw = "|".join(parts)
    device_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    id_file.write_text(device_id)
    return device_id


def get_user_id() -> str:
    """Get or create user ID for this device."""
    id_file = DATA_DIR / ".user_id"
    if id_file.exists():
        return id_file.read_text().strip()

    user_id = f"user_{get_device_id()}"
    id_file.write_text(user_id)
    return user_id


def get_device_name() -> str:
    """Human-readable device name."""
    return f"{platform.node()} ({platform.system()})"


def get_data_dir() -> Path:
    """Get the data directory for this device."""
    device_dir = DATA_DIR / get_device_id()
    device_dir.mkdir(parents=True, exist_ok=True)
    return device_dir


def get_db_path() -> Path:
    """Get SQLite database path for this device."""
    return get_data_dir() / "memory.db"


def get_chats_dir() -> Path:
    """Get chats directory for this device."""
    chats_dir = get_data_dir() / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    return chats_dir


def get_device_db() -> sqlite3.Connection:
    """Get a database connection for this device's data."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_device_tables(conn)
    return conn


def _ensure_device_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            agent TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_facts (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'general',
            fact_key TEXT NOT NULL,
            fact_value TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL DEFAULT 'conversation',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS learned_patterns (
            id TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            response_hint TEXT NOT NULL DEFAULT '',
            frequency INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_chat ON chat_history(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_role ON chat_history(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_key ON memory_facts(fact_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_freq ON learned_patterns(frequency DESC)")
    conn.commit()


def store_chat_message(chat_id: str, role: str, content: str, agent: str = "") -> None:
    """Store a chat message for this device."""
    from datetime import datetime
    msg_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat() + "Z"
    with get_device_db() as conn:
        conn.execute(
            "INSERT INTO chat_history (id, chat_id, role, content, agent, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, chat_id, role, content, agent, now),
        )


def get_chat_history(chat_id: str, limit: int = 50) -> list[dict]:
    """Get chat history for this device."""
    with get_device_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_history WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_all_chats() -> list[dict]:
    """Get all chats for this device."""
    with get_device_db() as conn:
        rows = conn.execute(
            """SELECT chat_id, 
                      MIN(created_at) as started,
                      MAX(created_at) as last_message,
                      COUNT(*) as message_count
               FROM chat_history 
               GROUP BY chat_id 
               ORDER BY last_message DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def store_fact(category: str, key: str, value: str, confidence: float = 1.0) -> None:
    """Store a fact for this device."""
    from datetime import datetime
    fact_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat() + "Z"
    with get_device_db() as conn:
        existing = conn.execute(
            "SELECT id FROM memory_facts WHERE category = ? AND fact_key = ?",
            (category, key),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE memory_facts SET fact_value = ?, confidence = ?, updated_at = ? WHERE id = ?",
                (value, confidence, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO memory_facts (id, category, fact_key, fact_value, confidence, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'conversation', ?, ?)",
                (fact_id, category, key, value, confidence, now, now),
            )


def recall_facts(category: str = "", limit: int = 20) -> list[dict]:
    """Recall facts for this device."""
    with get_device_db() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM memory_facts WHERE category = ? ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memory_facts ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def store_preference(key: str, value: str) -> None:
    """Store a preference for this device."""
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    with get_device_db() as conn:
        conn.execute(
            "INSERT INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now),
        )


def get_preferences() -> dict:
    """Get all preferences for this device."""
    with get_device_db() as conn:
        rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
    return {r["key"]: r["value"] for r in rows}


def learn_pattern(pattern_type: str, pattern: str, response_hint: str = "") -> None:
    """Learn a pattern for this device."""
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    with get_device_db() as conn:
        existing = conn.execute(
            "SELECT id, frequency FROM learned_patterns WHERE pattern = ?",
            (pattern,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE learned_patterns SET frequency = frequency + 1 WHERE id = ?",
                (existing["id"],),
            )
        else:
            conn.execute(
                "INSERT INTO learned_patterns (id, pattern_type, pattern, response_hint, frequency, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (uuid.uuid4().hex, pattern_type, pattern, response_hint, now),
            )


def get_learned_patterns(limit: int = 20) -> list[dict]:
    """Get learned patterns for this device."""
    with get_device_db() as conn:
        rows = conn.execute(
            "SELECT * FROM learned_patterns ORDER BY frequency DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def build_memory_context() -> str:
    """Build memory context string for AI prompts."""
    import re
    parts = []

    prefs = get_preferences()
    if prefs:
        pref_items = ", ".join(f"{k}: {v}" for k, v in list(prefs.items())[:10])
        parts.append(f"User preferences: {pref_items}")

    facts = recall_facts(limit=15)
    if facts:
        fact_items = [f"{f['fact_key']}: {f['fact_value']}" for f in facts]
        parts.append("Known facts about user: " + "; ".join(fact_items))

    patterns = get_learned_patterns(limit=5)
    if patterns:
        pattern_items = [p["pattern"] for p in patterns if p["frequency"] > 1]
        if pattern_items:
            parts.append("Frequent user patterns: " + "; ".join(pattern_items[:5]))

    return "\n".join(parts) if parts else ""


def extract_facts_from_message(message: str) -> None:
    """Extract and store facts from a user message."""
    import re
    patterns = [
        (r"(?:my name is|i'm|i am|mera naam)\s+([A-Z][a-zA-Z\s]{1,30})", "personal", "name"),
        (r"(?:i live in|i'm from|i stay in)\s+([A-Z][a-zA-Z\s]{1,25})", "personal", "location"),
        (r"(?:i work at|i work for|i'm a)\s+(developer|engineer|designer|manager|student|teacher|doctor|freelancer)", "personal", "profession"),
        (r"(?:i like|i love|i prefer|i enjoy)\s+(.{3,50})", "preferences", "likes"),
        (r"(?:my project|i'm building)\s+(.{5,80})", "projects", "current_project"),
        (r"(?:i use|i prefer)\s+(python|javascript|typescript|java|rust|go|react|vue|angular|node)", "preferences", "tech_stack"),
    ]
    for pattern, category, key in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) > 3:
                store_fact(category, key, value, confidence=0.9)


def extract_coding_patterns(message: str, response: str) -> None:
    """Extract coding patterns from conversation to learn user's style."""
    import re

    lang_patterns = [
        (r"```python", "python"),
        (r"```javascript|```js", "javascript"),
        (r"```typescript|```ts", "typescript"),
        (r"```java(?!\s*script)", "java"),
        (r"```rust|```rs", "rust"),
        (r"```go", "go"),
        (r"```html", "html"),
        (r"```css", "css"),
        (r"```sql", "sql"),
    ]
    for pattern, lang in lang_patterns:
        if re.search(pattern, message, re.IGNORECASE) or re.search(pattern, response, re.IGNORECASE):
            learn_pattern("language", lang, f"User works with {lang}")

    task_patterns = [
        (r"(?:fix|debug|error|bug)", "debugging", "User asks for debugging help"),
        (r"(?:create|build|make|write|implement)", "creation", "User asks to create code"),
        (r"(?:explain|what is|how does)", "learning", "User asks for explanations"),
        (r"(?:refactor|optimize|improve|clean)", "improvement", "User asks for code improvements"),
        (r"(?:test|unit test|integration test)", "testing", "User asks for tests"),
        (r"(?:deploy|docker|ci[/.]cd|kubernetes)", "devops", "User asks for deployment help"),
        (r"(?:api|endpoint|rest|graphql)", "api_design", "User asks for API design"),
        (r"(?:database|sql|query|schema)", "database", "User asks for database work"),
    ]
    for pattern, task_type, hint in task_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            learn_pattern("task_type", task_type, hint)

    style_patterns = [
        (r"(?:short|concise|brief|simple)", "style_concise", "User prefers concise responses"),
        (r"(?:detailed|explain|step.by.step|thorough)", "style_detailed", "User prefers detailed responses"),
        (r"(?:comment|document|docstring)", "style_documented", "User wants documented code"),
        (r"(?:no comment|without comment|minimal)", "style_minimal", "User prefers minimal comments"),
    ]
    for pattern, style_type, hint in style_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            learn_pattern("response_style", style_type, hint)


def build_training_context() -> str:
    """Build training context from conversation history for Aurine model."""
    parts = []

    patterns = get_learned_patterns(limit=50)
    if patterns:
        lang_patterns = [p for p in patterns if p["pattern_type"] == "language"]
        if lang_patterns:
            langs = [p["pattern"] for p in lang_patterns[:5]]
            parts.append(f"User frequently works with: {', '.join(langs)}")

        task_patterns = [p for p in patterns if p["pattern_type"] == "task_type"]
        if task_patterns:
            tasks = [p["pattern"] for p in task_patterns[:5]]
            parts.append(f"Common tasks: {', '.join(tasks)}")

        style_patterns = [p for p in patterns if p["pattern_type"] == "response_style"]
        if style_patterns:
            parts.append(f"Response style preference: {style_patterns[0]['pattern']}")

    facts = recall_facts(limit=20)
    if facts:
        parts.append("Known about user: " + "; ".join(f"{f['fact_key']}: {f['fact_value']}" for f in facts))

    return "\n".join(parts) if parts else ""


def get_device_info() -> dict:
    """Get device information."""
    return {
        "device_id": get_device_id(),
        "user_id": get_user_id(),
        "device_name": get_device_name(),
        "data_dir": str(get_data_dir()),
        "db_path": str(get_db_path()),
        "chats_dir": str(get_chats_dir()),
    }
