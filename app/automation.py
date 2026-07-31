"""Autonomous automation runs: goal-driven agent loops with progress tracking."""
import threading
import time
from datetime import datetime
from uuid import uuid4

from .agent_tools import TOOL_DEFINITIONS, execute_tool
from .llm import chat_with_tools

MAX_ROUNDS = 8
RUNS: dict[str, dict] = {}
_RUNS_LOCK = threading.Lock()

SYSTEM_PROMPT = (
    "You are Aurine Autopilot - an autonomous AI worker. "
    "You have been given a goal. Work through it step by step using your tools "
    "(search the web, read/write files, run code, manage projects). "
    "Keep going until the goal is fully complete. "
    "Respond ONLY with valid JSON: "
    '{"message": "what you did / your answer", "actions": [{"tool": "tool_name", "param": "value"}]}. '
    "When the goal is complete and no more tools are needed, respond with "
    '{"message": "FINAL ANSWER", "actions": []}'
)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def start_automation(user_id: str, goal: str, model_config: dict | None = None) -> str:
    run_id = uuid4().hex
    with _RUNS_LOCK:
        RUNS[run_id] = {
            "run_id": run_id,
            "user_id": user_id,
            "goal": goal,
            "status": "running",
            "progress": [],
            "result": "",
            "error": "",
            "tool_calls": 0,
            "rounds": 0,
            "created_at": _now(),
            "finished_at": "",
        }
    worker = threading.Thread(
        target=_run_automation,
        args=(run_id, user_id, goal, dict(model_config or {})),
        daemon=True,
    )
    worker.start()
    return run_id


def _run_automation(run_id: str, user_id: str, goal: str, model_config: dict) -> None:
    run = RUNS[run_id]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"GOAL:\n{goal}"},
    ]
    try:
        for round_index in range(1, MAX_ROUNDS + 1):
            result = chat_with_tools(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_executor=lambda name, args: execute_tool(name, args, user_id),
                temperature=0.2,
                model_config=model_config or None,
                max_iterations=3,
            )
            tool_calls = result.get("tool_calls", [])
            answer = str(result.get("answer", ""))
            run["rounds"] = round_index
            run["tool_calls"] += len(tool_calls)
            run["progress"].append({
                "round": round_index,
                "tool_calls": len(tool_calls),
                "answer": answer[:500],
                "at": _now(),
            })

            if not tool_calls:
                run["status"] = "done"
                marker = answer.strip().lower()
                if marker in ("final answer", "final answer.", "done", "complete", "complete.") and run["progress"]:
                    answer = run["progress"][-1]["answer"]
                run["result"] = answer
                break

            messages.append({
                "role": "assistant",
                "content": answer or f"Round {round_index}: executed {len(tool_calls)} tool(s).",
            })
            messages.append({
                "role": "user",
                "content": (
                    "Continue working toward the goal with the latest tool results in mind. "
                    "When the goal is complete or no more tools are needed, reply with your final answer and an empty actions list."
                ),
            })
        else:
            run["status"] = "limit"
            last = run["progress"][-1]["answer"] if run["progress"] else ""
            run["result"] = last or "Reached the round limit before completing the goal."
    except Exception as exc:  # noqa: BLE001
        run["status"] = "error"
        run["error"] = str(exc)
    run["finished_at"] = _now()


def list_runs(user_id: str, limit: int = 30) -> list[dict]:
    with _RUNS_LOCK:
        runs = [
            {k: v for k, v in r.items() if k != "user_id"}
            for r in RUNS.values()
            if r["user_id"] == user_id
        ]
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return runs[:limit]


def get_run(run_id: str, user_id: str) -> dict | None:
    with _RUNS_LOCK:
        run = RUNS.get(run_id)
        if not run or run["user_id"] != user_id:
            return None
        return {k: v for k, v in run.items() if k != "user_id"}


def _tidy_runs() -> None:
    with _RUNS_LOCK:
        stale = [rid for rid, r in RUNS.items() if r["finished_at"] and time.time() - r.get("_end_ts", 0) > 3600]
        for rid in stale:
            RUNS.pop(rid, None)
