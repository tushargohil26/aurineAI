import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("AURINE_TEST_BASE", "http://127.0.0.1:8000")
OTP_LOG = os.environ.get("AURINE_OTP_LOG", os.path.join(os.path.expanduser("~"), ".aurine", "data", "otp_codes.log"))
MODEL = os.environ.get("AURINE_TEST_MODEL", "qwen2.5-coder:7b")

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    tag = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def request(method, path, body=None, token=None, timeout=60):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def attempt():
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, json.loads(raw), raw
                except ValueError:
                    return resp.status, None, raw
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw), raw
            except ValueError:
                return exc.code, None, raw
        except urllib.error.URLError as exc:
            return None, {"error": str(exc)}, ""

    status, body, raw = attempt()
    if status == 429:
        time.sleep(63)
        status, body, raw = attempt()
    return status, body, raw


def read_otp(email):
    if not os.path.exists(OTP_LOG):
        return None
    marker = f"OTP for {email}: "
    code = None
    with open(OTP_LOG, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if marker in line:
                code = line.split(marker, 1)[1].strip().split()[0]
    return code


def register(email):
    status, body, _ = request("POST", "/auth/send-otp", {"email": email})
    assert status == 200, f"send-otp {status}"
    code = read_otp(email)
    assert code, "OTP not logged"
    status, body, _ = request("POST", "/auth/verify-otp", {"email": email, "code": code})
    assert status == 200, f"verify-otp {status}"
    token = body["token"]
    user_id = body["user"]["id"]
    return token, user_id


def main():
    print(f"=== Aurine nexus E2E suite ===")
    print(f"base:   {BASE}")
    print(f"model:  {MODEL}")
    print()

    print("[1] Public surface")
    status, _, raw = request("GET", "/health")
    check("GET /health", status == 200, f"status={status}")
    status, _, raw = request("GET", "/")
    check("GET /", status == 200 and "Aurine" in raw, f"status={status}")
    status, _, _ = request("GET", "/sw.js")
    check("GET /sw.js", status == 200, f"status={status}")
    status, body, _ = request("GET", "/static/manifest.json")
    check("GET /static/manifest.json", status == 200, f"status={status}")
    status, body, _ = request("GET", "/auth/google/status")
    check("GET /auth/google/status", status == 200, f"status={status}")
    status, body, _ = request("GET", "/v1/models", token="sk-invalid")
    check("GET /v1/models rejects bad key", status == 401, f"status={status}")

    print()
    print("[2] Auth guards (no token)")
    status, _, _ = request("GET", "/chats")
    check("GET /chats requires login", status == 401, f"status={status}")
    status, _, _ = request("GET", "/documents")
    check("GET /documents requires login", status == 401, f"status={status}")
    status, _, _ = request("GET", "/scheduled")
    check("GET /scheduled requires login", status == 401, f"status={status}")
    status, _, _ = request("POST", "/automation/start", {"goal": "hi"})
    check("POST /automation/start requires login", status == 401, f"status={status}")

    print()
    print("[3] OTP sign-up")
    suffix = uuid.uuid4().hex[:6]
    email_a = f"alpha{suffix}@test.dev"
    email_b = f"beta{suffix}@test.dev"
    token_a, id_a = register(email_a)
    token_b, id_b = register(email_b)
    check("register user A via OTP", bool(token_a) and bool(id_a))
    check("register user B via OTP", bool(token_b) and bool(id_b))
    check("users are isolated ids", id_a != id_b)

    print()
    print("[4] Authenticated surface")
    status, body, _ = request("POST", "/chats", {"title": "Nexus E2E chat", "agent_mode": "general"}, token=token_a)
    chat_id = body.get("chat", {}).get("id") if status == 200 else None
    check("POST /chats", status == 200 and chat_id, f"status={status}")
    status, body, _ = request("GET", "/chats", token=token_a)
    check("GET /chats (A)", status == 200 and any(c.get("id") == chat_id for c in body.get("chats", [])), f"status={status}")
    status, body, _ = request("GET", "/chats", token=token_b)
    check("chat isolation (B does not see A)", status == 200 and not any(c.get("id") == chat_id for c in body.get("chats", [])), f"status={status}")
    status, body, _ = request("POST", "/agents", {"name": "E2E Bot", "detail": "test", "instructions": "Be concise."}, token=token_a)
    agent_id = body.get("agent", {}).get("id") if status == 200 else None
    check("POST /agents", status == 200 and agent_id, f"status={status}")
    status, body, _ = request("GET", "/agents", token=token_a)
    check("GET /agents (A)", status == 200 and any(a.get("id") == agent_id for a in body.get("agents", [])), f"status={status}")
    status, body_b, _ = request("GET", "/agents", token=token_b)
    check("custom agent isolation (B sees none)", status == 200 and not body_b.get("agents"), f"status={status}")
    status, body, _ = request("POST", "/api-keys", {"name": "e2e"}, token=token_a)
    api_key = body.get("key", {}).get("key") if status == 200 else None
    check("POST /api-keys", status == 200 and api_key, f"status={status}")
    status, body, _ = request("GET", "/api-keys", token=token_a)
    check("GET /api-keys (A)", status == 200 and body.get("keys"), f"status={status}")

    print()
    print("[5] Memory (auto-learn + per-user isolation)")
    status, body, _ = request(
        "POST", "/chat",
        {"question": f"Remember this: my favorite color is deep ocean blue and my project is called Alpha {suffix}."},
        token=token_a, timeout=300,
    )
    check("POST /chat (A) AI answer", status == 200 and bool(body.get("answer")), f"status={status}")
    status, body, _ = request("GET", f"/memory/{id_a}", token=token_a)
    facts = (body.get("facts") or []) if status == 200 else []
    check("GET /memory/{A} (A)", status == 200, f"status={status}")
    check("memory auto-learned fact", any(suffix in str(f) for f in facts), f"facts={len(facts)}")
    status, _, _ = request("GET", f"/memory/{id_a}", token=token_b)
    check("memory isolation (B -> A is 403)", status == 403, f"status={status}")
    status, _, _ = request("GET", f"/memory/{id_a}")
    check("memory requires login (no token)", status == 401, f"status={status}")

    print()
    print("[6] Documents upload")
    boundary = f"----aurine{uuid.uuid4().hex}"
    filename = f"note-{suffix}.txt"
    payload = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "E2E upload test document content.\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/upload",
        data=payload,
        headers={"Authorization": f"Bearer {token_a}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            upload_status = resp.status
    except urllib.error.HTTPError as exc:
        upload_status = exc.code
    check("POST /upload (multipart)", upload_status == 200, f"status={upload_status}")
    status, body, _ = request("GET", "/documents", token=token_a)
    docs = body.get("documents", []) if status == 200 else []
    check("GET /documents (A) contains upload", status == 200 and any(filename in str(d) for d in docs), f"status={status} docs={len(docs)}")

    print()
    print("[7] Artifacts (LLM-generated)")
    status, body, _ = request(
        "POST", "/artifacts",
        {"prompt": f"Create a text file called note-{suffix}.txt whose content is exactly: Hello Nexus E2E", "artifact_type": "text"},
        timeout=300,
    )
    artifact = body.get("artifact", {}) if status == 200 else {}
    artifact_id = artifact.get("id")
    files = artifact.get("files") or []
    artifact_name = next((f.get("name") for f in files if f.get("name", "").endswith(".txt")), None) or (files[0].get("name") if files else None)
    check("POST /artifacts", status == 200 and artifact_id, f"status={status}")
    check("artifact has generated file", bool(artifact_name), f"files={[f.get('name') for f in files]}")
    status, body, _ = request("GET", "/artifacts")
    ids = [a.get("id") for a in body.get("artifacts", [])]
    check("GET /artifacts lists it", status == 200 and artifact_id in ids, f"status={status}")
    status, body, raw = request("GET", f"/artifacts/{artifact_id}/download/{artifact_name}", timeout=60)
    check("download generated file", status == 200 and bool(raw), f"status={status} bytes={len(raw)}")
    status, _, _ = request("GET", f"/artifacts/{artifact_id}/download/nope-{suffix}.txt")
    check("missing file download is 404", status == 404, f"status={status}")

    print()
    print("[8] Automation")
    status, body, _ = request("POST", "/automation/start", {"goal": "Write one short line summarizing this test run."}, token=token_a, timeout=300)
    run_id = body.get("run_id") if status == 200 else None
    check("POST /automation/start", status == 200 and run_id, f"status={status}")
    status, body, _ = request("GET", "/automation/runs", token=token_a)
    runs = body.get("runs", []) if status == 200 else []
    check("GET /automation/runs (A)", status == 200 and any(r.get("run_id") == run_id or r.get("id") == run_id for r in runs), f"status={status}")
    status, _, _ = request("GET", f"/automation/{run_id}", token=token_a)
    check("GET /automation/{run_id} (A)", status == 200, f"status={status}")
    status, _, _ = request("GET", f"/automation/{run_id}", token=token_b)
    check("automation run isolation (B -> 404)", status == 404, f"status={status}")

    print()
    print("[9] Scheduled items")
    status, body, _ = request("POST", "/scheduled", {"title": "E2E reminder", "detail": "Say OK.", "due_at": ""}, token=token_a)
    item_id = body.get("item", {}).get("id") if status == 200 else None
    check("POST /scheduled", status == 200 and item_id, f"status={status}")
    status, body, _ = request("GET", "/scheduled", token=token_a)
    items = body.get("items", []) if status == 200 else []
    check("GET /scheduled (A) contains item", status == 200 and any(i.get("id") == item_id for i in items), f"status={status}")
    status, body, _ = request("POST", f"/scheduled/{item_id}/run", token=token_a, timeout=300)
    check("POST /scheduled/{id}/run executes", status == 200 and body.get("done") is True, f"status={status}")
    status, _, _ = request("DELETE", f"/scheduled/{item_id}", token=token_a)
    check("DELETE /scheduled/{id}", status == 200, f"status={status}")
    status, body_b, _ = request("GET", "/scheduled", token=token_b)
    check("scheduled isolation (B has none of A)", status == 200 and not any(i.get("id") == item_id for i in body_b.get("items", [])), f"status={status}")

    print()
    print("[10] OpenAI-compatible /v1/chat/completions (API key)")
    status, body, _ = request("GET", "/v1/models", token=api_key)
    model_ids = [m.get("id") for m in body.get("data", [])] if status == 200 else []
    check("GET /v1/models with API key", status == 200 and bool(model_ids), f"status={status} models={len(model_ids)}")
    check("installed model listed", MODEL in model_ids, f"models={model_ids}")
    status, body, _ = request(
        "POST", "/v1/chat/completions",
        {"model": MODEL, "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "temperature": 0.0},
        token=api_key, timeout=600,
    )
    answer = ""
    try:
        answer = body["choices"][0]["message"]["content"]
    except Exception:
        pass
    check("POST /v1/chat/completions returns model reply", status == 200 and bool(answer), f"status={status}")

    print()
    print("[11] Chat stream (SSE)")
    status, body, raw = request("POST", "/chat/stream", {"question": "Reply with exactly: OK"}, token=token_a, timeout=600)
    check("POST /chat/stream streams data", status == 200 and bool(raw.strip()), f"status={status}")
    check("stream is SSE-like", "data:" in raw or "content" in raw, f"bytes={len(raw)}")

    print()
    print("[12] Update check (auth)")
    status, body, _ = request("POST", "/aurine/check-update", token=token_a)
    check("POST /aurine/check-update", status == 200, f"status={status}")

    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print()
    print(f"=== {passed}/{total} checks passed ===")
    failed = [name for name, ok in RESULTS if not ok]
    if failed:
        print("Failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
