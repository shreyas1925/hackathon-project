from dotenv import load_dotenv
import os
import streamlit as st
import json
from openai import AzureOpenAI
from tools.tool_schema import functions
from tools.tool_functions import create_monitor, fetch_ba_level_information, fetch_endpoint_information, compare_endpoint_charges, fetch_agent_information

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
more_api_key = os.getenv("MORE_API_KEY")
more_mongo_uri = os.getenv("MORE_MONGO_URI")
app_key = os.getenv("APP_KEY")

# Setup Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint='https://chat-ai.cisco.com',
    api_key=openai_api_key,
    api_version="2023-08-01-preview"
)

# Streamlit UI config
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

# ---------------- UI State Management ----------------
if "conversations" not in st.session_state:
    st.session_state.conversations = {"Default Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Default Chat"

# ---------------- Sidebar: Conversation Selector ----------------
st.sidebar.markdown("### 💬 Conversations")

# Clickable conversation buttons
for chat_name in st.session_state.conversations.keys():
    if st.sidebar.button(chat_name):
        st.session_state.current_chat = chat_name
        st.rerun()

# New conversation creation
st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ Start a new chat")

new_chat_name = st.sidebar.text_input("New conversation name", key="new_chat_name")
if st.sidebar.button("Create"):
    if new_chat_name and new_chat_name not in st.session_state.conversations:
        st.session_state.conversations[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        st.rerun()

# ---------------- Chat Memory ----------------
chat_key = st.session_state.current_chat
if chat_key not in st.session_state.conversations:
    st.session_state.conversations[chat_key] = []

chat_history = st.session_state.conversations[chat_key]

# ---------------- Display Header ----------------
st.markdown(f"""
<div class="chat-header">
    <h1>🛠️ MonitorEase</h1>
    <span>Chat: <b>{chat_key}</b></span>
</div>
""", unsafe_allow_html=True)

# ---------------- Display Chat ----------------
for role, content in chat_history:
    with st.chat_message(role):
        st.markdown(content)

# ---------------- Chat Input ----------------
user_input = st.chat_input("Ask me to create a monitor or list monitors...")

if user_input:
    chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    base_system_msg = {
        "role": "system",
        "content": """You are MonitorEase, a helpful assistant that helps app owners and support engineers.
        When the user asks to create a monitor, always map the test type to one of: HTTP, WebTransaction, Network, DNS, FTTP.
        If the user says http, httptest, or similar, use HTTP. If unsure, ask the user to clarify."""
    }

    messages = [base_system_msg] + [
        {"role": role, "content": content} for role, content in chat_history[-10:]
    ]

    # OpenAI LLM call
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto",
        user=json.dumps({"appkey": app_key})
    )

    message = response.choices[0].message
    assistant_content = message.content or ""

    if message.content:
        st.chat_message("assistant").markdown(message.content)
        chat_history.append(("assistant", message.content))

    # Function call handling
    if message.function_call:
        try:
            args = json.loads(message.function_call.arguments)
            func_name = message.function_call.name

            if func_name == "create_monitor":
                reply = create_monitor(**args)
            elif func_name == "fetch_ba_level_information":
                reply = fetch_ba_level_information(**args, user_input=user_input, openai_client=client, app_key=app_key)
            elif func_name == "fetch_endpoint_information":
                reply = fetch_endpoint_information(**args, user_input=user_input, openai_client=client, app_key=app_key)
            elif func_name == "compare_endpoint_charges":
                reply = compare_endpoint_charges(**args, openai_client=client, app_key=app_key)
            elif func_name == "fetch_agent_information":
                reply = fetch_agent_information(**args, openai_client=client, app_key=app_key)
            else:
                reply = "❌ Sorry, this function is not yet supported."

            with st.chat_message("assistant"):
                st.markdown(f"🧠 `{func_name}` was called with:\n```\n{json.dumps(args, indent=2)}\n```")

            st.chat_message("assistant").markdown(reply)
            chat_history.append(("assistant", reply))
        except Exception as e:
            err_msg = f"{e}"
            st.chat_message("assistant").markdown(err_msg)
            chat_history.append(("assistant", err_msg))
