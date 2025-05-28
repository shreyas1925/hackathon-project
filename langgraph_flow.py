from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from agents.reflect_summary_agent import reflect_and_summarize
from tools.tool_functions import create_monitor
from langsmith import traceable


class MonitorState(TypedDict, total=False):
    chat_history: List[dict]
    summary: str
    confirmation_prompt: str
    user_confirmation: str
    monitor_args: dict
    result: str

def build_monitor_flow(openai_client):

    builder = StateGraph(MonitorState)

    @traceable(name="Reflect & Summarize")
    def reflect(state: MonitorState) -> MonitorState:
        summary = reflect_and_summarize(openai_client, state["chat_history"])
        return {"summary": summary}

    @traceable(name="Generate Confirmation Prompt")
    def confirm_summary(state: MonitorState) -> MonitorState:
        summary = state["summary"]
        print(summary)
        return {
            "summary": summary,
            "confirmation_prompt": f"Here is what i understood:\n\n{summary}\n\nDo you want to proceed? (Yes/No)"
        }

    @traceable(name="Create Monitor Resource")
    def create(state: MonitorState) -> MonitorState:
        args = state.get("monitor_args", {})
        result = create_monitor(**args)
        return {"result": result}

    builder.add_node("Reflect", reflect)
    builder.add_node("Confirm", confirm_summary)
    builder.add_node("CreateMonitor", create)

    builder.set_entry_point("Reflect")
    builder.add_edge("Reflect", "Confirm")

    builder.add_conditional_edges(
        "Confirm",
        lambda state: "CreateMonitor" if state.get("user_confirmation", "").lower() == "yes" else END
    )

    builder.set_finish_point("CreateMonitor")

    return builder.compile()
