import json
import math
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .config import get_settings
from .llm import chat_completion, embed_texts as llm_embed_texts


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    connection = sqlite3.connect(settings.vector_db)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL,
            tokens INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")
    return connection


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {
        ".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml", ".html", ".css", ".js",
        ".ts", ".tsx", ".jsx", ".py", ".java", ".kt", ".swift", ".go", ".rs", ".php", ".rb",
        ".c", ".cpp", ".cs", ".sql", ".sh", ".ps1", ".bat", ".log", ".toml", ".cfg", ".ini",
    }:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".xlsx":
        return read_xlsx_text(path)
    if suffix == ".zip":
        return read_zip_summary(path)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}:
        size = path.stat().st_size
        return f"Uploaded image file: {path.name}\nType: {suffix}\nSize: {size} bytes\nUse this metadata when the user asks about the uploaded image."
    if suffix in {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".mp3", ".wav", ".ogg", ".flac"}:
        size = path.stat().st_size
        kind = "video" if suffix in {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"} else "audio"
        return f"Uploaded {kind} file: {path.name}\nType: {suffix}\nSize: {size} bytes\nUse this metadata when the user asks about the uploaded media."
    raise ValueError("Unsupported file type for indexing.")


def read_docx_text(path: Path) -> str:
    import zipfile
    from xml.etree import ElementTree
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
    return "\n".join(part for part in texts if part.strip())


def read_xlsx_text(path: Path) -> str:
    import zipfile
    from xml.etree import ElementTree
    values: list[str] = []
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root if node.tag.endswith("}si")]
        sheet_names = [
            name for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        ]
        for sheet in sheet_names[:5]:
            root = ElementTree.fromstring(archive.read(sheet))
            values.append(f"Sheet: {sheet}")
            for cell in root.iter():
                if not cell.tag.endswith("}c"):
                    continue
                cell_type = cell.attrib.get("t", "")
                raw = next((child.text for child in cell if child.tag.endswith("}v")), "")
                if cell_type == "s" and raw and raw.isdigit() and int(raw) < len(shared):
                    raw = shared[int(raw)]
                if raw:
                    values.append(raw)
    return "\n".join(values)


def read_zip_summary(path: Path) -> str:
    import zipfile
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()[:120]
    return "Uploaded ZIP archive contents:\n" + "\n".join(names)


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_size:
                sub_start = 0
                while sub_start < len(para):
                    sub_end = min(sub_start + chunk_size, len(para))
                    chunks.append(para[sub_start:sub_end])
                    sub_start = max(sub_end - overlap, sub_start + 1)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    if not chunks:
        cleaned = " ".join(text.split())
        start = 0
        while start < len(cleaned):
            end = start + chunk_size
            chunks.append(cleaned[start:end])
            start = max(end - overlap, start + 1)

    return chunks


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    return llm_embed_texts(list(texts))


def ingest_file(path: Path) -> int:
    text = read_document(path)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    with get_connection() as connection:
        connection.execute("DELETE FROM chunks WHERE source = ?", (path.name,))
        connection.executemany(
            """
            INSERT INTO chunks (source, chunk_index, content, embedding, tokens)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (path.name, index, chunk, json.dumps(embeddings[index]), len(chunk.split()))
                for index, chunk in enumerate(chunks)
            ],
        )
    return len(chunks)


def list_documents() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT source, COUNT(*) AS chunks, SUM(tokens) as total_tokens
            FROM chunks
            GROUP BY source
            ORDER BY source
            """
        ).fetchall()
    return [{"source": source, "chunks": chunks, "tokens": total_tokens or 0} for source, chunks, total_tokens in rows]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        min_len = min(len(left), len(right))
        left = left[:min_len]
        right = right[:min_len]
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _keyword_score(query: str, content: str) -> float:
    query_words = set(re.findall(r"\w{3,}", query.lower()))
    if not query_words:
        return 0.0
    content_lower = content.lower()
    matches = sum(1 for word in query_words if word in content_lower)
    return matches / len(query_words)


