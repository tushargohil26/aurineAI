# Aurine AI Assistant

Cloud-ready Codex-style assistant that runs with Ollama locally or OpenAI if you choose. It includes persistent chats, uploaded-file memory, real image/PDF/video/document artifacts, editable generated projects, project terminal commands, Ruflo-style agents, and plugin checks.

## Run

```powershell
cd "C:\Users\ADMIN\Documents\Codex\2026-06-29\is\outputs\aurine-ai-assistant"
.\run.ps1
```

Open:

```text
http://127.0.0.1:8000
```

You can also double-click `START_AURINE.bat`.

## Use

1. Ask normal questions without uploading anything.
2. Create separate chats from the sidebar.
3. Open `Agents` from the left sidebar and click an agent to use it in the current chat.
4. Cancel the selected agent from the chip inside the chat composer.
5. Ask coding questions and get implementation plans, commands, and files.
6. Ask for image, PDF, video-scene, or document generation to create real files.
7. Upload a PDF, `.txt`, or `.md` file when you want answers from your own data.

Generated code projects are saved in `generated_projects/`. Generated images, PDFs, video scenes, and documents are saved in `generated_artifacts/`.

Ruflo-style agents and plugin families are available from the Agents and Plugins panels, including swarm, RAG memory, test generator, docs, security audit, SPARC, AgentDB, and more.

## Setup Notes

Do not hard-code your OpenAI API key. Create a `.env` file from `.env.example` and paste a newly generated key there.

Default local mode:

```text
AI_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

OpenAI mode is optional:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your-new-key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## AuraCode

Run the desktop terminal coding agent:

```powershell
.\auracode.ps1
```
