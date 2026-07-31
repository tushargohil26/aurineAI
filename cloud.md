# Cloud Deployment (Aurine Nexus Server)

The **Nexus server** is a single Aurine instance that runs your own AI models and
serves all your devices. Each account gets isolated chats, documents, and memory
(per-user data separation is enforced on the server).

## Option 1 - One command with Docker (recommended)

A Docker VPS (or any machine with Docker) can run the whole stack: the Aurine app
plus Ollama with your custom `aurine-coder` / `aurine-native` models.

```powershell
# 1. Copy the repo to the server (or build from this folder)
# 2. Build and start (pulls ~9 GB of models on first run)
docker compose up -d --build

# 3. Open:
#    http://SERVER_IP:8000
```

- The app container auto-connects to the `ollama` service (`OLLAMA_BASE_URL=http://ollama:11434`).
- Custom models `aurine-coder` and `aurine-native` are created from the Modelfiles on first start.
- Data (vector DB, uploads, user data) is stored in the `aurine_data` volume; models in `ollama_models`.
- Change the public port with `NEXUS_PORT=8080 docker compose up -d`.

## Option 2 - Run directly on the machine (no Docker)

```powershell
# Local Ollama is required (already installed):
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
ollama create aurine-coder -f Modelfile
ollama create aurine-native -f Modelfile-native

# Start the Nexus server on 0.0.0.0:8000
python auracode.py --nexus
# (or installed: auracode.bat --nexus)

# Other devices connect to:  http://YOUR_LAN_IP:8000
```

Add a firewall rule so other devices can reach port 8000:

```powershell
netsh advfirewall firewall add rule name="Aurine Nexus" dir=in action=allow protocol=TCP localport=8000
```

## Option 3 - Render (cloud PaaS, cloud provider keys)

1. Push this folder to GitHub.
2. Create a new Render Web Service.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:

```text
AI_PROVIDER=google        # or openai, groq, deepseek...
GOOGLE_API_KEY=your-free-key
GOOGLE_CHAT_MODEL=gemini-2.0-flash
DATA_DIR=/var/data/data
VECTOR_DB=/var/data/vector_store.sqlite3
GENERATED_PROJECTS_DIR=/var/data/generated_projects
```

6. Add a persistent disk mounted at `/var/data` (keeps user data + vectors across redeploys).

## Docker (single container, cloud API only)

```powershell
docker build -t aurine-nexus .
docker run -p 8000:8000 -e AI_PROVIDER=google -e GOOGLE_API_KEY="key" aurine-nexus
```

## Notes

- Per-user isolation: users sign up and each account has its own chat history,
  uploaded documents, and memory. The `/memory/{user_id}` endpoint rejects non-owners.
- First OTP login in dev mode: the 6-digit code is written to `{DATA_DIR}/otp_codes.log`.
  Configure `EMAIL_SMTP_*` to send real emails.
- Production elements: FastAPI backend, PWA frontend, Ollama or cloud chat/embedding
  models, SQLite vector store, persistent volumes, environment variables for secrets.
