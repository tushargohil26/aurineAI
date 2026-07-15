# Cloud Deployment

This app is cloud-ready for Render, Railway, Fly.io, or any Docker host.

## Recommended Render Setup

1. Push this folder to GitHub.
2. Create a new Render Web Service.
3. Use these commands:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Add environment variables:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your-new-openai-key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DATA_DIR=/var/data/data
VECTOR_DB=/var/data/vector_store.sqlite3
GENERATED_PROJECTS_DIR=/var/data/generated_projects
```

5. Add a persistent disk:

```text
Mount Path: /var/data
Size: 1 GB or more
```

Without a persistent disk, uploaded PDFs and the vector database may disappear after redeploys.

## Docker

```powershell
docker build -t my-ai-assistant .
docker run -p 8000:8000 -e OPENAI_API_KEY="your-new-openai-key" my-ai-assistant
```

For no external API key, run Ollama on your own server and set:

```text
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://your-ollama-host:11434
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

Open:

```text
http://127.0.0.1:8000
```

## Production Elements

- FastAPI backend
- Static web app frontend
- OpenAI or Ollama chat model
- OpenAI or Ollama embedding model
- SQLite vector store
- Persistent disk for uploaded files and vectors
- Code Builder for AI-generated multi-file projects
- Zip download for generated projects
- Environment variables for secrets
- Dockerfile for container hosting
