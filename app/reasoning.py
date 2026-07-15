import json
import re
from typing import Generator

from .llm import chat_completion, chat_completion_stream


class ReasoningEngine:
    def __init__(self, model_config: dict | None = None):
        self.model_config = model_config or {}
        self.temperature = 0.2

    def analyze_complexity(self, query: str) -> dict:
        simple_indicators = [
            r"\b(hi|hello|hey|bye|thanks|ok|yes|no)\b",
            r"^[\w\s?]{1,30}$",
            r"\b(time|date|weather|time kya|date kya)\b",
        ]
        complex_indicators = [
            r"\b(build|create|implement|design|architect|refactor|deploy|migrate)\b",
            r"\b(full.?stack|end.?to.?end|complete|entire|whole|system)\b",
            r"\b(bug|error|issue|problem|fix|debug|crash|failing)\b",
            r"\b(analyze|compare|evaluate|research|investigate)\b",
            r"\b(step.?by.?step|detailed|comprehensive|thorough)\b",
            r"\b(code|project|app|website|api|database|server)\b.*\b(with|using|in|for)\b",
        ]
        simple_score = sum(1 for p in simple_indicators if re.search(p, query, re.IGNORECASE))
        complex_score = sum(1 for p in complex_indicators if re.search(p, query, re.IGNORECASE))

        if simple_score > 0 and complex_score == 0:
            return {"level": "simple", "reasoning_needed": False, "estimated_steps": 1}
        if complex_score >= 3:
            return {"level": "complex", "reasoning_needed": True, "estimated_steps": max(3, complex_score)}
        if complex_score >= 1:
            return {"level": "moderate", "reasoning_needed": True, "estimated_steps": 2}
        return {"level": "moderate", "reasoning_needed": False, "estimated_steps": 1}

    def generate_plan(self, query: str, context: str = "") -> str:
        plan_prompt = (
            "Analyze this request and create a brief execution plan.\n"
            "List the steps needed to fully address the request. Be specific and actionable.\n"
            "Format: numbered list of steps, each one line.\n\n"
            f"Request: {query}\n"
        )
        if context:
            plan_prompt += f"Context: {context[:500]}\n"
        plan_prompt += "\nPlan:"

        messages = [
            {"role": "system", "content": "You are a task planner. Output a concise numbered plan. No preamble."},
            {"role": "user", "content": plan_prompt},
        ]
        try:
            plan = chat_completion(messages=messages, temperature=0.2, model_config=self.model_config)
            return plan.strip()
        except Exception:
            return f"1. Understand the request\n2. Gather information\n3. Execute the solution\n4. Verify the result"

    def self_verify(self, query: str, answer: str) -> str:
        verify_prompt = (
            "Review this answer for accuracy, completeness, and quality.\n"
            "If there are issues, provide a corrected version. If the answer is good, return it as-is.\n\n"
            f"Original question: {query}\n"
            f"Answer to verify:\n{answer}\n\n"
            "If corrections needed, output the improved answer. If already good, output the same answer."
        )
        messages = [
            {"role": "system", "content": "You are a quality reviewer. Output only the final verified answer."},
            {"role": "user", "content": verify_prompt},
        ]
        try:
            verified = chat_completion(messages=messages, temperature=0.1, model_config=self.model_config)
            return verified.strip() if verified.strip() else answer
        except Exception:
            return answer

    def decompose_task(self, query: str) -> list[dict]:
        decomp_prompt = (
            "Break this task into subtasks. For each subtask, identify what tool or capability is needed.\n"
            "Output JSON: {\"subtasks\": [{\"description\": \"...\", \"tool_needed\": \"...\", \"priority\": \"high|medium|low\"}]}\n\n"
            f"Task: {query}"
        )
        messages = [
            {"role": "system", "content": "Output valid JSON only. No explanation."},
            {"role": "user", "content": decomp_prompt},
        ]
        try:
            result = chat_completion(messages=messages, temperature=0.2, json_mode=True, model_config=self.model_config)
            parsed = json.loads(result)
            return parsed.get("subtasks", [])
        except Exception:
            return [{"description": query, "tool_needed": "general", "priority": "high"}]

    def reflect_and_improve(self, query: str, current_answer: str, tools_used: list[dict]) -> str:
        tools_summary = "\n".join(
            f"- {t.get('name', 'unknown')}: {str(t.get('arguments', {}))[:100]}"
            for t in tools_used
        ) if tools_used else "None"

        reflect_prompt = (
            "Review the current answer and tool usage. Consider:\n"
            "1. Is the answer complete?\n"
            "2. Were the right tools used?\n"
            "3. Is there information that could be added?\n"
            "4. Is the answer in the right language and tone?\n\n"
            f"Question: {query}\n"
            f"Current answer: {current_answer[:2000]}\n"
            f"Tools used: {tools_summary}\n\n"
            "If improvements are needed, provide an enhanced answer. Output the final improved answer."
        )
        messages = [
            {"role": "system", "content": "You are a reflection agent. Output the improved final answer."},
            {"role": "user", "content": reflect_prompt},
        ]
        try:
            improved = chat_completion(messages=messages, temperature=0.2, model_config=self.model_config)
            return improved.strip() if improved.strip() and len(improved) > 50 else current_answer
        except Exception:
            return current_answer

    def chain_of_thought(self, query: str, context: str = "") -> Generator[str, None, None]:
        yield f"Thinking about: {query[:100]}...\n\n"

        complexity = self.analyze_complexity(query)
        yield f"**Analysis:** Complexity level: {complexity['level']}\n"

        if not complexity["reasoning_needed"]:
            yield "**Decision:** Direct response is sufficient.\n\n"
            return

        yield f"**Plan:** Breaking into ~{complexity['estimated_steps']} steps\n\n"

        plan = self.generate_plan(query, context)
        yield f"**Execution Plan:**\n{plan}\n\n"
        yield "---\n\n"


def build_reasoning_context(query: str, model_config: dict | None = None) -> str:
    engine = ReasoningEngine(model_config)
    complexity = engine.analyze_complexity(query)

    if not complexity["reasoning_needed"]:
        return ""

    parts = [f"Query complexity: {complexity['level']}"]
    if complexity["reasoning_needed"]:
        plan = engine.generate_plan(query)
        parts.append(f"Suggested approach:\n{plan}")

    return "\n".join(parts)
