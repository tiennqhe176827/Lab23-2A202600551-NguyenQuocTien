"""Report generation helper."""

from __future__ import annotations

from pathlib import Path

from .metrics import MetricsReport


def render_report(metrics: MetricsReport) -> str:
    """Render a complete lab report from metrics data."""
    lines = [
        "# Day 08 Lab Report",
        "",
        "## 1. Team / student",
        "",
        "- Name: Student",
        "- Repo/commit: phase2-track3-day8-langgraph-agent",
        "- Date: 2026-06-29",
        "",
        "## 2. Architecture",
        "",
        "The LangGraph agent implements a support ticket orchestration workflow.",
        "",
        "- **intake**: Normalizes raw user queries",
        "- **classify**: Uses LLM structured output to classify routes",
        "- **answer**: Generates responses using LLM with context",
        "- **tool**: Executes mock tool calls with error simulation",
        "- **evaluate**: Gates retry loops by checking tool results",
        "- **retry**: Increments attempt counter for bounded retry loops",
        "- **dead_letter**: Handles unresolvable failures after max retries",
        "- **clarify**: Asks for missing information on vague queries",
        "- **risky_action**: Prepares destructive actions for approval",
        "- **approval**: Handles human-in-the-loop decisions",
        "- **finalize**: Emits final audit events for all routes",
        "",
        "State fields use append-only reducers for auditability.",
        "",
        "## 3. State schema",
        "",
        "| Field | Reducer | Why |",
        "|---|---|---|",
        "| messages | append | audit conversation/events |",
        "| tool_results | append | track tool execution results |",
        "| errors | append | log failures for debugging |",
        "| events | append | complete audit trail |",
        "| route | overwrite | current route only |",
        "| attempt | overwrite | current retry count |",
        "| final_answer | overwrite | latest response |",
        "| evaluation_result | overwrite | latest evaluation |",
        "| pending_question | overwrite | current clarification |",
        "| proposed_action | overwrite | current proposed action |",
        "| approval | overwrite | latest approval decision |",
        "",
        "## 4. Scenario results",
        "",
        "| Scenario | Expected | Actual | Success | Retries | Interrupts |",
        "|---|---|---|---:|---:|---:|",
    ]

    for m in metrics.scenario_metrics:
        actual = m.actual_route or "N/A"
        success = "Yes" if m.success else "No"
        lines.append(
            f"| {m.scenario_id} | {m.expected_route} | {actual} | "
            f"{success} | {m.retry_count} | {m.interrupt_count} |"
        )

    lines.extend([
        "",
        f"**Summary**: {metrics.total_scenarios} scenarios, "
        f"{metrics.success_rate:.0%} success rate, "
        f"{metrics.total_retries} total retries, "
        f"{metrics.total_interrupts} total interrupts",
        "",
        "## 5. Failure analysis",
        "",
        "1. **Retry/tool failure**: The tool_node simulates transient failures. "
        "The evaluate_node detects ERROR results and triggers retry loops. "
        "The route_after_retry function ensures bounded retries.",
        "",
        "2. **Risky action without approval**: The risky_action_node prepares "
        "proposed actions and routes through approval_node. The "
        "route_after_approval function enforces approval before tool execution.",
        "",
        "## 6. Persistence / recovery evidence",
        "",
        "The lab uses MemorySaver for in-memory checkpointing. Each scenario "
        "runs with a unique thread_id. SQLite extension is available.",
        "",
        "## 7. Extension work",
        "",
        "- SQLite checkpointer with WAL mode",
        "- Mock HITL approval with interrupt() support",
        "- LLM-based classification with structured output",
        "- LLM-grounded answer generation with context",
        "",
        "## 8. Improvement plan",
        "",
        "If I had one more day, I would productionize:",
        "1. Real HITL integration with interrupt() and Streamlit UI",
        "2. Parallel fan-out using Send() for multi-tool execution",
        "3. Time travel debugging via get_state_history() replay",
        "4. Observability with LangSmith tracing",
        "",
    ])

    return "\n".join(lines)


def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    """Write the rendered report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(metrics), encoding="utf-8")
