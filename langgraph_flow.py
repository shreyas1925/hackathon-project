from typing import TypedDict, List, Callable
from langgraph.graph import StateGraph, END
from agents.reflect_summary_agent import reflect_and_summarize
from agents.reflect_review_agent import review_monitor_arguments
from tools.tool_functions import create_monitor
from langsmith import traceable


class MonitorState(TypedDict, total=False):
    chat_history: List[dict]
    summary: str
    confirmation_prompt: str
    user_confirmation: str
    monitor_args: dict
    result: str
    operation_type: str

def build_monitor_flow(openai_client, tool_function: Callable, operation_type: str):

    builder = StateGraph(MonitorState)

    @traceable(name="Reflect & Summarize")
    def reflect(state: MonitorState) -> MonitorState:
        summary = reflect_and_summarize(openai_client, state["chat_history"])
        return {"summary": summary}

    @traceable(name="Generate Confirmation Prompt")
    def confirm_summary(state: MonitorState) -> MonitorState:
        summary = state["summary"]
        return {
            "summary": summary,
            "confirmation_prompt": f"Here is what I understood:\n\n{summary}\n\nDo you want to proceed? (Yes/No)"
        }

    @traceable(name="Execute Monitor Resource")
    def execute_tool(state: MonitorState) -> MonitorState:
        args = state.get("monitor_args", {})
        result = tool_function(**args)
        return {"result": result}

    builder.add_node("Reflect", reflect)
    builder.add_node("Confirm", confirm_summary)
    builder.add_node("Execute", execute_tool)

    # Entry point and flow logic
    if tool_function.__name__ in ["create_monitor", "update_monitor"]:
        def review(state: MonitorState) -> MonitorState:
            state["operation_type"] = operation_type  
            return review_monitor_arguments(state)
        builder.add_node("Review", review)
        builder.set_entry_point("Review")
        builder.add_edge("Review", "Reflect")
    else:
        builder.set_entry_point("Reflect")

    # Common edges
    builder.add_edge("Reflect", "Confirm")
    builder.add_conditional_edges(
        "Confirm",
        lambda state: "Execute" if state.get("user_confirmation", "").lower() == "yes" else END
    )
    builder.set_finish_point("Execute")

    return builder.compile()