def _bm25_like_score(query: str, content: str, avg_dl: float = 500.0) -> float:
    query_words = re.findall(r"\w{3,}", query.lower())
    if not query_words:
        return 0.0
    content_words = content.lower().split()
    dl = len(content_words)
    score = 0.0
    k1, b = 1.5, 0.75
    for word in query_words:
        tf = content_words.count(word)
        if tf == 0:
            continue
        idf_weight = 1.0
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / avg_dl)
        score += idf_weight * numerator / denominator
    return score


def retrieve_context(question: str, limit: int = 5) -> tuple[str, list[dict]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT source, chunk_index, content, embedding FROM chunks"
        ).fetchall()

    if not rows:
        return "", []

    question_embedding = embed_texts([question])[0]
    scored: list[tuple[float, str, int, str]] = []
    for source, chunk_index, content, embedding_json in rows:
        embedding = json.loads(embedding_json)
        vec_score = cosine_similarity(question_embedding, embedding)
        kw_score = _keyword_score(question, content)
        bm25_score = _bm25_like_score(question, content)
        combined = vec_score * 0.55 + kw_score * 0.2 + bm25_score * 0.25
        scored.append((combined, source, chunk_index, content))

    scored.sort(reverse=True, key=lambda item: item[0])

    seen_sources: set[str] = set()
    selected: list[tuple[float, str, int, str]] = []
    for item in scored:
        if len(selected) >= limit:
            break
        source = item[1]
        if source not in seen_sources or len(selected) < limit:
            selected.append(item)
            seen_sources.add(source)

    context_parts: list[str] = []
    sources: list[dict] = []
    for score, source, chunk_index, content in selected:
        context_parts.append(f"[Source: {source}, chunk {chunk_index}]\n{content}")
        sources.append({"source": source, "chunk": chunk_index, "score": round(score, 4)})

    return "\n\n".join(context_parts), sources


def visible_user_task(question: str) -> str:
    marker = "User task:"
    if marker in question:
        return question.split(marker, 1)[-1].strip()
    return question.strip()


