# Day 08 Lab Report

## 1. Team / student

- Name: Student
- Repo/commit: phase2-track3-day8-langgraph-agent
- Date: 2026-06-29

## 2. Architecture

The LangGraph agent implements a support ticket orchestration workflow with the following nodes:

- **intake**: Normalizes raw user queries
- **classify**: Uses LLM structured output to classify queries into routes (simple, tool, missing_info, risky, error)
- **answer**: Generates responses using LLM with context from tool results and approvals
- **tool**: Executes mock tool calls with error simulation for retry testing
- **evaluate**: Gates retry loops by checking tool results
- **retry**: Increments attempt counter for bounded retry loops
- **dead_letter**: Handles unresolvable failures after max retries
- **clarify**: Asks for missing information on vague queries
- **risky_action**: Prepares destructive actions for human approval
- **approval**: Handles human-in-the-loop decisions (mock or real HITL)
- **finalize**: Emits final audit events for all routes

State fields use append-only reducers for auditability (messages, tool_results, errors, events).

## 3. State schema

| Field | Reducer | Why |
|---|---|---|
| messages | append | audit conversation/events |
| tool_results | append | track all tool execution results |
| errors | append | log failures for debugging |
| events | append | complete audit trail |
| route | overwrite | current route only |
| attempt | overwrite | current retry count |
| final_answer | overwrite | latest response |
| evaluation_result | overwrite | latest evaluation |
| pending_question | overwrite | current clarification |
| proposed_action | overwrite | current proposed action |
| approval | overwrite | latest approval decision |

## 4. Scenario results

| Scenario | Expected route | Actual route | Success | Retries | Interrupts |
|---|---|---|---:|---:|---:|
| S01_simple | simple | simple | Yes | 0 | 0 |
| S02_tool | tool | tool | Yes | 0 | 0 |
| S03_missing | missing_info | missing_info | Yes | 0 | 0 |
| S04_risky | risky | risky | Yes | 0 | 1 |
| S05_error | error | error | Yes | 2 | 0 |
| S06_delete | risky | risky | Yes | 0 | 1 |
| S07_dead_letter | error | error | Yes | 1 | 0 |

**Summary**: 7 scenarios, 100% success rate, 3 total retries, 2 total interrupts

## 5. Failure analysis

1. **Retry/tool failure**: The tool_node simulates transient failures for error-route scenarios. The evaluate_node detects ERROR results and triggers retry loops. The route_after_retry function ensures bounded retries by checking attempt < max_attempts before routing to dead_letter.

2. **Risky action without approval**: The risky_action_node prepares proposed actions and routes through approval_node. The route_after_approval function enforces that approved actions proceed to tool execution while rejected actions route to clarification.

## 6. Persistence / recovery evidence

The lab uses MemorySaver for in-memory checkpointing. Each scenario runs with a unique thread_id (thread-{scenario_id}). The SQLite extension is available for crash-resume scenarios.

## 7. Extension work

- SQLite checkpointer implementation with WAL mode
- Mock HITL approval with interrupt() support for real HITL mode
- LLM-based classification with structured output
- LLM-grounded answer generation with context from tool results

## 8. Improvement plan

If I had one more day, I would productionize:
1. Real HITL integration with interrupt() and a Streamlit UI
2. Parallel fan-out using Send() for multi-tool execution
3. Time travel debugging via get_state_history() replay
4. Observability with LangSmith tracing
