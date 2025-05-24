from dotenv import load_dotenv
import os
import streamlit as st
import json
from openai import AzureOpenAI
from tools.tool_schema import functions
from tools.tool_functions import (
    fetch_ba_level_information, fetch_endpoint_information,
    compare_endpoint_charges, fetch_agent_information, fetch_request_status
)
from langgraph_flow import build_monitor_flow  

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
app_key = os.getenv("APP_KEY")

# Setup Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint='https://chat-ai.cisco.com',
    api_key=openai_api_key,
    api_version="2023-08-01-preview"
)


# Streamlit UI setup
st.set_page_config(page_title="MonitorEase Assistant", layout="wide")
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        .stChatMessage.user { background-color: #f0f0f0; }
        .stChatMessage.assistant { background-color: #eaf4ff; }
        .stTextInput > div > div { width: 100% !important; }
        .chat-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.5rem 1rem; border-bottom: 1px solid #ddd;
        }
        .chat-header h1 { margin: 0; font-size: 1.5rem; }
        .chat-header span { font-size: 0.9rem; color: gray; }
        section[data-testid="stSidebar"] button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# State initialization
if "conversations" not in st.session_state:
    st.session_state.conversations = {"Default Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Default Chat"
if "langgraph_state" not in st.session_state:
    st.session_state.langgraph_state = None
if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False

# Sidebar: Conversations
st.sidebar.markdown("### 💬 Conversations")
for chat_name in st.session_state.conversations.keys():
    if st.sidebar.button(chat_name):
        st.session_state.current_chat = chat_name
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ Start a new chat")
new_chat_name = st.sidebar.text_input("New conversation name", key="new_chat_name")
if st.sidebar.button("Create"):
    if new_chat_name and new_chat_name not in st.session_state.conversations:
        st.session_state.conversations[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        st.rerun()

# Active conversation
chat_key = st.session_state.current_chat
chat_history = st.session_state.conversations.setdefault(chat_key, [])

# Display header and past chat
st.markdown(f"""
<div class="chat-header">
    <h1>🛠️ MonitorEase</h1>
    <span>Chat: <b>{chat_key}</b></span>
</div>
""", unsafe_allow_html=True)

for role, content in chat_history:
    with st.chat_message(role):
        st.markdown(content)

# Chat Input
user_input = st.chat_input("Ask me to create a monitor or list monitors...")
monitor_flow = build_monitor_flow(client)
if user_input:
    chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # Handle LangGraph confirmation input
    if st.session_state.awaiting_confirmation:
        st.session_state.langgraph_state["user_confirmation"] = user_input.strip().lower()
        result_state = monitor_flow.invoke(st.session_state.langgraph_state)

        if result_state.get("user_confirmation", "").lower() == "yes":
            st.chat_message("assistant").markdown(result_state["result"])
            chat_history.append(("assistant", result_state["result"]))
        else:
            cancel_msg = "Okay, monitor creation is cancelled. Please go on and ask for any queries"
            st.chat_message("assistant").markdown(cancel_msg)
            chat_history.append(("assistant", cancel_msg))

        st.session_state.awaiting_confirmation = False
        st.session_state.langgraph_state = None

    else:
        # LLM + function call
        base_system_msg = {
            "role": "system",
            "content": """You are MonitorEase, a helpful assistant that helps app owners and support engineers.
            When the user asks to create a monitor, always map the test type to one of: HTTP, WebTransaction, Network, DNS, FTTP.
            If the user says http, httptest, or similar, use HTTP. If unsure, ask the user to clarify.
            If a user asks something unrelated, say:
            "I'm sorry, I don't understand that request. Could you please rephrase or try something related to monitoring?"
            Only call tools (functions) when the user intent matches your tool definitions."""
        }

        messages = [base_system_msg] + [
            {"role": role, "content": content} for role, content in chat_history[-10:]
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            function_call="auto",
            user=json.dumps({"appkey": app_key})
        )

        message = response.choices[0].message
        if message.content:
            st.chat_message("assistant").markdown(message.content)
            chat_history.append(("assistant", message.content))

        # Handle function calls
        if message.function_call:
            try:
                args = json.loads(message.function_call.arguments)
                func_name = message.function_call.name

                if func_name == "create_monitor":
                    st.session_state.langgraph_state = {
                        "chat_history": messages,
                        "monitor_args": args,
                    }
                    result_state = monitor_flow.invoke(st.session_state.langgraph_state)
                    confirmation_prompt = result_state.get("confirmation_prompt", "Proceed? (Yes/No)")

                    st.session_state.awaiting_confirmation = True
                    st.chat_message("assistant").markdown(confirmation_prompt)
                    chat_history.append(("assistant", confirmation_prompt))

                else:
                    # Map and call other tools
                    tool_map = {
                        "fetch_ba_level_information": fetch_ba_level_information,
                        "fetch_endpoint_information": fetch_endpoint_information,
                        "compare_endpoint_charges": compare_endpoint_charges,
                        "fetch_agent_information": fetch_agent_information,
                        "fetch_request_status": fetch_request_status
                    }
                    reply = tool_map.get(func_name, lambda **kwargs: "❌ Unsupported function.")(
                        **args, openai_client=client, app_key=app_key, user_input=user_input
                    )
                    st.chat_message("assistant").markdown(reply)
                    chat_history.append(("assistant", reply))

            except Exception as e:
                err_msg = f"❌ Error: {str(e)}"
                st.chat_message("assistant").markdown(err_msg)
                chat_history.append(("assistant", err_msg))