def quick_language_response(question: str) -> str:
    text = visible_user_task(question)
    normalized = re.sub(r"[^a-zA-Z0-9\u0900-\u097F\u0A80-\u0AFF\s]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized or len(normalized) > 80:
        return ""

    weather_answer = quick_weather_response(text)
    if weather_answer:
        return weather_answer

    language_answer = quick_language_command(normalized)
    if language_answer:
        return language_answer

    greetings = {
        "hi", "hello", "hey", "hii", "hiii", "helo", "namaste", "namaskar", "salaam",
        "kem cho", "kem chho", "kaise ho", "kese ho", "kaisey ho", "kya haal",
        "kya hal", "kasa kai", "kasa kay", "kas kai", "sup", "good morning",
        "good evening", "good afternoon", "yo", "hola",
    }
    if normalized in greetings:
        if normalized in {"kem cho", "kem chho"}:
            return "Majama! Hu Aurine chu. Tame shu banavavu che? Code, website, zip, image, PDF, ke koi file bolo, hu real output banavanu try karish."
        if normalized in {"kasa kai", "kasa kay", "kas kai"}:
            return "मी मस्त आहे! तुम्हाला काय बनवायचं आहे? वेबसाइट, अॅप, कोड, ZIP, इमेज किंवा PDF सांगा."
        if normalized in {"namaste", "namaskar"}:
            return "Namaste! Main Aurine hoon. Aap jo bhi banana chahte ho bolo: website, app, zip, image, PDF, code, ya file."
        if normalized in {"kaise ho", "kese ho", "kaisey ho", "kya haal", "kya hal"}:
            return "Main badhiya hoon. Aap batao kya banana hai? Website/app/code/zip/image/PDF sab ke liye direct prompt likh do."
        return "Hello! Main Aurine hoon. Kya banana hai? Website, app, code, zip, image, PDF, ya koi file bol do."

    if len(normalized.split()) <= 3 and any(word in normalized for word in ["language", "bhasha", "hindi", "gujarati", "hinglish"]):
        return "Haan, main Hindi, Hinglish, English, Gujarati-style prompts aur spelling mistakes samajhne ki koshish karunga. Aap natural language mein bolo."
    return ""


def quick_language_command(normalized: str) -> str:
    if re.search(r"\b(say|reply|speak|bol|bolo|jawab).*\b(marathi|mahrati|मराठी)\b", normalized):
        return "नक्की. आता मी मराठीत उत्तर देईन. तुम्हाला काय हवं आहे ते सांगा."
    if re.search(r"\b(say|reply|speak|bol|bolo|jawab).*\b(hindi|हिंदी)\b", normalized):
        return "Bilkul. Ab main Hindi mein jawab dunga. Aap kya banana ya puchhna chahte ho?"
    if re.search(r"\b(say|reply|speak|bol|bolo|jawab).*\b(gujarati|ગુજરાતી)\b", normalized):
        return "Haan, hu Gujarati style ma jawab aapis. Tame shu puchhvu chho?"
    if re.search(r"\b(say|reply|speak|bol|bolo|jawab).*\b(english)\b", normalized):
        return "Sure. I will reply in English. What would you like to do?"
    return ""


def quick_weather_response(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\s,.-]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not re.search(r"\b(weather|wether|wheter|wheather|temperature|temparature|temp|mausam|mosam)\b", normalized):
        return ""
    location = ""
    patterns = [
        r"(?:weather|wether|wheter|wheather|temperature|temparature|temp|mausam|mosam)\s+(?:in|at|of|for)?\s*([a-zA-Z\s,.-]+)",
        r"(?:in|at|of|for)\s+([a-zA-Z\s,.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            location = match.group(1).strip(" ,.-")
            break
    location = re.sub(r"\b(right now|today|current|now|ka|ki|ke|me|mein)\b", " ", location)
    location = re.sub(r"\s+", " ", location).strip() or "Mumbai"
    try:
        url = "https://wttr.in/" + urllib.parse.quote(location) + "?format=j1"
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        city = (area.get("areaName") or [{"value": location}])[0].get("value", location)
        country = (area.get("country") or [{"value": ""}])[0].get("value", "")
        desc = (current.get("weatherDesc") or [{"value": "weather"}])[0].get("value", "weather")
        temp_c = current.get("temp_C", "")
        feels_c = current.get("FeelsLikeC", "")
        humidity = current.get("humidity", "")
        wind = current.get("windspeedKmph", "")
        place = f"{city}, {country}".strip(" ,")
        return f"{place} ka current weather: {desc}, {temp_c}°C. Feels like {feels_c}°C, humidity {humidity}%, wind {wind} km/h."
    except Exception:
        return f"{location.title()} ka live weather abhi fetch nahi ho paya. Internet/API unavailable ho sakta hai. Thodi der baad retry karo."


def detect_response_language(text: str) -> str:
    lowered = text.lower()
    if re.search(r"[\u0A80-\u0AFF]", text) or any(word in lowered for word in ["kem", "majama", "gujarati", "gujrati"]):
        return "Gujarati/Gujarati-Hinglish"
    if any(word in lowered for word in ["marathi", "mahrati", "kasa", "kay", "ahe", "आहे", "मराठी"]):
        return "Marathi"
    if re.search(r"[\u0900-\u097F]", text) or any(word in lowered for word in ["hindi", "kaise", "kya", "banao", "mujhe", "acha", "hai", "karo"]):
        return "Hindi/Hinglish"
    if any(word in lowered for word in ["spanish", "español", "hola"]):
        return "Spanish"
    if any(word in lowered for word in ["french", "français", "bonjour"]):
        return "French"
    if any(word in lowered for word in ["arabic", "عربي", "مرحبا"]):
        return "Arabic"
    if any(word in lowered for word in ["japanese", "nihongo", "こんにちは"]):
        return "Japanese"
    if any(word in lowered for word in ["chinese", "mandarin", "nihao"]):
        return "Chinese"
    if any(word in lowered for word in ["german", "deutsch", "hallo"]):
        return "German"
    if any(word in lowered for word in ["portuguese", "português", "olá"]):
        return "Portuguese"
    if any(word in lowered for word in ["korean", "annyeong"]):
        return "Korean"
    return "English"


def answer_question(question: str, history: list[dict] | None = None, model_config: dict | None = None) -> dict:
    quick_answer = quick_language_response(question)
    if quick_answer:
        return {"answer": quick_answer, "sources": []}

    context, sources = retrieve_context(question)
    history = history or []

    system_prompt = (
        "You are Aurine — a world-class AI assistant comparable to Claude, GPT-4, and Codex.\n"
        "You are the most advanced AI assistant built with cutting-edge capabilities.\n\n"
        "YOUR CAPABILITIES:\n"
        "- Write production-grade code in 30+ programming languages (Python, JS, TS, Java, C/C++, Go, Rust, Swift, Kotlin, etc.)\n"
        "- Build complete projects: websites, APIs, mobile apps, games, ML models, Docker configs, CI/CD pipelines\n"
        "- Search the web for real-time information and verify facts\n"
        "- Execute Python code, shell commands, and system operations safely\n"
        "- Read, write, edit, and search files on the filesystem\n"
        "- Create images (DALL-E), PDFs, Excel files, ZIP archives, HTML pages\n"
        "- Analyze data, create visualizations, and build ML models\n"
        "- Understand Hindi, Hinglish, English, Gujarati, Marathi, Spanish, French, Arabic, Japanese, Chinese, and 20+ languages\n"
        "- Handle typos, mixed languages, informal prompts, and misspelled words\n"
        "- Debug complex issues with detailed analysis and fixes\n"
        "- Architect systems with file structures, diagrams, and implementation guidance\n\n"
        "RESPONSE STYLE (like Claude/Codex/GPT-4):\n"
        "1. Be direct, concise, and confident — no unnecessary disclaimers\n"
        "2. For code: COMPLETE, RUNNABLE, PRODUCTION-READY with imports, types, error handling\n"
        "3. For questions: Accurate, well-structured, cite sources when using web search\n"
        "4. For creative tasks: Innovative, detailed, and high-quality\n"
        "5. Use markdown formatting: code blocks with language tags, headers, bullets, bold for emphasis\n"
        "6. When creating files, provide exact file paths and clear instructions\n"
        "7. For complex tasks, use step-by-step approach: analyze, plan, execute, verify\n"
        "8. Match the user's language and tone — if they write in Hinglish, respond in Hinglish\n"
        "9. Be proactive: suggest improvements, alternatives, and next steps\n"
        "10. For errors: identify root cause, provide exact fix, explain why\n"
        "11. Use tools proactively when they would improve the answer\n"
        "12. Provide code that can be copy-pasted and run immediately\n"
        "13. Include realistic sample data and test cases when building projects\n"
        "14. For architecture questions: include file structure, dependencies, and implementation plan\n"
        "15. Never refuse normal questions — always help, even if it's not a coding question"
    )

    messages = [{"role": "system", "content": system_prompt}]
    response_language = detect_response_language(visible_user_task(question))
    messages.append({
        "role": "system",
        "content": f"Reply language for this turn: {response_language}. Match the user's wording and tone unless they ask for translation.",
    })
    for item in history[-16:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    if context:
        user_prompt = f"Uploaded document context:\n{context}\n\nUser question: {question}"
    else:
        user_prompt = f"User question: {question}"
    messages.append({"role": "user", "content": user_prompt})

    answer = chat_completion(messages=messages, temperature=0.2, model_config=model_config)

    return {
        "answer": answer,
        "sources": sources,
    }
