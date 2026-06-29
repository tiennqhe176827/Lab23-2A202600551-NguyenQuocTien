"""Node functions for the LangGraph workflow.

Each function receives AgentState and returns a partial state update dict.
Do NOT mutate input state — return new values only.

LLM REQUIREMENT:
- classify_node MUST use a real LLM call (structured output for intent classification)
- answer_node MUST use a real LLM call (grounded response generation)
- evaluate_node SHOULD use LLM-as-judge (bonus points; heuristic acceptable for base score)
"""

from __future__ import annotations

import os
from pydantic import BaseModel

from .llm import get_llm
from .state import AgentState, make_event


# ─── EXAMPLE: working node (provided for reference) ──────────────────
def intake_node(state: AgentState) -> dict:
    """Normalize raw query. This node is provided as a working example."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


# ─── Structured output schemas for LLM calls ────────────────────────

class Classification(BaseModel):
    route: str
    risk_level: str


# ─── TODO(student): implement ALL nodes below ────────────────────────


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route using an LLM.

    *** MUST use a real LLM call — keyword-only heuristics will lose points. ***
    """
    llm = get_llm()
    query = state.get("query", "")

    structured_llm = llm.with_structured_output(Classification)

    classification = structured_llm.invoke(
        f"""You are a support ticket classifier. Classify the following user query into exactly ONE of these categories:

- "simple": Basic questions, FAQs, how-to guides (e.g., password reset, account info)
- "tool": Queries requiring a tool lookup or API call (e.g., order status, data retrieval)
- "missing_info": Vague or incomplete queries that need clarification (e.g., "fix it", "help")
- "risky": Queries involving destructive or sensitive actions requiring approval (e.g., refund, delete, cancel)
- "error": Queries describing errors, failures, timeouts, or system issues

Also assess risk_level:
- "high" for risky route
- "low" for all other routes

Priority guide: risky > tool > missing_info > error > simple

User query: "{query}"
"""
    )

    return {
        "route": classification.route,
        "risk_level": classification.risk_level,
        "events": [make_event("classify", "completed", f"route={classification.route}")],
    }


def tool_node(state: AgentState) -> dict:
    """Execute a mock tool call with error simulation."""
    route = state.get("route", "")
    attempt = state.get("attempt", 0)

    if route == "error" and attempt < 2:
        result = "ERROR: Transient failure occurred while processing request"
    else:
        result = f"Tool result: Successfully processed query '{state.get('query', '')[:50]}'"

    return {
        "tool_results": [result],
        "events": [make_event("tool", "completed", f"attempt={attempt}")],
    }


def evaluate_node(state: AgentState) -> dict:
    """Evaluate tool results — the retry-loop gate."""
    tool_results = state.get("tool_results", [])
    latest = tool_results[-1] if tool_results else ""

    if "ERROR" in str(latest).upper():
        evaluation = "needs_retry"
    else:
        evaluation = "success"

    return {
        "evaluation_result": evaluation,
        "events": [make_event("evaluate", "completed", f"result={evaluation}")],
    }


def answer_node(state: AgentState) -> dict:
    """Generate a final response using an LLM.

    *** MUST use a real LLM call — hardcoded strings will lose points. ***
    """
    llm = get_llm()
    query = state.get("query", "")
    tool_results = state.get("tool_results", [])
    approval = state.get("approval")

    context_parts = [f"User query: {query}"]
    if tool_results:
        context_parts.append(f"Tool results: {tool_results}")
    if approval:
        context_parts.append(f"Approval decision: {approval}")
    context = "\n".join(context_parts)

    response = llm.invoke(
        f"""You are a helpful support assistant. Generate a clear, helpful response based on the following context.

{context}

Provide a concise, professional response that directly addresses the user's query."""
    )

    answer = response.content if hasattr(response, "content") else str(response)

    return {
        "final_answer": answer,
        "events": [make_event("answer", "completed", "response generated")],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask for missing information instead of hallucinating."""
    query = state.get("query", "")
    question = f"I understand you need help, but I need more details. Could you please clarify what specific issue you're experiencing with: '{query[:100]}'?"

    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("clarify", "completed", "asked for clarification")],
    }


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky action for human approval."""
    query = state.get("query", "")
    proposed = f"Proposed action: Process the following request that requires approval - '{query[:100]}'. This action may have irreversible effects."

    return {
        "proposed_action": proposed,
        "events": [make_event("risky_action", "completed", "action prepared for approval")],
    }


def approval_node(state: AgentState) -> dict:
    """Human-in-the-loop approval step.

    Default: mock approval. Extension: real HITL with interrupt() if LANGGRAPH_INTERRUPT=true.
    """
    if os.getenv("LANGGRAPH_INTERRUPT") == "true":
        from langgraph.types import interrupt
        decision = interrupt({"action": state.get("proposed_action", ""), "message": "Please approve or reject this action"})
    else:
        decision = {"approved": True, "reviewer": "mock-reviewer", "comment": "auto-approved for testing"}

    return {
        "approval": decision,
        "events": [make_event("approval", "completed", f"approved={decision.get('approved', False)}")],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt."""
    attempt = state.get("attempt", 0) + 1

    return {
        "attempt": attempt,
        "errors": [f"Retry attempt {attempt} after tool failure"],
        "events": [make_event("retry", "completed", f"attempt={attempt}")],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Handle unresolvable failures after max retries exceeded."""
    max_attempts = state.get("max_attempts", 3)
    answer = f"I apologize, but I was unable to resolve your request after {max_attempts} attempts. Your issue has been escalated to a human agent who will follow up with you shortly."

    return {
        "final_answer": answer,
        "events": [make_event("dead_letter", "completed", f"max_attempts={max_attempts}")],
    }


def finalize_node(state: AgentState) -> dict:
    """Emit a final audit event. All routes must pass through here before END."""
    return {
        "events": [make_event("finalize", "completed", "workflow finished")],
    }
